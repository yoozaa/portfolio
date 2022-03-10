# -*- coding: cp1251 -*-
"""
   Аналог behavior_hyperlink.hpp

BEHAVIOR: hyperlink
    goal: Implementation of hyperlink notifications.
    All <a href="something"> elements have "style.behavior=hyperlink" set by default
SAMPLE:
   TBD


"""

from layout import *

class element_hyperlink(element_behavior):

    behaviors = ('hyperlink', )
    verbose_level = VERB_MAX

    def beforeInit(self, *args, **kwargs):
        super(element_hyperlink, self).beforeInit(*args, **kwargs)
        # устанавливает атр. target = "_blank"
        self.internet = True

    def notify(self, el, click=BY_MOUSE_CLICK):
        if not self.internet:
            el['target'] = '_blank'
        el.post_event(HYPERLINK_CLICK, click, el)

    def on_mouse(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        r = super(element_hyperlink, self).on_mouse(he, target, event_type, pt, mouseButtons, keyboardStates)
        if r:
            return r
        if event_type == MOUSE_ENTER:
            return False

        elif event_type == MOUSE_LEAVE:
            return False

        elif event_type == MOUSE_DOWN:
            if mouseButtons == MAIN_MOUSE_BUTTON:
                element(he).set_state(STATE_CURRENT)
                return True

        elif event_type == MOUSE_UP:
            el = element(he)
            was_current = el.get_state(STATE_CURRENT)
            if was_current:
                # clearing CURRENT state
                el.set_state(0, STATE_CURRENT)
                self.notify(el)

            return True
        return False

    def on_key(self, he, cmd, target, key_code, alt_state):
        '''
        if cmd == KEY_UP:
            el = element(he)
            if key_code not in (' ', VK_RETURN):
               return False
            self.notify(el)
            return True
        '''
        if cmd == KEY_DOWN:
            element(he).set_state(STATE_CURRENT)
            return True

        if cmd == KEY_UP:
            el = element(he)
            was_current = el.get_state(STATE_CURRENT)
            el.set_state(0, STATE_CURRENT)

            if key_code not in (' ', VK_RETURN):
                return False

            if was_current:
                self.notify(el)
            return True

        return False

    def on_focus(self, he, cmd, target, by_mouse_click, cancel):
        """ focus event """
        return True

