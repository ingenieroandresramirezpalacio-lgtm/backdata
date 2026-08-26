"""
Configuracion central de la aplicacion.

Todo lo que cambia entre un computador de pruebas y el servidor real de la
fabrica (claves, host de la base de datos, duracion de la sesion) se lee
del archivo .env con pydantic-settings. En el codigo NUNCA hay contrasenas
escritas a mano.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Aplicacion ---
    app_name: str = "DATACONTROL"
    app_env: str = "development"
    tz: str = "America/Bogota"

    # --- Base de datos ---
    postgres_user: str = "datacontrol"
    postgres_password: str = "datacontrol"
    postgres_db: str = "datacontrol"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Seguridad (JWT) ---
    jwt_secret_key: str = "clave-de-desarrollo-cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # --- CORS ---
    # Se lee como texto separado por comas (ver la propiedad origenes_cors).
    # Si se declarara como list[str], pydantic-settings exigiria escribirlo
    # en el .env como una lista JSON, que es mucho mas incomodo de mantener.
    cors_origins: str = "http://localhost:4200"

    # --- Administrador inicial ---
    admin_username: str = "admin"
    admin_nombre_completo: str = "Administrador DATACONTROL"
    admin_password: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def origenes_cors(self) -> list[str]:
        """CORS_ORIGINS=a,b,c -> ["a", "b", "c"]."""
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]

    @property
    def database_url(self) -> str:
        """Cadena de conexion que usa SQLAlchemy para hablar con PostgreSQL."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def es_produccion(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Instancia unica de la configuracion (se lee del entorno una sola vez).
    Se expone como funcion para poder sustituirla en las pruebas.
    """
    return Settings()


settings = get_settings()
