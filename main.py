from email_validator import EmailNotValidError, validate_email
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from configuration import Configuration
from models import User, database


application = Flask(__name__)
application.config.from_object(Configuration)
database.init_app(application)
JWTManager(application)


def missing_field(payload, field_name):
    return field_name not in payload or payload[field_name] == ""


def invalid_email(email):
    if not isinstance(email, str) or len(email) > 256:
        return True

    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return True
    return False


@application.route("/register", methods=["POST"])
def register():
    # Safely extract JSON without throwing a 400 exception on bad input
    payload = request.get_json(silent=True) or {}

    for field_name in ("forename", "surname", "email", "password"):
        if missing_field(payload, field_name):
            return jsonify(message=f"Field {field_name} is missing."), 400

    if invalid_email(payload["email"]):
        return jsonify(message="Invalid email."), 400

    password = payload["password"]
    if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
        return jsonify(message="Invalid password."), 400

    if User.query.filter_by(email=payload["email"]).first() is not None:
        return jsonify(message="Email already exists."), 400

    user = User(
        forename=payload["forename"],
        surname=payload["surname"],
        email=payload["email"],
        password_hash=generate_password_hash(password),
        role="EMPLOYEE",
    )
    database.session.add(user)
    database.session.commit()
    return "", 200


@application.route("/login", methods=["POST"])
def login():
    # Safely extract JSON without throwing a 400 exception on bad input
    payload = request.get_json(silent=True) or {}

    for field_name in ("email", "password"):
        if missing_field(payload, field_name):
            return jsonify(message=f"Field {field_name} is missing."), 400

    if invalid_email(payload["email"]):
        return jsonify(message="Invalid email."), 400

    user = User.query.filter_by(email=payload["email"]).first()
    if user is None or not isinstance(payload["password"], str) or not check_password_hash(
        user.password_hash, payload["password"]
    ):
        return jsonify(message="Invalid credentials."), 400

    claims = {
        "forename": user.forename,
        "surname": user.surname,
        "role": user.role,
    }
    access_token = create_access_token(identity=user.email, additional_claims=claims)
    return jsonify(accessToken=access_token), 200


@application.route("/delete", methods=["POST"])
@jwt_required()
def delete_user():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify(message="Unknown user."), 400

    database.session.delete(user)
    database.session.commit()
    return "", 200


@application.route("/", methods=["GET"])
def health_check():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000)
