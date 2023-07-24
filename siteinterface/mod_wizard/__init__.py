# -*- coding: utf-8 -*-
from flask import Blueprint


bp_wizard = Blueprint('wizard', __name__, template_folder='templates', url_prefix='/wizard')
from .controllers import *