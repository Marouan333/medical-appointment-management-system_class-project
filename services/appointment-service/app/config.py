from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/appointment_db"
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    SERVICE_NAME: str = "appointment-service"

    PATIENT_SERVICE_URL: str = "http://patient-service:8000"
    PRACTITIONER_SERVICE_URL: str = "http://practitioner-service:8000"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8000"


settings = Settings()
