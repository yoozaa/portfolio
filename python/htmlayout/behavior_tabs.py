# -*- coding: cp1251 -*-

from layout import *
from tkshtml import *
from keys import *

TAB_DIRECT_NEXT = 1
TAB_DIRECT_PREV = -1
TAB_DIRECT_FIRST = -2
TAB_DIRECT_LAST = 2
TAB_DIRECT_NONE = 0


class element_tabs(element_behavior):
    behaviors = ('tabs', )

    def beforeInit(self, *args, **kwargs):
        super(element_tabs, self).beforeInit(*args, **kwargs)
        self.on_expanded = None
        self.on_collapsed = None
        self.initial_select = True
        # css для определения элемента с закладками
        self.tabs_strip = '.strip'
        # атрубут, при наличии которого элемент - tab
        self.tabs_button_attr = 'panel'
        # атрибут, при наличии которого элемент - tabsheet
        self.tabsheet_attr = 'name'
        self.attached(self.he)
        self.log_init()

    def afterInit(self, *args, **kwargs):
        super(element_tabs, self).afterInit(*args, **kwargs)
        if self.initial_select:
            self.attached(self.he)

    def attached(self, he):
        tabs_el = element(he)  #:root below matches the element we use to start lookup from.
        tab_el = tabs_el.find_first(":root>%s>[%s][selected]" % (self.tabs_strip, self.tabs_button_attr))  # initialy selected
        if tab_el:
            return self.select_tab(tabs_el, tab_el)

    def on_mouse(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if not he:
            return False
        if event_type != MOUSE_DOWN and event_type != MOUSE_DCLICK:
            return False
        tabs_el = element(he) # our tabs container
        tab_el = self.target_tab(element(target), element(he))
        try:
            if tab_el:
                if not tab_el:
                    return False
            # el here is a <element panel="panel-id1">tab1 caption</element>
            # and we've got here MOUSE_DOWN somewhere on it.
            return self.select_tab(tabs_el, tab_el)
        finally:
            del tabs_el
            del tab_el
        return False

    def on_key(self, he, cmd, target, key_code, alt_state):
        """ keyboard events """
        r = super(element_tabs, self).on_key(he, cmd, target, key_code, alt_state)

        if not r and cmd == KEY_DOWN:
            tabs_el = element(he) # our tabs container
            tab_el = self.current_tab(tabs_el) # currently selected
            try:
                if key_code == VK_TAB:
                    if alt_state & CONTROL_KEY_PRESSED == CONTROL_KEY_PRESSED:
                        if alt_state & SHIFT_KEY_PRESSED == SHIFT_KEY_PRESSED:
                            d = TAB_DIRECT_PREV
                        else:
                            d = TAB_DIRECT_NEXT
                        r = self.select_tab(tabs_el, tab_el, d)
                elif key_code == VK_LEFT:
                    if self.is_in_focus(tab_el):
                        r = self.select_tab(tabs_el, tab_el, TAB_DIRECT_PREV)
                elif key_code == VK_RIGHT:
                    if self.is_in_focus(tab_el):
                        r = self.select_tab(tabs_el, tab_el, TAB_DIRECT_NEXT)
                elif key_code == VK_HOME:
                    if self.is_in_focus(tab_el):
                        r = self.select_tab(tabs_el, tab_el, TAB_DIRECT_FIRST)
                elif key_code == VK_END:
                    if self.is_in_focus(tab_el):
                        r = self.select_tab(tabs_el, tab_el, TAB_DIRECT_LAST)
            finally:
                del tabs_el
                del tab_el
        return r

    def is_in_focus(self, el):
        return el.test_css(":focus") or el.select_parent(":focus")

    def select_tab(self, tabs_el, tab_el, direction = TAB_DIRECT_NONE):
        if direction == TAB_DIRECT_NONE:
            r = self.select_tab_none(tabs_el, tab_el)
        else:
            r = self.select_tab_direct(tabs_el, tab_el, direction)
        return r

    def select_tab_none(self, tabs_el, tab_el):
        r = False

        if tab_el and tab_el.get_state(STATE_CURRENT):
            # already selected, nothing to do...
            r = True # but we've handled it.
        else:
            # find currently selected element (tab and panel) and remove "selected" from them
            prev_panel_el = tabs_el.find_first(":root>[%s]:expanded" % (self.tabsheet_attr))
            prev_tab_el = self.current_tab(tabs_el)

            # find new tab and panel
            panel_el = tab_el and \
                tabs_el.find_first(":root>[%s=\"%s\"]" % (self.tabsheet_attr, tab_el.get_attr(self.tabs_button_attr))) or None
            try:
                r = True
                if panel_el:
                    if prev_panel_el:
                        prev_panel_el.set_attr("selected", 0) # remove selected attribute - just in case somone is using attribute selectors
                        prev_panel_el.set_state(STATE_COLLAPSED,0) # set collapsed in case of someone use it for styling
                    if prev_tab_el:
                        prev_tab_el.set_attr("selected", 0) # remove selected attribute
                        prev_tab_el.set_state(0,STATE_CURRENT) # reset also state flag, :current

                    panel_el.set_attr("selected", '') # set selected attribute (empty)
                    panel_el.set_state(STATE_EXPANDED,0) # expand it


                    # notify all parties involved
                    if prev_tab_el:
                        prev_tab_el.post_event(ELEMENT_COLLAPSED,0, prev_tab_el) # source here is old collapsed tab itself

                    # NOTE #1: these event will bubble from panel elements up to the root so panel itself, tabs ctl, its parent, etc.
                    # will receive these notifications. Handle them if you need to change UI dependent from current tab.
                    # NOTE #2: while handling this event in:
                    #        virtual BOOL on_event (HELEMENT he, HELEMENT target, BEHAVIOR_EVENTS type, UINT reason ),
                    # HELEMENT target is the panel element being collapsed/expanded
                #else:
                #    r = True # panel="somename" without matching name="somename"
            finally:
                if prev_panel_el:
                    del prev_panel_el
                if prev_tab_el:
                    del prev_tab_el
                if panel_el:
                    del panel_el
        if tab_el:
            tab_el.set_attr("selected", "") # set selected attribute (empty)
            tab_el.set_state(STATE_CURRENT,0) # set also state flag, :current
            tab_el.post_event(ELEMENT_EXPANDED,0, tab_el) # source here is new expanded tab itself
        return r

    def select_tab_direct(self, tabs_el, tab_el, direction):
        """  select next/prev/first/last tab """
        # find new tab
        new_tab_el = None
        if tabs_el:
            if direction == TAB_DIRECT_FIRST:
                new_tab_el = tab_el.first_sibling()
                while new_tab_el and new_tab_el.get_state(STATE_DISABLED):
                    new_tab_el = new_tab_el.next_sibling()
            elif direction == TAB_DIRECT_PREV:
                new_tab_el = tab_el.prev_sibling()
                while new_tab_el and new_tab_el.get_state(STATE_DISABLED):
                    new_tab_el = new_tab_el.prev_sibling()
            elif direction == TAB_DIRECT_NEXT:
                new_tab_el = tab_el.next_sibling();
                while new_tab_el and new_tab_el.get_state(STATE_DISABLED):
                    new_tab_el = new_tab_el.next_sibling()
            elif direction == TAB_DIRECT_LAST:
                new_tab_el = tab_el.last_sibling()
                while new_tab_el and new_tab_el.get_state(STATE_DISABLED):
                    new_tab_el = new_tab_el.prev_sibling()

            r = new_tab_el and new_tab_el.get_attr(self.tabs_button_attr) # is a tab element

        if r:
            r = self.select_tab_none(tabs_el, new_tab_el)
        if new_tab_el:
            del new_tab_el
        return r

    def target_tab(self, he, h_tabs_container):
        if not he or he == h_tabs_container:
            return None
        el = he
        panel_name = el.get_attr(self.tabs_button_attr)
        if panel_name:
            return el # here we are!
        else:
            return self.target_tab(el.parent(), h_tabs_container)

    def tab_activate(self, tabs_el, tab_el, reason):
        """ активизируем закладку по индексу reason """
        el = self.get_tab(reason)
        if el and not el.get_state(STATE_DISABLED):
            self.select_tab(tabs_el, el)
            el.focus()
        if el:
            del el
        return True

    def tab_expanded(self, tabs_el, tab_el, reason):
        if self.on_expanded:
            self.on_expanded(tab_el)
        return True

    def tab_collapsed(self, tabs_el, tab_el, reason):
        if self.on_collapsed:
            self.on_collapsed(tab_el)
        return True

    def get_tabs(self):
        """ должен вернуть div.tabs """
        return element(self.he) #:root below matches the element we use to start lookup from.

    def get_tab(self, idx):
        r = None
        tabs_el = self.get_tabs()
        try:
            panel_element = tabs_el.find_first(":root>%s>[%s]" % (self.tabs_strip, self.tabs_button_attr))
            if panel_element:
                panel_elements = panel_element.parent()
                if panel_elements and idx >= 0 and idx < panel_elements.get_child_count():
                    r = panel_elements.get_child(idx)
        finally:
            del tabs_el
        return r

    def do_switch_tab(self, idx):
        """ переключиться на закладку по индексу """
        tabs_el = self.get_tabs()
        tabs_el.post_event(DO_SWITCH_TAB, idx)
        del tabs_el

    def tabs_handle_event(self, cmd, he, target, reason, *args, **kwargs):
        if not he:
            return False
        tabs_el = element(he)
        tab_el = None
        if target:
            tab_el = element(target)
        try:
            if cmd == ELEMENT_EXPANDED:
                # self.log('ELEMENT_EXPANDED')
                r = self.tab_expanded(tabs_el, tab_el, reason)
            elif cmd == ELEMENT_COLLAPSED:
                # self.log('ELEMENT_COLLAPSED')
                r = self.tab_collapsed(tabs_el, tab_el, reason)
            elif cmd == ACTIVATE_CHILD:
                # DO_SWITCH_TAB = ACTIVATE_CHILD
                # self.log('ACTIVATE_CHILD')
                r = self.tab_activate(tabs_el, tab_el, reason)
        finally:
            del tabs_el
            if tab_el:
                del tab_el
        return r

    def handle_event(self, cmd, he, target, reason, *args, **kwargs):
        r = False
        if cmd in (ELEMENT_EXPANDED, ELEMENT_COLLAPSED, ACTIVATE_CHILD):
            r = self.tabs_handle_event(cmd, he, target, reason, *args, **kwargs)
        else:
            r = super(element_tabs, self).handle_event(cmd, he, target, reason, *args, **kwargs)
        return r

    def current_tab(self, tabs_el):
        return tabs_el.find_first(":root>%s>[%s]:current" % (self.tabs_strip, self.tabs_button_attr))

    def tab_by_name(self, panel_name):
        r = None
        tabs_el = self.get_tabs()
        if tabs_el:
            try:
                for i in range(tabs_el.get_child_count()):
                    tab_el = tabs_el.get_child(i)
                    if tab_el.get_attr(self.tabs_button_attr) == panel_name:
                        r = tab_el
                        break
            finally:
                del tabs_el
        return r

    def set_disable_tab(self, panel_name):
        tab_el = self.tab_by_name(panel_name)
        if tab_el:
            tab_el.delete()
            del tab_el


class element_tabs2(element_tabs):
    """ Реализация tabs для случая нового дизайна (изменены классы элементов)
    """
    behaviors = ('tabs2', )
    def beforeInit(self, *args, **kwargs):
        super(element_tabs2, self).beforeInit(*args, **kwargs)
        self.tabs_strip = '#menu'
        self.tabs_button_attr = 'tabname'
        self.tabsheet_attr = 'tabcontent'
        self.element = self.get_element()

    def tab_expanded(self, tabs_el, tab_el, reason):
        tab_el.addclass('tabname_selected')
        self.element.query('[%s="%s"]' % (self.tabsheet_attr, tab_el[self.tabs_button_attr])).addclass('tabcontent_selected')
        return True

    def tab_collapsed(self, tabs_el, tab_el, reason):
        tab_el.removeclass('tabname_selected')
        self.element.query('[%s="%s"]' % (self.tabsheet_attr, tab_el[self.tabs_button_attr])).removeclass('tabcontent_selected')
        return True


if __name__ == "__main__":
    element_tabs()
