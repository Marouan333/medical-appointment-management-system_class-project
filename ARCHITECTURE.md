# Architecture — Système de Gestion des Rendez-vous Médicaux

## 1. Diagramme d'architecture

```
                              ┌──────────────────────────────────┐
                              │         CLIENTS                  │
                              │  (Web / Mobile / Postman)        │
                              └──────────────┬───────────────────┘
                                             │  HTTPS / REST + JWT
              ┌──────────────────────────────┼─────────────────────────────────┐
              │                              │                                 │
              ▼                              ▼                                 ▼
   ┌────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
   │   AUTH-SERVICE     │       │   PATIENT-SERVICE      │       │ PRACTITIONER-SERVICE   │
   │   :8001            │       │   :8002                │       │   :8003                │
   │  - register/login  │       │  - profile             │       │  - profiles            │
   │  - JWT issuance    │       │  - medical history     │       │  - schedules           │
   │  - roles           │       │  - preferences         │       │  - availability calc.  │
   └────────┬───────────┘       └────────┬───────────────┘       └────────┬───────────────┘
            │                            │                                │
            │ JWT (HS256, shared secret) │                                │ HTTP (booked slots)
            └─────► all services decode locally                           │
                                                                          │
                              ┌────────────────────────┐                  │
                              │  APPOINTMENT-SERVICE   │◄─────────────────┘
                              │  :8004                 │
                              │  - book / reschedule   │ HTTP ▼
                              │  - cancel / confirm    │   ┌──────────────────────────┐
                              │  - conflict detection  │──▶│  NOTIFICATION-SERVICE    │
                              │  - audit log           │   │  :8005                   │
                              └────────┬───────────────┘   │  - email (Mailhog SMTP)  │
                                       │                   │  - SMS (stub)            │
                                       │                   │  - reminder scheduler    │
                                       │                   └──────────────────────────┘
                                       │ DB read
                                       ▼
                              ┌────────────────────────┐
                              │  ANALYTICS-SERVICE     │
                              │  :8006                 │
                              │  - fill rate           │
                              │  - no-show rate        │
                              │  - peak hours          │
                              └────────────────────────┘

                ┌─────────────────────────────────────────────────────┐
                │              POSTGRESQL 16 (single instance)        │
                │  auth_db │ patient_db │ practitioner_db │           │
                │  appointment_db │ notification_db │ analytics_db    │
                └─────────────────────────────────────────────────────┘

                ┌─────────────────────────────┐
                │  MAILHOG  :1025 (SMTP) :8025 (UI)
                └─────────────────────────────┘
```

---

## 2. Flux de données — réservation d'un rendez-vous (golden path)

```
Patient                Auth                  Practitioner         Appointment           Notification
   │                    │                         │                     │                     │
   │── POST /login ────►│                         │                     │                     │
   │◄── access+refresh ─│                         │                     │                     │
   │                    │                         │                     │                     │
   │── GET /availability ──────────────────────►  │                     │                     │
   │                    │   (fetch booked slots) ◄─────────────────────►│                     │
   │◄── slots ────────────────────────────────────│                     │                     │
   │                    │                         │                     │                     │
   │── POST /appointments (JWT) ──────────────────────────────────────► │                     │
   │                    │                         │ ◄─ practitioner_exists?│                  │
   │                    │                         │                     │── notify ──────────►│
   │◄── 201 Created ────────────────────────────────────────────────────│                     │
   │                                                                    │                     │── SMTP
   │                                                                    │                     │   to Mailhog
```

**Étapes détaillées:**
1. Patient se connecte → `auth-service` retourne un JWT.
2. Patient consulte les créneaux libres via `practitioner-service/{id}/availability`.
3. Le practitioner-service combine: planning hebdo + overrides (vacances) + créneaux déjà réservés (récupérés depuis appointment-service via `/appointments/internal/booked`).
4. Patient envoie `POST /appointments` avec son JWT.
5. appointment-service:
   - Décode le JWT (secret partagé)
   - Vérifie l'existence du practitioner (HTTP)
   - Détecte les conflits sur la table `appointments` (chevauchement temporel)
   - Insère le RDV avec `status=scheduled`
   - Écrit une entrée dans `appointment_history`
   - Appelle notification-service (best-effort, fire-and-forget)
6. notification-service envoie l'email via Mailhog SMTP, capturé pour visualisation.

---

## 3. Bases de données

### auth_db
| Table | Colonnes principales |
|---|---|
| `users` | id (UUID), email, password_hash, role, is_active, created_at |
| `refresh_tokens` | id, user_id, token, expires_at, created_at |

### patient_db
| Table | Colonnes principales |
|---|---|
| `patients` | id, user_id, first_name, last_name, birth_date, phone, address, preferred_channel, language |
| `medical_history` | id, patient_id (FK), condition, notes, recorded_at |

### practitioner_db
| Table | Colonnes principales |
|---|---|
| `practitioners` | id, user_id, first_name, last_name, specialty, bio |
| `schedules` | id, practitioner_id (FK), day_of_week (0-6), start_time, end_time, slot_duration_min |
| `availability_overrides` | id, practitioner_id (FK), date, is_available, reason |

### appointment_db
| Table | Colonnes principales |
|---|---|
| `appointments` | id, patient_id, practitioner_id, start_at, end_at, status, reason, created_at, updated_at |
| `appointment_history` | id, appointment_id (FK), action, actor_id, timestamp, note |

### notification_db
| Table | Colonnes principales |
|---|---|
| `notifications` | id, user_id, channel (email/sms), template, recipient, subject, body, payload (JSONB), status, error, created_at, sent_at |

### analytics_db
Réservé pour des agrégats matérialisés (`daily_stats`). Dans la version actuelle, analytics-service lit directement depuis `appointment_db` via SQL agrégé (simplification étudiante).

---

## 4. Communication entre services

| Source | Destination | Endpoint | Synchronicité | Authentification |
|---|---|---|---|---|
| practitioner-service | appointment-service | `GET /appointments/internal/booked` | Sync HTTP | aucune (interne) |
| appointment-service | practitioner-service | `GET /practitioners/{id}` | Sync HTTP | aucune (read public) |
| appointment-service | patient-service | `GET /patients/{id}` | Sync HTTP | JWT propagé |
| appointment-service | notification-service | `POST /notifications/send` | Fire-and-forget | aucune (interne) |
| analytics-service | postgres (appointment_db) | SQL direct | Sync DB | DB credentials |

**Pourquoi REST synchrone ?** Pour un projet étudiant, REST est suffisant et facile à débugger via Postman. Un bus d'événements (RabbitMQ) serait l'évolution naturelle pour découpler la chaîne appointment → notification.

---

## 5. Sécurité

### Émission des tokens
- `auth-service` est le seul émetteur.
- Algorithme: **HS256** avec un secret partagé (`JWT_SECRET`).
- Access token: 60 min. Refresh token: 7 jours, persisté en DB pour révocation.

### Validation
Chaque service décode le token localement avec le même secret — aucun appel réseau supplémentaire. Cela permet:
- Latence minimale
- Résilience: si auth-service tombe, les sessions actives continuent
- Inconvénient: pas de révocation immédiate des access tokens (acceptable pour la durée courte)

### Rôles & RBAC
4 rôles: `patient`, `practitioner`, `secretary`, `admin`.
Décorateurs `require_roles(...)` aux endpoints sensibles:
- Création profil patient/practitioner: rôle correspondant requis
- Liste de tous les patients: `practitioner | secretary | admin`
- Statistiques détaillées: `secretary | admin` ou `admin`
- Désactivation utilisateur: `admin`

---

## 6. Détection de conflits (appointment-service)

Lors d'un `POST /appointments` ou `PUT /appointments/{id}`:

```sql
SELECT EXISTS(
  SELECT 1 FROM appointments
  WHERE practitioner_id = :pid
    AND status IN ('scheduled','confirmed')
    AND start_at < :end_at
    AND end_at   > :start_at
    AND id != :exclude_id
)
```

Cette condition (`start_at < end & end_at > start`) détecte tout chevauchement temporel.

**Évolution possible:** ajouter une contrainte `EXCLUDE` PostgreSQL avec `tstzrange` pour empêcher les conflits au niveau DB:
```sql
ALTER TABLE appointments
  ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (
    practitioner_id WITH =,
    tstzrange(start_at, end_at, '[)') WITH &&
  ) WHERE (status IN ('scheduled','confirmed'));
```

---

## 7. Disponibilités (practitioner-service)

Algorithme de génération des créneaux libres pour `GET /practitioners/{id}/availability?date_from=&date_to=`:

```
slots = []
booked = fetch_from_appointment_service(practitioner_id, date_from, date_to)

for day in [date_from .. date_to]:
    if override(day) is unavailable: continue
    for schedule in schedules where day_of_week == day.weekday():
        cursor = day.start_time
        while cursor + slot_duration <= day.end_time:
            slot = (cursor, cursor + slot_duration)
            if not overlaps_any(slot, booked):
                slots.append(slot)
            cursor += slot_duration
```

---

## 8. Décisions de conception

| Décision | Justification |
|---|---|
| Postgres unique avec 6 DB logiques | Économie de ressources, suffisant pour démo. La séparation logique préserve l'isolation. |
| Tables auto-créées via SQLAlchemy | Pas de gestion d'Alembic — délibéré pour simplifier le projet étudiant. |
| JWT décodé localement | Évite la dépendance forte à auth-service, latence faible. |
| Mailhog au lieu d'un vrai SMTP | Capture tous les emails sans config externe; UI web pour valider. |
| Notification fire-and-forget | Le RDV ne doit pas échouer si la notification plante. |
| analytics-service lit directement appointment_db | Simplification: SQL natif est plus puissant que REST pour des agrégats. |

---

## 9. Endpoints récapitulatifs

### auth-service (`/auth`, `/users`)
`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `GET /auth/verify`, `GET /users` (admin), `PATCH /users/{id}/disable` (admin)

### patient-service (`/patients`)
`POST /patients`, `GET /patients`, `GET /patients/me`, `GET /patients/{id}`, `PUT /patients/{id}`, `POST /patients/{id}/history`, `GET /patients/by-user/{user_id}`

### practitioner-service (`/practitioners`)
`POST /practitioners`, `GET /practitioners`, `GET /practitioners/{id}`, `PUT /practitioners/{id}`, `PUT /practitioners/{id}/schedule`, `GET /practitioners/{id}/schedule`, `POST /practitioners/{id}/overrides`, `GET /practitioners/{id}/availability`

### appointment-service (`/appointments`)
`POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/confirm`, `POST /{id}/no-show`, `POST /{id}/complete`, `GET /internal/booked`

### notification-service (`/notifications`)
`POST /notifications/send`, `GET /notifications`, `GET /notifications/{id}`

### analytics-service (`/stats`)
`GET /stats/practitioner/{id}`, `GET /stats/daily`, `GET /stats/no-shows`, `GET /stats/peak-hours`, `GET /stats/overview`
