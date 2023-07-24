# -*- coding: utf-8 -*-


from flask import Blueprint

bp_logic = Blueprint('logic', __name__, template_folder='templates', url_prefix='/logic')
from .controllers import *
