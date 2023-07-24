# -*- coding: utf-8 -*-
from flask import Blueprint


bp_network = Blueprint('network', __name__, template_folder='templates', url_prefix='/network')
from .controlllers import *

