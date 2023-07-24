from flask import Flask
from flask_cors import CORS
from flask_compress import Compress
from siteinterface.config import config

compress = Compress()

app = Flask(__name__)

compress.init_app(app)

CORS(app, resources={r"/*": {"origins": "*"}})

app.config.from_object(config)

app.config.from_envvar('FLASKR_SETTINGS', silent=True)