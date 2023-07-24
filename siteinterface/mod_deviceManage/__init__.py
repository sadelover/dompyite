# -*- coding: utf-8 -*-
from flask import Blueprint

bp_deviceManage = Blueprint('deviceManage', __name__, template_folder='templates', url_prefix='/deviceManage')
from .controllers import *

