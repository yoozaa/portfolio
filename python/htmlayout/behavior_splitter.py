# -*- coding: cp1251 -*-

'''

BEHAVIOR: splitter
    goal: Implementation of splitter - element-divider between two other elements.
TYPICAL USE CASE:
    <div style="flow:horizontal">
      <div style="width:100px"></div> <!-- first element -->
      <div style="behavior:splitter"></div>
      <div style="width:100%%"></div> <!-- second element -->
    </div>
SAMPLE:
   See: samples/behaviors/splitters.htm

'''

from layout import *
from tkshtml import *
import gtd

class element_splitter(element_behavior):

    def beforeInit(self, *args, **kwargs):
        super(element_splitter, self).beforeInit(*args, **kwargs)
        self.pressed_offset = 0
        self.style_attr = 'width'
        self.left = P_LEFT
        self.right = P_RIGHT
        self.point = P_X

    def on_mouse(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        r = super(element_splitter, self).on_mouse(he, target, event_type, pt, mouseButtons, keyboardStates)
        if r:
            return r

        if mouseButtons != MAIN_MOUSE_BUTTON:
            return False

        if event_type == MOUSE_UP:
            gtd.system.release_capture()
            return True

        if event_type != MOUSE_MOVE and event_type != MOUSE_DOWN:
            return False

        # mouse moved and pressed

        # el is our splitter element
        splitter_el = element(he)
        parent_element = splitter_el.parent()

        first = splitter_el.prev_sibling()
        second = splitter_el.next_sibling()

        if not first or not second:
            # nothing to do
            return False

        need_update = self.do_sizing(event_type, pt, splitter_el, first, second, parent_element)

        if need_update and event_type == MOUSE_MOVE:
            # done! update changes on the view
            parent_element.update()

        # it is ours - stop event bubbling
        return True


    def do_sizing(self, event_type, pt, splitter_el, first, second, parent_el):
        # which element width we will change?

        rc_parent = parent_el.get_rect()
        rc = first.get_rect()

        # if width of first element is less than half of parent we
        # will change its width.
        change_first = (rc[self.right] - rc[self.left]) < (rc_parent[self.right] - rc_parent[self.left])/2

        if not change_first:
            rc = second.get_rect()

        if event_type == MOUSE_DOWN:
            self.pressed_offset = pt[self.point]
            splitter_el.set_capture()
            # don't need updates
            return False

        # mouse move handling
        if pt[self.point] == self.pressed_offset:
            # don't need updates
            return False

        width = rc[self.right] - rc[self.left]

        if change_first:
            width += pt[self.point] - self.pressed_offset
            if width >= 0:
                first.set_style_attr(self.style_attr, "%dpx" % (width))
                second.set_style_attr(self.style_attr, "100%%")
        else:
            width -= pt[self.point] - self.pressed_offset
            if width >= 0:
                first.set_style_attr(self.style_attr,"100%%")
                second.set_style_attr(self.style_attr, "%dpx" % (width))
        # need update
        return True



class element_hsplitter(element_splitter):
    behaviors = ('hsplitter', )

class element_vsplitter(element_splitter):
    behaviors = ('vsplitter', )
    def beforeInit(self, *args, **kwargs):
        super(element_vsplitter, self).beforeInit(*args, **kwargs)
        self.style_attr = 'height'
        self.left = P_TOP
        self.right = P_BOTTOM
        self.point = P_Y
