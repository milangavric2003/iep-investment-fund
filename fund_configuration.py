import os


class FundConfiguration:
    MONGO_URL = os.getenv(
        "MONGO_URL",
        "mongodb://root:example@localhost:27017/?authSource=admin",
    )
    MONGO_DATABASE = os.getenv("MONGO_DATABASE", "investment_fund")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "development-secret-key-with-at-least-32-bytes"
    )
