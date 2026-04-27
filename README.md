# Système de Gestion des Rendez-vous Médicaux

Microservices project — FastAPI · PostgreSQL · OAuth2/JWT · Docker.

---

## 1. Vue d'ensemble

Plateforme de prise de rendez-vous médicaux composée de **6 microservices** indépendants, chacun avec sa propre base de données logique, communiquant via REST.

| Service | Port | Rôle |
|---|---|---|
| `auth-service` | 8001 | JWT, rôles, login/register, OAuth2 |
| `patient-service` | 8002 | Profils patients, antécédents, préférences |
| `practitioner-service` | 8003 | Profils soignants, plannings, disponibilités |
| `appointment-service` | 8004 | Création / modification / annulation RDV, gestion conflits |
| `notification-service` | 8005 | Emails (Mailhog), SMS, rappels automatiques |
| `analytics-service` | 8006 | Taux de remplissage, no-shows, pics d'activité |

Infra: **Postgres 16** (multi-DB), **Mailhog** (capture des emails dev).

---

## 2. Démarrage rapide

```bash
# Cloner / récupérer le repo
cd "PROJETQADI 2"

# Copier le fichier d'environnement
cp .env.example .env

# Build + start
docker compose up -d --build

# Vérifier que tout tourne
docker compose ps
```

Une fois démarré:

| URL | Description |
|---|---|
| http://localhost:8001/docs | Swagger Auth |
| http://localhost:8002/docs | Swagger Patients |
| http://localhost:8003/docs | Swagger Practitioners |
| http://localhost:8004/docs | Swagger Appointments |
| http://localhost:8005/docs | Swagger Notifications |
| http://localhost:8006/docs | Swagger Analytics |
| http://localhost:8025 | Interface Mailhog (emails capturés) |

Pour arrêter: `docker compose down` (ajouter `-v` pour supprimer les volumes Postgres).

---

## 3. Tester avec Postman

1. Importer `postman/medical-rdv.postman_collection.json`
2. Importer `postman/medical-rdv.postman_environment.json`
3. Sélectionner l'environnement **Medical-RDV Local**
4. Exécuter les requêtes dans l'ordre des dossiers (1 → 7).

Les tokens JWT sont stockés automatiquement dans les variables d'environnement après chaque login.

### Scénario de test golden path

1. **1. Auth** → `Register Patient` puis `Register Practitioner` puis `Register Admin`
2. **1. Auth** → `Login Practitioner` (le token bascule en mode practitioner)
3. **3. Practitioner** → `Create Practitioner Profile` → `Set Weekly Schedule`
4. **1. Auth** → `Login Patient`
5. **2. Patient** → `Create Patient Profile`
6. **3. Practitioner** → `Get Availability` (vérifier les créneaux)
7. **4. Appointment** → `Book Appointment`
8. **4. Appointment** → `Conflict Test` (doit retourner 409)
9. **5. Notification** → vérifier l'email dans http://localhost:8025
10. **6. Analytics** (login admin) → `Practitioner Stats`

---

## 4. Architecture

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le diagramme complet et les flux de données.

---

## 5. Structure du projet

```
PROJETQADI 2/
├── docker-compose.yml
├── .env / .env.example
├── README.md
├── ARCHITECTURE.md
├── infra/
│   └── init-db.sh                # Crée les 6 bases au démarrage de Postgres
├── postman/
│   ├── medical-rdv.postman_collection.json
│   └── medical-rdv.postman_environment.json
└── services/
    ├── auth-service/
    ├── patient-service/
    ├── practitioner-service/
    ├── appointment-service/
    ├── notification-service/
    └── analytics-service/
```

Chaque service suit la même arborescence:
```
service-x/
├── Dockerfile
├── requirements.txt
└── app/
    ├── main.py            # bootstrap FastAPI
    ├── config.py          # settings (pydantic)
    ├── database.py        # SQLAlchemy engine/session
    ├── security.py        # JWT decode + role guards
    ├── models.py          # SQLAlchemy models
    ├── schemas.py         # Pydantic schemas
    └── routers/           # endpoints
```

---

## 6. Sécurité — JWT partagé

- L'**auth-service** émet les tokens (access + refresh) signés avec `JWT_SECRET` (HS256).
- Tous les autres services **décodent localement** les tokens avec le même secret — aucun aller-retour réseau pour valider.
- Quatre rôles: `patient`, `practitioner`, `secretary`, `admin`.
- Les endpoints sensibles utilisent `require_roles(...)` pour le contrôle d'accès.

---

## 7. Bases de données

Toutes les bases vivent dans une seule instance Postgres (séparation logique, simplifie le projet étudiant). Voir [ARCHITECTURE.md](ARCHITECTURE.md#bases-de-données) pour le schéma détaillé.

Connexion directe depuis l'hôte:
```bash
psql -h localhost -U postgres -d auth_db   # ou patient_db, etc.
```
(mot de passe: `postgres`)

---

## 8. Commandes utiles

```bash
# Logs d'un service
docker compose logs -f auth-service

# Redémarrer un seul service
docker compose restart appointment-service

# Reconstruire après changement de code
docker compose up -d --build patient-service

# Reset complet (efface les données)
docker compose down -v && docker compose up -d --build

# Shell dans un container
docker compose exec auth-service bash
```

---

## 9. Livrables

- ✅ **Diagramme d'architecture** + flux de données → `ARCHITECTURE.md`
- ✅ **Collection Postman** → `postman/`
- ✅ **docker-compose.yml** fonctionnel avec tous les services + Postgres + Mailhog
- ✅ **6 microservices** Python/FastAPI complets
- 📄 **Rapport PDF** → à générer depuis `ARCHITECTURE.md` (`pandoc ARCHITECTURE.md -o rapport.pdf`)

---

## 10. Améliorations possibles

- API Gateway (nginx ou Traefik) pour un point d'entrée unique
- Bus d'événements (RabbitMQ / Kafka) pour découpler appointment ↔ notification
- Frontend React minimal pour la démo
- Tests automatisés (pytest) avec fixtures et test DB
- CI GitHub Actions
- Observabilité: Prometheus + Grafana
- Migrations Alembic (actuellement `Base.metadata.create_all` au démarrage — suffisant pour le projet étudiant)
