from pathlib import Path

from sqlalchemy import text

from models import database
from migrate import application


def seed_database():
    statements = Path(__file__).with_name("seed.sql").read_text(encoding="utf-8")
    with application.app_context():
        database.session.execute(text(statements))
        database.session.commit()


if __name__ == "__main__":
    seed_database()