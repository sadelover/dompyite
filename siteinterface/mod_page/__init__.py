# -*- coding: utf-8 -*-


from flask import Blueprint

bp_page = Blueprint('page', __name__, template_folder='templates', url_prefix='/page')
from .controllers import *
