from datetime import datetime, timezone
import json
from uuid import UUID

from bson import ObjectId
from bson.json_util import dumps
from pymongo import MongoClient
from redis import Redis

from fund_configuration import FundConfiguration


mongo_client = MongoClient(FundConfiguration.MONGO_URL)
mongo_database = mongo_client[FundConfiguration.MONGO_DATABASE]
redis_client = Redis(
    host=FundConfiguration.REDIS_HOST,
    port=FundConfiguration.REDIS_PORT,
    db=FundConfiguration.REDIS_DB,
    decode_responses=True,
)
ORDER_INDEX_KEY = "fund:orders:pending"


def parse_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


def parse_iso_datetime(value):
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialize_document(document):
    return dumps(document, separators=(",", ":"))


def asset_to_response(asset):
    response = {
        "id": str(asset["_id"]),
        "name": asset["name"],
        "categories": asset["categories"],
        "buying_date": asset["buying_date"].isoformat().replace("+00:00", "Z"),
        "buying_price": asset["buying_price"],
        "info": asset["info"],
    }

    if "selling_date" in asset:
        response["selling_date"] = asset["selling_date"].isoformat().replace(
            "+00:00", "Z"
        )
    if "selling_price" in asset:
        response["selling_price"] = asset["selling_price"]

    return response


def order_key(order_uuid):
    return f"fund:orders:{order_uuid}"


def store_order(order):
    # The order document and index entry are written in one Redis transaction.
    with redis_client.pipeline(transaction=True) as pipeline:
        pipeline.set(order_key(order["uuid"]), json.dumps(order))
        pipeline.sadd(ORDER_INDEX_KEY, order["uuid"])
        pipeline.execute()


def get_order(order_uuid):
    try:
        UUID(order_uuid)
    except (TypeError, ValueError, AttributeError):
        return None

    value = redis_client.get(order_key(order_uuid))
    return json.loads(value) if value is not None else None


def remove_order(order_uuid):
    with redis_client.pipeline(transaction=True) as pipeline:
        pipeline.delete(order_key(order_uuid))
        pipeline.srem(ORDER_INDEX_KEY, order_uuid)
        pipeline.execute()


def get_pending_orders():
    order_uuids = sorted(redis_client.smembers(ORDER_INDEX_KEY))
    orders = []
    for order_uuid in order_uuids:
        order = get_order(order_uuid)
        if order is not None:
            orders.append(order)
        else:
            redis_client.srem(ORDER_INDEX_KEY, order_uuid)
    return orders