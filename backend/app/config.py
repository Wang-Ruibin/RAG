"""应用程序配置管理"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MySQL 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "campus_qa"

    # Redis 缓存配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # JWT 认证配置
    JWT_SECRET_KEY: str = "campus-qa-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24小时

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]

    # Redis 降级配置
    REDIS_FALLBACK_TO_FAKE: bool = True  # 真实 Redis 不可用时降级到 fakeredis

    # 缓存配置
    CACHE_EXPIRE_SECONDS: int = 600  # 默认缓存10分钟
    CACHE_KEY_PREFIX: str = "campus:qa:"

    # 数据库连接字符串 (由上述字段组合)
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
