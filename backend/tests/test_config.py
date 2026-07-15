from __future__ import annotations

import pytest
from app.core.config import Settings
from sqlalchemy.engine import make_url


def test_mysql_url_safely_encodes_reserved_password_characters() -> None:
    settings = Settings(
        _env_file=None,
        database_url="",
        db_backend="mysql",
        mysql_user="campus_user",
        mysql_password="sample@password:/?#",
        mysql_database="campus_qa",
    )

    url = make_url(settings.sqlalchemy_database_url)

    assert url.drivername == "mysql+pymysql"
    assert url.username == "campus_user"
    assert url.password == "sample@password:/?#"
    assert url.database == "campus_qa"
    assert url.query["charset"] == "utf8mb4"


def test_mysql_runtime_rejects_missing_secrets() -> None:
    settings = Settings(
        _env_file=None,
        database_url="",
        db_backend="mysql",
        mysql_password="",
        jwt_secret="development-only-change-me",
    )

    with pytest.raises(RuntimeError, match="MYSQL_PASSWORD, JWT_SECRET"):
        settings.validate_runtime()


def test_mysql_runtime_rejects_template_placeholders() -> None:
    settings = Settings(
        _env_file=None,
        database_url="",
        db_backend="mysql",
        mysql_password="replace-with-your-local-password",
        jwt_secret="replace-with-a-long-random-string",
    )

    with pytest.raises(RuntimeError, match="MYSQL_PASSWORD, JWT_SECRET"):
        settings.validate_runtime()


def test_model_device_accepts_cross_platform_choices() -> None:
    assert Settings(_env_file=None, model_device="auto").model_device == "auto"
    assert Settings(_env_file=None, model_device="cpu").model_device == "cpu"
    assert Settings(_env_file=None, model_device="cuda").model_device == "cuda"
