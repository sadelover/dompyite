# -*- coding: utf-8 -*-


from flask import Blueprint

bp_equipment = Blueprint('equipment', __name__, template_folder='templates', url_prefix='/equipment')
from .controllers import *
