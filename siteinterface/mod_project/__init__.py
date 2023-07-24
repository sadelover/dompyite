# -*- coding: utf-8 -*-


from flask import Blueprint

bp_project = Blueprint('project', __name__, template_folder='templates', url_prefix='/project')
from .controllers import *
