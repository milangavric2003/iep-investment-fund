from datetime import datetime, timezone

from fund_helpers import mongo_database


def seed_assets():
    assets = [
        {
            "demo_key": "government-bond",
            "name": "Government Bond",
            "categories": ["fixed-income", "government"],
            "buying_price": 10000,
            "buying_date": datetime(2026, 1, 10, tzinfo=timezone.utc),
            "selling_price": 12000,
            "selling_date": datetime(2026, 5, 10, tzinfo=timezone.utc),
            "info": {
                "issuer": "Example State",
                "rating": {"value": "AAA"},
            },
        },
        {
            "demo_key": "solar-company",
            "name": "Solar Company Shares",
            "categories": ["equity", "renewable-energy"],
            "buying_price": 7500,
            "buying_date": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "info": {
                "ticker": "SOLR",
                "risk": {"score": 4},
            },
        },
    ]

    for asset in assets:
        mongo_database.assets.update_one(
            {"demo_key": asset["demo_key"]},
            {"$set": asset},
            upsert=True,
        )


if __name__ == "__main__":
    seed_assets()