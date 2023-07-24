# -*- coding: utf-8 -*-


from flask import Blueprint

bp_point = Blueprint('point', __name__, template_folder='templates', url_prefix='/point')
from .controllers import *
