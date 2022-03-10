# -*- coding: cp1251 -*-

"""
   Расширение функционала html_document, позволяющая создавать макеты страниц на python
"""

from document import *
from gtd import system
from query import *


class markup_element(baseobject):
    tagname = 'noname'

    def beforeInit(self, *args, **kwargs):
        super(markup_element, self).beforeInit(*args, **kwargs)
        self.id = ''
        self.style = None
        self.cls = ''
        self.caption = ''
        self.element = None
        self.document = None
        self.elements = [obj for obj in args if isinstance(obj, markup_element)]
        self.attrs = [key for key in kwargs.keys() if key not in self.__dict__]
        self.on_click = None
        self.on_init = None

    def gen(self, document, root):
        self.document = document
        self.element = self.create_element(document, root)
        if self.elements is None:
            pass
        else:
            for e in self.elements:
                e.gen(document, self.element)
        self.do_gen(self.element, document, root)
        return self

    def create_element(self, document, root):
        return element().create_element(self.tagname, self.caption, root)

    def do_gen(self, element, document, root):
        if self.id:
            self.element['id'] = self.id
        if self.cls:
            self.element['class'] = self.cls
        if self.style:
            for key in self.style:
                self.element.set_style_attr(key, self.style[key])
        for attr in self.attrs:
            bind_attr = 'bind_%s' % (attr)
            if hasattr(self, bind_attr) and callable(getattr(self, bind_attr)):
                getattr(self, bind_attr)(element, document, root)
            elif hasattr(element, attr) and not callable(getattr(element, attr)):
                setattr(element, attr, getattr(self, attr))
            else:
                element.set_attr(attr, getattr(self, attr))
        if self.on_init:
            self.on_init(self)


class div(markup_element):
    tagname = 'div'


class textarea(markup_element):
    tagname = 'textarea'


class typed_element(markup_element):
    def afterInit(self, *args, **kwargs):
        super(typed_element, self).afterInit(*args, **kwargs)
        self.attrs.append('type')


class input(typed_element):
    tagname = 'input'


class menu(markup_element):
    tagname = 'menu'


class ul(markup_element):
    tagname = 'ul'


class li(markup_element):
    tagname = 'li'


class hr(markup_element):
    tagname = 'hr'


class textinput(input):
    type = 'text'


class dateinput(input):
    type = 'date'


class widget(markup_element):
    tagname = 'widget'


class select_widget(typed_element):
    type = 'select'
    tagname = 'widget'


class dock_widget(typed_element):
    type = 'dockpanel'
    tagname = 'widget'


class option(markup_element):
    tagname = 'option'


class h1(markup_element):
    tagname = 'h1'


class table(markup_element):
    tagname = 'table'

    def bind_on_id_changed(self, element, document, root):
        for be in document.behaviors_obj:
            if be.he == element.he:
                be.on_handle_id_changed = self.on_id_changed

    def bind_on_editcurrent(self, element, document, root):
        for be in document.behaviors_obj:
            if be.he == element.he:
                be.on_editcurrent = self.on_editcurrent


def get_virtual_table(*args, **kwargs):
    return div(
        cls='client_align vgrid_wrapper',
        style={
            'flow': 'horizontal'
        },
        elements=[
            table(*args, **kwargs)
        ]
    )


class button_handler(object):

    def bind_on_click(self, element, document, root):
        element.attach_handler(on_handle_button_click=self.button_click, layout=document)

    def button_click(self, sender, he, *args, **kwargs):
        return self.on_click(self, sender, he, *args, **kwargs)


class button(button_handler, markup_element):
    tagname = 'button'


class div_button(button_handler, div):
    def afterInit(self, *args, **kwargs):
        super(div_button, self).afterInit(*args, **kwargs)
        if self.style is None:
            self.style = {}
        self.style['behavior'] = 'button'


class checkbox(button):
    """ checkbox """
    def __init__(self, *args, **kwargs):
        super(checkbox, self).__init__(type='checkbox', *args, **kwargs)


class a(markup_element):
    tagname = 'a'

    def bind_on_click(self, element, document, root):
        element.attach_handler(on_handle_hyperlink_click=self.hyperlink_click, layout=document)

    def hyperlink_click(self, sender, he, *args, **kwargs):
        return self.on_click(self, sender, he, *args, **kwargs)


class close_button(button):
    pass


class cancel_button(button):
    pass


class dialog_window(div):
    pass


class span(markup_element):
    tagname = 'span'


class p(markup_element):
    tagname = 'p'


class img(markup_element):
    tagname = 'img'


class markup(baseobject):
    def beforeInit(self, html_cls=html_document, mkup_element=None, documentparams=None, *args, **kwargs):
        super(markup, self).beforeInit(*args, **kwargs)
        self.root_css = 'body'
        self.html_cls = html_cls
        self.mkup_element = mkup_element
        self.documentparams = documentparams
        self.kw_document_complete=None

    def get_document_class(self):
        return self.html_cls

    def get_document(self, *args, **kwargs):
        if self.documentparams:
            kwargs.update(self.documentparams)
        if 'on_document_complete' in kwargs:
            self.kw_document_complete = kwargs['on_document_complete']
            del kwargs['on_document_complete']
        return self.get_document_class()(on_document_complete=self.document_complete, *args, **kwargs)

    def show(self, *args, **kwargs):
        return self.get_document(*args, **kwargs).show()

    def select(self, *args, **kwargs):
        return self.get_document(*args, **kwargs).select_result()

    def _(self, css_selector, document):
        return document.query(css_selector)

    def gen(self, document, root):
        mk_element = self.get_markup_element()
        try:
            iterator = iter(mk_element)
        except TypeError:
            mk_element.gen(document, root)
        else:
            for e in iterator:
                e.gen(document, root)
        return 0

    def get_markup_element(self):
        return self.mkup_element

    def document_complete(self, document, *args, **kwargs):
        r = self.gen(document, self.get_root_element(document))
        if self.kw_document_complete is not None:
            self.kw_document_complete(document, *args, **kwargs)
        return r

    def get_root_element(self, document):
        return document.find_first(self.root_css)

    def info(self, msg):
        system.infomes(msg)


class test_markup(markup):
    def get_markup_element(self):
        return div(
            div(
                button(
                    caption='Тестовая кнопка'
                    , on_click=lambda button: button.document.info('Тестовая кнопка')
                )
                , a(
                    caption='Создать'
                    , href='#'
                    , on_click=lambda a: a.document.info('Создать')
                )
                , id='main'
                , cls='client_align'
                , style={
                    'border': '1px solid red'
                    , 'flow': 'horizontal'
                }
            )
            , button(caption="Изменение background-color", on_click=self.change_background_color)
            , style={
                'height': '100%',
                'width': '100%',
                'background-color': 'gold',
                'border': '3px solid red',
            }
        )

    def change_background_color(self, mk_element):
        mk_element.element.select_parent('div').set_style_attr('background-color', 'green')

