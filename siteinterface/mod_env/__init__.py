# -*- coding: utf-8 -*-


from flask import Blueprint

bp_env = Blueprint('env', __name__, template_folder='templates', url_prefix='/env')
from .controllers import *
