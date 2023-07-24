# -*- encoding=utf-8 -*-
__author__ = 'yan'

#单例类，无需维护
class Singleton(object):

    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls, *args, **kw)
        return cls._instance