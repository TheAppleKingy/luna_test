from pydantic_settings import BaseSettings


class DBConfig(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_db: str

    @property
    def conn_url(self):
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:5432/{self.postgres_db}"


class RabbitConfig(BaseSettings):
    rabbitmq_default_user: str
    rabbitmq_default_pass: str
    rabbitmq_host: str
    queue_name: str = "payments.new"

    @property
    def conn_url(self):
        return f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@{self.rabbitmq_host}"


class AppConfig(BaseSettings):
    api_key: str
    outbox_send_limit: int
