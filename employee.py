import re
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager

from decorators import role_required
from fund_configuration import FundConfiguration
from fund_helpers import (
    asset_to_response,
    mongo_database,
    parse_iso_datetime,
    parse_object_id,
    store_order,
)


application = Flask(__name__)
application.config.from_object(FundConfiguration)
JWTManager(application)

INFO_OPERATORS = {
    "eq": "$eq",
    "ne": "$ne",
    "gt": "$gt",
    "gte": "$gte",
    "lt": "$lt",
    "lte": "$lte",
}


def build_info_filter(raw_filter):
    if not isinstance(raw_filter, dict):
        return None

    field = raw_filter.get("field")
    operator = raw_filter.get("operator")
    if (
        not isinstance(field, str)
        or not field
        or not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", field)
        or operator not in INFO_OPERATORS
        or "value" not in raw_filter
    ):
        return None

    # Restrict dotted paths to the info document and map public operators explicitly.
    return {f"info.{field}": {INFO_OPERATORS[operator]: raw_filter["value"]}}


@application.route("/search", methods=["POST"])
@role_required("EMPLOYEE")
def search_assets():
    payload = request.get_json(silent=True) or {}
    query = {}

    if "name" in payload:
        if not isinstance(payload["name"], str) or len(payload["name"]) > 256:
            return jsonify(message="Invalid name."), 400
        query["name"] = {"$regex": re.escape(payload["name"]), "$options": "i"}

    if "category" in payload:
        if not isinstance(payload["category"], str) or len(payload["category"]) > 256:
            return jsonify(message="Invalid category."), 400
        query["categories"] = payload["category"]

    if "buying_date" in payload:
        buying_date = parse_iso_datetime(payload["buying_date"])
        if buying_date is None:
            return jsonify(message="Invalid buying date."), 400
        query["buying_date"] = {"$gt": buying_date}

    if "selling_date" in payload:
        selling_date = parse_iso_datetime(payload["selling_date"])
        if selling_date is None:
            return jsonify(message="Invalid selling date."), 400
        query["selling_date"] = {"$exists": True, "$lt": selling_date}

    if "info_filters" in payload:
        if not isinstance(payload["info_filters"], list):
            return jsonify(message="Invalid info filters."), 400
        for raw_filter in payload["info_filters"]:
            info_filter = build_info_filter(raw_filter)
            if info_filter is None:
                return jsonify(message="Invalid info filter."), 400
            query.update(info_filter)

    assets = mongo_database.assets.find(query).sort("_id", 1)
    return jsonify(assets=[asset_to_response(asset) for asset in assets]), 200


@application.route("/create_buy_order", methods=["POST"])
@role_required("EMPLOYEE")
def create_buy_order():
    payload = request.get_json(silent=True) or {}
    for field_name in ("name", "categories", "buying_price", "info"):
        if field_name not in payload or payload[field_name] == "":
            return jsonify(message=f"Field {field_name} is missing."), 400

    categories = payload["categories"]
    if not isinstance(categories, list) or not categories:
        return jsonify(message="Categories list is empty."), 400
    if any(
        not isinstance(category, str) or not category or len(category) > 256
        for category in categories
    ):
        return jsonify(message="Invalid categories."), 400

    if not isinstance(payload["name"], str) or len(payload["name"]) > 256:
        return jsonify(message="Invalid name."), 400
    if not isinstance(payload["info"], dict):
        return jsonify(message="Invalid info."), 400

    buying_price = payload["buying_price"]
    if (
        isinstance(buying_price, bool)
        or not isinstance(buying_price, (int, float))
        or buying_price <= 0
    ):
        return jsonify(message="Invalid buying price."), 400

    order = {
        "uuid": str(uuid4()),
        "order_type": "BUY",
        "name": payload["name"],
        "categories": categories,
        "info": payload["info"],
        "buying_price": buying_price,
    }
    store_order(order)
    return "", 200


@application.route("/create_sell_order", methods=["POST"])
@role_required("EMPLOYEE")
def create_sell_order():
    payload = request.get_json(silent=True) or {}
    for field_name in ("id", "selling_price"):
        if field_name not in payload or payload[field_name] == "":
            return jsonify(message=f"Field {field_name} is missing."), 400

    asset_id = parse_object_id(payload["id"])
    if asset_id is None or mongo_database.assets.find_one({"_id": asset_id}) is None:
        return jsonify(message="Invalid id."), 400

    selling_price = payload["selling_price"]
    if (
        isinstance(selling_price, bool)
        or not isinstance(selling_price, (int, float))
        or selling_price <= 0
    ):
        return jsonify(message="Invalid selling price."), 400

    order = {
        "uuid": str(uuid4()),
        "order_type": "SELL",
        "id": payload["id"],
        "selling_price": selling_price,
    }
    store_order(order)
    return "", 200

# # exercise - return number of assets from category
# @application.route("/numAssets/<category>", methods=["GET"])
# @role_required("EMPLOYEE")
# def numAssets(category):
#     query = {}
#     query["categories"] = category
#     numOfCategories = mongo_database.assets.count_documents(query)
#     return jsonify(message=f"Num of categories: {numOfCategories}"), 200
#     # return jsonify(message=f"Num of categories: "), 200


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5001)