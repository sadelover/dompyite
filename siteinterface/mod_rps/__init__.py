# -*- coding: utf-8 -*-


from flask import Blueprint

bp_rps = Blueprint('rps', __name__, template_folder='templates', url_prefix='/rps')
from .controllers import *