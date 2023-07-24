# -*- coding: utf-8 -*-


from flask import Blueprint

bp_system = Blueprint('system', __name__, template_folder='templates', url_prefix='/system')
from .controllers import *
