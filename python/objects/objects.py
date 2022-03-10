# -*- coding: cp1251 -*-

""" Описаны классы для работы с объектами """

from strutils import *

class singleton(object):
    """ singleton object """
    obj = None
    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = object.__new__(cls, *args, **kwargs)
            cls.obj.init_properties()
        return cls.obj

    def init_properties(self):
        pass

class singledict(dict):
    """ глобальный словарик """
    obj = None
    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = dict.__new__(cls, *args, **kwargs)
        return cls.obj

class deriveddict(singledict): pass

def get_method_desc(func):
    """ Описание метода класса """
    return "%s.%s" % (func.__class__.__name__, func.__name__)

# декоратор для логирования результатов функций
def log_method(func):
    def func_proxy(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            self.log(uformat(u'%s( %s ) -> %s', get_method_desc(func), self.format_args(*args, **kwargs), r))
    return func_proxy


STACK_FRAME, STACK_FILENAME, STACK_LINE_NUMBER, STACK_FUNCTION_NAME, STACK_LINES, STACK_INDEX = xrange(6)
FRAME_SECOND = 1
FRAME_THIRD = 2

class baseobject(object):

    verbose = False

    def __init__(self, *args, **kwargs):
        self.beforeInit(*args, **kwargs)
        self.initprops()
        self.setkwargs(**kwargs)
        self.afterInit(*args, **kwargs)
        if self.verbose and not self.log_object:
            self.log_init()
        self.finalizeInit(*args, **kwargs)

    def initprops(self):
        if not hasattr(self, 'aborted'):
            self.aborted = False
        if not hasattr(self, 'error_object'):
            self.error_object = None
        if not hasattr(self, 'log_object'):
            self.log_object = None

    def setkwargs(self, **kwargs):
        map(lambda key: setattr(self, key, kwargs[key]), kwargs.keys())

    def beforeInit(self, *args, **kwargs):
        pass

    def afterInit(self, *args, **kwargs):
        pass

    def finalizeInit(self, *args, **kwargs):
        pass

    def uformat(self, *args, **kwargs):
        return uformat(*args, **kwargs)

    def log_init(self):
        from gtd import process
        self.log_object = process.ProcessManager().info
        self.error_object = process.ProcessManager().exception

    def format_args(self, *args, **kwargs):
        return u', '.join([uformat(u'%s', arg) for arg in args] + [uformat(u'%s=%s', k, kwargs[k]) for k in kwargs.keys()])

    def log_args(self, *args, **kwargs):
        self.log(self.format_args(*args, **kwargs))

    def vlog(self, *args, **kwargs):
        """ verbose log """
        if self.verbose:
            self._log_whereami(FRAME_THIRD, *args, **kwargs)

    def log_stack(self):
        import inspect
        stack = inspect.stack()
        s = 'Log stack'
        for line in stack[1:]:
            s += '\n\t%s\t%s\t%s\t%s' % (line[3], line[2], line[1], line[4][0].strip())
        self.log(s)

    def _log_whereami(self, stack_deep, *args, **kwargs):
        import inspect
        uargs = self.format_args(*args, **kwargs)
        self.log(uformat(u'%s.%s( %s )', self.__class__.__name__, inspect.stack()[stack_deep][STACK_FUNCTION_NAME], uargs))

    def log_whereami(self, *args, **kwargs):
        self._log_whereami(FRAME_THIRD, *args, **kwargs)

    def log(self, message, *args, **kwargs):
        if self.log_object:
            return self.log_object(message, *args, **kwargs)
        return ''

    def log_error(self, e, func_desc = '', *args, **kwargs):
        if self.error_object:
            return self.error_object(e, func_desc, *args, **kwargs)
        return ''

    def get_referrers_info(self):
        import gc
        r = uformat('%d referrers: %d. ' % (id(self), len(gc.get_referrers(self)),))
        r += u', '.join((uformat(u'%s', type(obj).__name__) for obj in gc.get_referrers(self)))
        return r

    def log_errormessage(self, *args, **kwargs):
        return self.log(self.format_args(*args, **kwargs))

    def stop(self, expr = True):
        if expr and not self.aborted:
            self.aborted = True
            from debug import stop
            stop()


class maybe(object):
    def __init__(self, obj):
        self._obj = obj

    def __getattr__(self, item):
        r = getattr(self._obj, item, None)
        if r:
            return r
        else:
            return lambda *args, **kwargs: None

    def __setattr__(self, item, value):
        if item == '_obj':
            super(maybe, self).__setattr__(item, value)
        else:
            self._obj.__setattr__(item, value)


def test(*args, **kwargs):
    print "testing singleton"
    s1 = singleton()
    s2 = singleton()
    if s1 == s2:
        print "singleton test ok"
    else:
        print "singleton test failed"

    print "testing singlton dictionary"

    sd1 = singledict()
    sd2 = singledict()
    if sd1 == sd2:
        print "singledict equal test ok"
    else:
        print "singledict equal test failed"

    sd1['key'] = 'value'
    print "sd1['key']", sd1['key']
    print "sd2['key']", sd2['key']

    print "testing derived dict"

    dd = deriveddict()
    if sd1 == dd:
        print "singledict equal test failed"
    else:
        print "singledict equal test ok"

if __name__ == "__main__":
    test()
