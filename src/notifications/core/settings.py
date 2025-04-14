import os
from pathlib import Path

from fastapi_mail import ConnectionConfig
from pydantic import BaseModel


class Paths:
    ROOT_DIR_SRC: Path = Path(__file__).parents[2]
    PATH_TO_BASE_FOLDER = ROOT_DIR_SRC.parents[1]
    TEMPLATE_DIR: Path = ROOT_DIR_SRC / "notifications" / "core" / "templates"


class RunConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8003


class ApiPrefix(BaseModel):
    prefix: str = "/api/notifications"
    v1_prefix: str = "/v1"
    internal: str = "/internals"
    healthcheck: str = "/healthcheck"
    emails: str = "/emails"
    confirm_email: str = "/confirmation"
    recovery_email: str = "/recovery"


class FastMailConfig(BaseModel):
    USERNAME: str = os.getenv("MAIL_USERNAME")
    PASSWORD: str = os.getenv("MAIL_PASSWORD")
    FROM: str = os.getenv("MAIL_FROM")
    PORT: int = int(os.getenv("MAIL_PORT"))
    SERVER: str = os.getenv("MAIL_SERVER")
    STARTTLS: bool = bool(int(os.getenv("MAIL_STARTTLS")))
    SSL_TLS: bool = bool(int(os.getenv("MAIL_SSL_TLS")))
    FROM_NAME: str = os.getenv("MAIL_FROM_NAME")
    USE_CREDENTIALS: bool = bool(os.getenv("MAIL_USE_CREDENTIALS"))
    VALIDATE_CERTS: bool = bool(os.getenv("MAIL_VALIDATE_CERTS"))

    @property
    def conf(self) -> ConnectionConfig:
        return ConnectionConfig(
            MAIL_USERNAME=self.USERNAME,
            MAIL_PASSWORD=self.PASSWORD,
            MAIL_FROM=self.FROM,
            MAIL_PORT=self.PORT,
            MAIL_SERVER=self.SERVER,
            MAIL_STARTTLS=self.STARTTLS,
            MAIL_FROM_NAME=self.FROM_NAME,
            MAIL_SSL_TLS=self.SSL_TLS,
            USE_CREDENTIALS=self.USE_CREDENTIALS,
            VALIDATE_CERTS=self.VALIDATE_CERTS,
        )


class EmailSubjects(BaseModel):
    CONFIRM: str = "ПИСЬМО ДЛЯ ВЕРИФИКАЦИИ ПОЧТЫ СЕРВИСА КРУТОЙ БОБР"
    RECOVERY: str = "ПИСЬМО ДЛЯ ВОССТАНОВЛЕНИЯ ПАРОЛЯ СЕРВИСА КРУТОЙ БОБР"


class MailTemplate(BaseModel):
    CONFIRM: str = "confirm_email.html"
    RECOVERY: str = "reset_pass.html"


class RabbitMQConfig(BaseModel):
    USERNAME: str = os.getenv("RABBIT_USERNAME")
    PASSWORD: str = os.getenv("RABBIT_PASSWORD")
    HOST: str = os.getenv("RABBIT_HOST")
    PORT: int = int(os.getenv("RABBIT_PORT"))
    VHOST: str = os.getenv("RABBIT_VHOST")
    TIMEOUT: int = int(os.getenv("RABBIT_TIMEOUT"))

    RABBIT_EMAIL_QUEUE: str = os.getenv("RABBIT_EMAIL_QUEUE")
    PREFETCH_COUNT: int = int(os.getenv("RABBIT_PREFETCH_COUNT", "10"))

    @property
    def url(self) -> str:
        return f"amqp://{self.USERNAME}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.VHOST}"


class Settings:
    mode: str = os.getenv("MODE")
    api_key: str = os.getenv("API_KEY")
    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()
    fast_mail: FastMailConfig = FastMailConfig()
    subjects: EmailSubjects = EmailSubjects()
    templates: MailTemplate = MailTemplate()
    paths: Paths = Paths()
    rmq: RabbitMQConfig = RabbitMQConfig()


def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
