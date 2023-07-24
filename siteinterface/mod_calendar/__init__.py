# -*- coding: utf-8 -*-


from flask import Blueprint

bp_calendar = Blueprint('calendar', __name__, template_folder='templates', url_prefix='/calendar')
from .controllers import *
