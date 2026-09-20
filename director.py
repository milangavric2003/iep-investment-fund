from datetime import datetime, timezone
from uuid import UUID

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager

from decorators import role_required
from fund_configuration import FundConfiguration
from fund_helpers import (
    asset_to_response,
    get_order,
    get_pending_orders,
    mongo_database,
    remove_order,
)


application = Flask(__name__)
application.config.from_object(FundConfiguration)
JWTManager(application)


@application.route("/pending_orders", methods=["GET"])
@role_required("DIRECTOR")
def pending_orders():
    return jsonify(orders=get_pending_orders()), 200


@application.route("/decision", methods=["POST"])
@role_required("DIRECTOR")
def decision():
    payload = request.get_json(silent=True) or {}

    if "uuid" not in payload or payload["uuid"] == "":
        return jsonify(message="Field uuid is missing."), 400

    try:
        UUID(payload["uuid"])
    except (TypeError, ValueError, AttributeError):
        return jsonify(message="Invalid uuid."), 400

    order = get_order(payload["uuid"])
    if order is None:
        return jsonify(message="Invalid uuid."), 400

    if "approved" not in payload:
        return jsonify(message="Field approved is missing."), 400
    if not isinstance(payload["approved"], bool):
        return jsonify(message="Invalid decision."), 400

    if not payload["approved"]:
        remove_order(payload["uuid"])
        return "", 200

    approval_time = datetime.now(timezone.utc)
    if order["order_type"] == "BUY":
        mongo_database.assets.insert_one(
            {
                "name": order["name"],
                "categories": order["categories"],
                "buying_price": order["buying_price"],
                "buying_date": approval_time,
                "info": order["info"],
            }
        )
    elif order["order_type"] == "SELL":
        from bson import ObjectId

        update_result = mongo_database.assets.update_one(
            {"_id": ObjectId(order["id"])},
            {
                "$set": {
                    "selling_price": order["selling_price"],
                    "selling_date": approval_time,
                }
            },
        )
        if update_result.matched_count == 0:
            return jsonify(message="Invalid id."), 400
    else:
        return jsonify(message="Invalid order."), 400

    # Redis is removed only after MongoDB succeeds, so a failed write can be retried.
    remove_order(payload["uuid"])
    return "", 200


@application.route("/report", methods=["GET"])
@role_required("DIRECTOR")
def report():
    pipeline = [
        {"$unwind": "$categories"},
        {
            "$group": {
                "_id": "$categories",
                "spent": {"$sum": "$buying_price"},
                "earned": {
                    "$sum": {"$cond": [{"$ne": [{"$type": "$selling_price"}, "missing"]}, "$selling_price", 0]}
                },
            }
        },
        {"$sort": {"earned": -1, "spent": 1, "_id": 1}},
        {
            "$project": {
                "_id": 0,
                "category": "$_id",
                "spent": 1,
                "earned": 1,
            }
        },
    ]
    return jsonify(statistics=list(mongo_database.assets.aggregate(pipeline))), 200

# # returns the biggest profit (selling_price - buying_price) of all selled assets (with selling_price lte 175000)
# @application.route("/getBiggestProfit", methods=["GET"])
# @role_required("DIRECTOR")
# def getBiggestProfit():
#     assets = mongo_database.assets.find({"selling_price": {"$lte": 175000 } }, {"_id": 1, "buying_price": 1, "selling_price": 1})
#     if not assets:
#         return jsonify(message="No solid assets found."), 400

#     assetMax = assets[0].get("selling_price", 0) - assets[0].get("buying_price", 0)
#     assetMaxObj = assets[0]
#     for asset in assets:
#         if asset.get("selling_price", 0) - asset.get("buying_price", 0) > assetMax:
#             assetMax = asset.get("selling_price", 0) - asset.get("buying_price", 0)
#             assetMaxObj = asset

#     result = [{"id": str(assetMaxObj.get("_id")), "profit": assetMax}]

#     return jsonify(stat = result), 200

@application.route("/getAverageProfit", methods=["GET"])
#@role_required("DIRECTOR")
def getAverageProfit():
    from bson import ObjectId
    pipeline = [
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "selling_price": 1,
                "buying_price": 1,
                "profit": {"$subtract": ["$selling_price", "$buying_price"]},
            }
        }
    ]
    return jsonify(statistics=list(mongo_database.assets.aggregate(pipeline))), 200

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5002)