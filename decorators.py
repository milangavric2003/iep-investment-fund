from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, jwt_required


def role_required(required_role):
    def decorator(function):
        @jwt_required()
        @wraps(function)
        def wrapper(*args, **kwargs):
            if get_jwt().get("role") != required_role:
                # The project contract uses the same 401 response for missing and unauthorized roles.
                return jsonify(msg="Missing Authorization Header"), 401
            return function(*args, **kwargs)

        return wrapper

    return decorator