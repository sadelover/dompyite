# -*- coding: utf-8 -*-


from flask import Blueprint

bp_fdd = Blueprint('fdd', __name__, template_folder='templates', url_prefix='/fdd')
from .controllers import *
