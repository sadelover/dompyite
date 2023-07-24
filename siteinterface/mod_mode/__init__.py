# -*- coding: utf-8 -*-


from flask import Blueprint

bp_mode = Blueprint('mode', __name__, template_folder='templates', url_prefix='/mode')
from .controllers import *
