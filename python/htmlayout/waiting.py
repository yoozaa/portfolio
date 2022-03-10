# -*- coding: cp1251 -*-

"""

    Окно ожидания события с одной кнопкой - прервать.

"""

from gtd.html.dialog import html_dialog
from gtd.html.markup import markup
from gtd.html.markup_templates import *
from gtd.html.busy import busy_html_document


class waiting_html_document(busy_html_document):

    def beforeInit(self, *args, **kwargs):
        super(waiting_html_document, self).beforeInit(*args, **kwargs)
        self.filename = 'decl://html/busy/waiting.html'
        self.isterminated = False
        self.on_continue = None
        self.on_terminate = None

    def button_click(self, he):
        r = super(waiting_html_document, self).button_click(he)
        if not r and test_css(he, '#terminatebutton'):
            self.isterminated = True
            return True

    def do_continue(self, param):
        if self.isterminated:
            return False
        if self.on_continue:
            return self.on_continue(param)
        return False

    def do_terminate(self, param):
        if self.on_terminate:
            return self.on_terminate(param)
        return True

    def waitfor(self, on_continue, on_terminate, param):
        from gtd import system
        self.on_continue = on_continue
        self.on_terminate = on_terminate
        system.waitfor(self.do_continue, param, self.do_terminate, self)


def do_button_click(sender, he):
    return sender.modalresult(RESULT_OK, -1)


def waiting_for(what_for):
    return get_window().select(
        width=400,
        height=440,
        styles=["main.css", "express/express.css", "ui.css", "ui/all.css", "dialog.css"],
        what_for=what_for,
        # on_handle_key=do_handle_key,
        on_handle_button_click=do_button_click,
    )


class waiting_dialog(html_dialog):

    def beforeInit(self, *args, **kwargs):
        super(waiting_dialog, self).beforeInit(*args, **kwargs)
        self.title = 'Ожидание завершения процессов'
        self.escape_close = False


def get_window():
    return markup(
        waiting_dialog,
        [
            make_waiting_markup(),
        ],
    )


def make_waiting_markup():
    elements = [
        dialog_caption(),
        div_main(elements=[p(caption='Ожидание'), button(caption='Завершить')], flow='vertical'),
    ]
    return shadow_dialog(elements)
