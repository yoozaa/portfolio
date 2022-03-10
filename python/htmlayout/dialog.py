# -*- coding: cp1251 -*-

"""

   Управление диалоговыми окнами

"""

from document import html_document
import msystem
from keys import *

# Minimizes a window, even if the thread that owns the window is not responding.
# This flag should only be used when minimizing windows from a different thread.
SW_FORCEMINIMIZE = 11
# Hides the window and activates another window.
SW_HIDE = 0
# Maximizes the specified window.
SW_MAXIMIZE = 3
# Minimizes the specified window and activates the next top-level window in the Z order.
SW_MINIMIZE = 6
# Activates and displays the window. If the window is minimized or maximized,
# the system restores it to its original size and position.
# An application should specify this flag when restoring a minimized window.
SW_RESTORE = 9
# Activates the window and displays it in its current size and position.
SW_SHOW = 5
# Sets the show state based on the SW_ value specified in the STARTUPINFO structure passed to the
# CreateProcess function by the program that started the application.
SW_SHOWDEFAULT = 10
# Activates the window and displays it as a maximized window.
SW_SHOWMAXIMIZED = 3
# Activates the window and displays it as a minimized window.
SW_SHOWMINIMIZED = 2
# Displays the window as a minimized window.
# This value is similar to SW_SHOWMINIMIZED, except the window is not activated.
SW_SHOWMINNOACTIVE = 7
# Displays the window in its current size and position.
# This value is similar to SW_SHOW, except that the window is not activated.
SW_SHOWNA = 8
# Displays a window in its most recent size and position.
# This value is similar to SW_SHOWNORMAL, except that the window is not activated.
SW_SHOWNOACTIVATE = 4
# Activates and displays a window.
# If the window is minimized or maximized, the system restores it to its original size and position.
# An application should specify this flag when displaying the window for the first time.
SW_SHOWNORMAL = 1


class html_dialog(html_document):
    """ Диалоговое окно """
    default_html = "<html><body .dialog></body></html>"
    default_styled_html = "<html><style>%s</style><body .dialog></body></html>"

    def beforeInit(self, *args, **kwargs):
        super(html_dialog, self).beforeInit(*args, **kwargs)
        self.dialog_window = True
        self.button_min = 0
        self.button_max = 0
        self.button_close = 0
        self.post_for_parent = False
        self.escape_close = True
        self.max_height = 900

    def correct_height(self, height=None):
        self.commit_updates()
        self.refresh('height', self.get_intrinsic_height() if height is None else height)

    def correct_max_height(self, main_css='div#main'):
        self.query(main_css).set_style_attr('overflow-y', 'visible')
        self.commit_updates()
        height = self.get_intrinsic_height()
        if height <= self.max_height:
            self.refresh('height', height)
        else:
            self.query(main_css).set_style_attr('overflow-y', 'auto')
            self.refresh('height', self.max_height)

    def document_complete(self, *args, **kwargs):
        r = super(html_dialog, self).document_complete(*args, **kwargs)
        self.button_min = self.find_helement('#minimize')
        self.button_max = self.find_helement('#maximize')
        self.button_close = self.find_helement('#close')
        self.set_maximized_button_style(msystem.is_maximized(self.hwnd))
        return r

    def set_maximized_button_style(self, maximized):
        button = self.find_first("#maximize")
        if button:
            if maximized:
                button.set_attr('state', 'maximized')
            else:
                button.set_attr('state', 'normal')

    def maximize(self):
        msystem.ShowWindow(self.hwnd, SW_MAXIMIZE)
        self.set_maximized_button_style(True)
 
    def restore(self):
        msystem.ShowWindow(self.hwnd, SW_RESTORE)
        self.set_maximized_button_style(False)

    def on_key_down(self, he, target, key_code, alt_state):
        if key_code == VK_ESCAPE and not alt_state and self.escape_close:
            self.modalresult(2)
            return True
        return super(html_dialog, self).on_key_down(he, target, key_code, alt_state)

    def button_click(self, he, *args, **kwargs):
        r = super(html_dialog, self).button_click(he)
        if r:
            return r
        if he == self.button_min:
            msystem.ShowWindow(self.hwnd, SW_MINIMIZE)
            return True
        elif he == self.button_max:
            if msystem.is_maximized(self.hwnd):
                self.restore()
            else:
                self.maximize()
            return True
        elif he == self.button_close:
            self.close(immediately=True, to_parent=False)
            return True
        self.log_whereami()
        return False
