# -*- coding: utf-8 -*-

from flask import Blueprint

bp_fix = Blueprint('fix', __name__, template_folder='templates', url_prefix='/fix')
from .controllers import *