from flask import Flask
from flask_migrate import Migrate

from configuration import Configuration
from models import database


application = Flask(__name__)
application.config.from_object(Configuration)
database.init_app(application)
Migrate(application, database)
