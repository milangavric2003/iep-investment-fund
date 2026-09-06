from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, jwt_required


def role_required(required_role):
    def decorator(function):
        @jwt_required()
        @wraps(function)
        def wrapper(*args, **kwargs):
            if get_jwt().get("role") != required_role:
                return jsonify(message="Invalid role."), 403
            return function(*args, **kwargs)

        return wrapper

    return decorator