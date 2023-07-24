# -*- coding: utf-8 -*-


from flask import Blueprint

bp_care = Blueprint('care', __name__, template_folder='templates', url_prefix='/care')
from .controllers import *
