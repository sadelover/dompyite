# -*- coding: utf-8 -*-
from flask import Blueprint

bp_modscan = Blueprint('modscan', __name__, template_folder='templates', url_prefix='/modscan')
from .controllers import *
