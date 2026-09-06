import os
from datetime import timedelta


class Configuration:
    database_url = os.getenv("DATABASE_URL", "localhost")
    database_username = os.getenv("DATABASE_USERNAME", "root")
    database_password = os.getenv("DATABASE_PASSWORD", "root")
    database_name = os.getenv("DATABASE_NAME", "investment_fund")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        (
        f"mysql+pymysql://{database_username}:{database_password}"
        f"@{database_url}/{database_name}"
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "development-secret-key-with-at-least-32-bytes"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)