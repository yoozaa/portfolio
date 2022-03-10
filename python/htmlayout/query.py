# -*- coding: cp1251 -*-

"""

    Манипуляции над деревом элементов в стиле jquery

"""

from gtd import system

from layout import *

class element_selector(baseobject):
    """ Выборка элементов из дерева, начиная с he, по различным условиям """
    def beforeInit(self, he, *args, **kwargs):
        super(element_selector, self).beforeInit(*args, **kwargs)
        self.he = he
        self.items = []
        self.first = False

    def get_root_element(self):
        return self.he

    def callback(self, he):
        """ Возвращает True если дальше перебирать не надо """
        self.items.append(he)
        return self.first

    def select(self, css_selector, first = False, *args, **kwargs):
        self.first = first
        self.items = []
        HTMLayoutSelectElements(self.get_root_element(), css_selector, self.callback)
        return self.items

    def visit(self, tag_name, attr_name = '', attr_value = '', depth = 0, first = False):
        self.first = first
        self.items = []
        HTMLayoutVisitElements(self.get_root_element(), tag_name, attr_name, attr_value, self.callback, depth)
        return self.items


class hwnd_element_selector(element_selector):
    """ Выборка относительно корневого элемента окна, определяемого hwnd """
    def beforeInit(self, hwnd, *args, **kwargs):
        super(hwnd_element_selector, self).beforeInit(HTMLayoutGetRootElement(hwnd), *args, **kwargs)


class query(baseobject):

    """ Запросы в стиле jQuery """

    stop_methods = (
        'find_nearest',
        'index',
        'get_attr',
        'get_style_attr',
        'get_state',
        'get_innertext',
        'get_value',
        'get_html',
        'get_checked',
        'get_enabled',
        'get_visible',
        'get_visited',
        'get_display',
        'get_type',
        )

    def beforeInit(self, hwnd, selector, *args, **kwargs):
        super(query, self).beforeInit(*args, **kwargs)
        self.hwnd = hwnd
        self.selector = selector
        self.objects = []
        self.first = False

    def get_selector_class(self):
        return hwnd_element_selector

    def afterInit(self, *args, **kwargs):
        super(query, self).afterInit(*args, **kwargs)
        if not self.objects and self.selector:
            self.objects = self.get_selector_class()(self.hwnd).select(self.selector, first = self.first)

    def __getattr__(self, attr):
        return attr in self.stop_methods and q_element_stop(self, attr) or q_element_attribute(self, attr)

    def test(self):
        system.showmessage('%d' % (len(self.objects)))
        return self

    def call(self, func, *args, **kwargs):
        for he in self.objects:
            func(he, *args, **kwargs)
        return self

    def count(self):
        return len(self.objects)

class element_query(query):
    """ Действия над отдельными элементами hwnd = he """
    def get_selector_class(self):
        return element_selector


class q_element_attribute(baseobject):

    def beforeInit(self, query, attrname, *args, **kwargs):
        self.query = query
        self.attrname = attrname
        self.stop_on_first = False

    def __call__(self, *args, **kwargs):
        for he in self.query.objects:
            att = getattr(q_element(he), self.attrname)
            if callable(att):
                r = att(*args, **kwargs)
                if self.stop_on_first:
                    return r
        return self.query


class q_element_stop(q_element_attribute):

    def beforeInit(self, *args, **kwargs):
        super(q_element_stop, self).beforeInit(*args, **kwargs)
        self.stop_on_first = True


class q_element(element):

    def set_state(self, *args, **kwargs):
        super(q_element, self).set_state(*args, **kwargs)
        return self

    def set_attr(self, *args, **kwargs):
        super(q_element, self).set_attr(*args, **kwargs)
        return self

    def create_element(self, *args, **kwargs):
        super(q_element, self).create_element(*args, **kwargs)
        return self

    def iif(self, cond):
        return iif_element(cond, self)

    def css(self, css):
        map(lambda key: self.set_style_attr(key, css[key]), css)
        return self


class iif_element(object):

    def __init__(self, cond, element):
        self.cond = cond
        self.element = element

    def __getattr__(self, attr):
        return self.cond and getattr(self.element, attr) or self.pass_call

    def pass_call(self, *args, **kwargs):
        return self.element

