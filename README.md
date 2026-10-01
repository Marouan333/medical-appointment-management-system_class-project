# Medical Appointment Management System

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=flat&logo=json-web-tokens&logoColor=white)

Medical appointment booking platform built as 6 independent FastAPI microservices with PostgreSQL, OAuth2/JWT authentication, and Docker.

---

## Architecture

6 microservices, each with its own logical database, communicating via REST.

| Service | Port | Role |
|---------|------|------|
| `auth-service` | 8001 | JWT, roles, login/register, OAuth2 |
| `patient-service` | 8002 | Patient profiles, history, preferences |
| `practitioner-service` | 8003 | Practitioner profiles, schedules, availability |
| `appointment-service` | 8004 | Create / update / cancel appointments, conflict management |
| `notification-service` | 8005 | Emails (Mailhog), SMS, automatic reminders |
| `analytics-service` | 8006 | Fill rate, no-shows, activity peaks |

Infrastructure: **PostgreSQL 16** (multi-DB), **Mailhog** (dev email capture).

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Marouan333/medical-appointment-management-system
cd medical-appointment-management-system

# Copy environment file
cp .env.example .env

# Build and start all services
docker compose up -d --build

# Verify services are running
docker compose ps
```

Once running:

| URL | Description |
|-----|-------------|
| http://localhost:8001/docs | Swagger -- Auth |
| http://localhost:8002/docs | Swagger -- Patients |
| http://localhost:8003/docs | Swagger -- Practitioners |
| http://localhost:8004/docs | Swagger -- Appointments |
| http://localhost:8005/docs | Swagger -- Notifications |
| http://localhost:8006/docs | Swagger -- Analytics |
| http://localhost:8025 | Mailhog (captured emails) |

To stop: `docker compose down` (add `-v` to also remove PostgreSQL volumes).

---

## Testing with Postman

1. Import `postman/medical-rdv.postman_collection.json`
2. Import `postman/medical-rdv.postman_environment.json`
3. Select the **Medical-RDV Local** environment
4. Run requests in folder order (1 to 7) -- JWT tokens are stored automatically

---

## Key Features

- OAuth2 with JWT access and refresh tokens
- Role-based access control (patient, practitioner, admin)
- Conflict detection for overlapping appointments
- Automatic email and SMS reminders via the notification service
- Analytics dashboard: fill rate, no-show rate, peak hours
