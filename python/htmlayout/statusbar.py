# -*- coding: cp1251 -*-

"""

   statusbar для программы Декларант

"""

from layout import *
from document import *

class statusbar_manager(object):

    obj = None
    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = object.__new__(cls, *args, **kwargs)
            cls.obj.init_properties()
        return cls.obj

    def init_properties(self):
        self.bars = []

    def get_bar(self, status_id = -1):
        r = None
        if status_id == -1:
            if self.bars:
                return self.bars[0]
        else:
            a = [b for b in self.bars if status_id == b.status_id]
            if a:
                return a[0]
        return r

    def add_bar(self, bar):
        self.bars.append(bar)

    def delete_bar(self, bar):
        self.bars = [b for b in self.bars if b != bar]


class statusbar(html_document):

    def beforeInit(self, status_id, *args, **kwargs):
        super(statusbar, self).beforeInit(*args, **kwargs)
        self.status_id = status_id
        self.filename = 'decl://html/statusbar.html'
        self.focus_activecontrol = False

    def show(self, *args, **kwargs):
        super(statusbar, self).show(*args, **kwargs)
        statusbar_manager().add_bar(self)

    def close(self, *args, **kwargs):
        super(statusbar, self).close(*args, **kwargs)
        statusbar_manager().delete_bar(self)

    def show_element(self, element, *args, **kwargs):
        element.visibility = 'visible'

    def hide_element(self, element, *args, **kwargs):
        element.visibility = 'collapse'

    def step_value(self, element, *args, **kwargs):
        element['value'] = int(element['value'] or 0) + 1
        element.update()

    def set_innertext(self, element, *args, **kwargs):
        element.innertext = kwargs.get('text', '')
        element.update()

    def set_value(self, element, *args, **kwargs):
        element['value'] = kwargs.get('value', 0)
        element.update()

    def set_attr_value(self, element, *args, **kwargs):
        if 'attr_name' in kwargs:
            element.set_attr(kwargs['attr_name'], kwargs.get('attr_value', ''))

    def init_progress(self, caption, max_count):
        self.do_select_x(self.set_attr_value, 'div#progress1 progress', attr_name = 'maxvalue', attr_value = str(max_count))
        self.do_select_x(self.set_value, 'div#progress1 progress', value = 0)
        self.do_select_x(self.show_element, 'div#progress1')
        self.do_select_x(self.set_innertext, 'div#progress1 span', text = caption)
        self.correct_height()

    def deinit_progress(self):
        self.do_select_x(self.hide_element, 'div#progress1')
        self.correct_height()

    def step_progress(self):
        self.do_select_x(self.step_value, 'div#progress1 progress')
        self.correct_height()

    def init_progress_2(self, caption, max_count):
        self.do_select_x(self.set_attr_value, 'div#progress2 progress', attr_name = 'maxvalue', attr_value = str(max_count))
        self.do_select_x(self.set_value, 'div#progress2 progress', value = 0)
        self.do_select_x(self.show_element, 'div#progress2')
        self.do_select_x(self.set_innertext, 'div#progress2 span', text = caption)
        self.correct_height()

    def deinit_progress_2(self):
        self.do_select_x(self.hide_element, 'div#progress2')
        self.correct_height()

    def step_progress_2(self):
        self.do_select_x(self.step_value, 'div#progress2 progress')
        self.correct_height()

    def init_db_progress(self):
        self.set_db_status('', '')
        self.do_select_x(self.show_element, 'div#db_progress')
        self.correct_height()

    def deinit_db_progress(self):
        self.do_select_x(self.hide_element, 'div#db_progress')
        self.correct_height()

    def set_db_status(self, tblname, message):
        self.do_select_x(self.set_innertext, 'div#db_progress span#tblname', text = tblname)
        self.do_select_x(self.set_innertext, 'div#db_progress span#db_message', text = message)
        self.correct_height()

    def set_status(self, status):
        if not status:
            status = '&nbsp;'
        self.do_select(lambda e: e.set_html(status), 'div#status')
        self.correct_height()

    def correct_height(self):
        self.commit_updates()
        self.refresh('height', self.get_intrinsic_height())

    def create_custom_div(self, div_id):
        area = self.find_first('div#custom_area')
        try:
            if area:
                div = element().create_element('div', None, area)
                div['ID'] = div_id
                area.visibility = 'visible'
                return div
        finally:
            del area

    def remove_custom_div(self, div_id):
        area = self.find_first('div#custom_area')
        try:
            if area:
                div = area.find_first('div#%s' % (div_id))
                try:
                    if div:
                        div.delete()
                finally:
                    del div
                area.visibility = 'collapse'
        finally:
            del area

    def document_complete(self, *args, **kwargs):
        r = super(statusbar, self).document_complete(*args, **kwargs)
        self.correct_height()
        return r

    def hide_document(self):
        """ делает документ невидимым """

        def hide(e):
            e.set_style_attr('visibility', 'collapse')
            self.correct_height()
        return self.do_select(hide, 'body')


def foo2(attr_name = '', *args, **kwargs):
    print attr_name


def foo(param, *args, **kwargs):
    print param
    foo2(*args, **kwargs)


def test():
    foo(0, attr_name = 'foo')


if __name__ == "__main__":

    test()
