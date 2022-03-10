# -*- coding: cp1251 -*-

"""
   интерфейсный модуль для HTMLayout.dll
   функции определены в tkshtml.pyd
"""

import datetime
import os
import time
from ctypes import *
from tkshtml import *
from keys import *
from gtd import system, ROOT_PATH, process, log_error, log_msg, error_method_int, error_method_none
from tks.strutils import uformat
from tks.objects import baseobject
from Queue import Empty

VERB_RELEASE = 0
VERB_DEBUG = 2
VERB_MAX = 8

WM_KEYDOWN = 0x0100
WM_USER = 0x0400
WM_MODALRESULT = WM_USER + 1
WM_DOCUMENTRELOAD = WM_USER + 2
WM_DOCUMENTCLOSE = WM_USER + 3


HLDOM_OK = 0
HLDOM_INVALID_HWND = 1
HLDOM_INVALID_HANDLE = 2
HLDOM_PASSIVE_HANDLE = 3
HLDOM_INVALID_PARAMETER = 4
HLDOM_OPERATION_FAILED = 5
HLDOM_OK_NOT_HANDLED = -1

# enum HTMLayoutResourceType
HLRT_DATA_HTML = 0
HLRT_DATA_IMAGE = 1
HLRT_DATA_STYLE = 2
HLRT_DATA_CURSOR = 3
HLRT_DATA_SCRIPT = 4

# event groups.
# enum EVENT_GROUPS
#/** attached/detached */
HANDLE_INITIALIZATION = 0x0000
#/** mouse events */
HANDLE_MOUSE = 0x0001
#/** key events */
HANDLE_KEY = 0x0002
#/** focus events, if this flag is set it also means that element it attached to is focusable */
HANDLE_FOCUS = 0x0004
#/** scroll events */
HANDLE_SCROLL = 0x0008
#/** timer event */
HANDLE_TIMER = 0x0010
#/** size changed event */
HANDLE_SIZE = 0x0020
#/** drawing request (event) */
HANDLE_DRAW = 0x0040
#/** requested data () has been delivered */
HANDLE_DATA_ARRIVED = 0x080
#/** secondary, synthetic events:
#    BUTTON_CLICK, HYPERLINK_CLICK, etc.,
#    a.k.a. notifications from intrinsic behaviors */
HANDLE_BEHAVIOR_EVENT = 0x0100
#/** behavior specific methods */
HANDLE_METHOD_CALL = 0x0200
#/** system drag-n-drop events */
HANDLE_EXCHANGE    = 0x0400
#/** all of them */
HANDLE_ALL = 0x03FF
#/** disable INITIALIZATION events to be sent.
#normally engine sends
#BEHAVIOR_DETACH / BEHAVIOR_ATTACH events unconditionally,
#this flag allows to disable this behavior
#*/
DISABLE_INITIALIZATION = 0x80000000


#  TBEHAVIOR_EVENTS
# click on button
BUTTON_CLICK = 0x0
# mouse down or key down in button
BUTTON_PRESS = 0x1
# checkbox/radio/slider changed its state/value
BUTTON_STATE_CHANGED = 0x2
# before text change
EDIT_VALUE_CHANGING = 0x3
# after text change
EDIT_VALUE_CHANGED = 0x4
# selection in <select> changed
SELECT_SELECTION_CHANGED = 0x5
# node in select expanded/collapsed, heTarget is the node
SELECT_STATE_CHANGED = 0x6
# request to show popup just received
POPUP_REQUEST = 0x7

#     here DOM of popup element can be modifed.
# popup element has been measured and ready to be shown on screen,
POPUP_READY = 0x8
#     here you can use functions like ScrollToView.
# popup element is closed,
POPUP_DISMISSED = 0x9
#     here DOM of popup element can be modifed again - e.g. some items can be removed
#     to free memory.
# "grey" event codes  - notfications from behaviors from this SDK
MENU_ITEM_ACTIVE = 0xA
# menu item click
MENU_ITEM_CLICK = 0xB

#   BEHAVIOR_EVENT_PARAMS.heTarget - owner(anchor) of the menu
#   BEHAVIOR_EVENT_PARAMS.he - the menu item, presumably <li> element
#   BEHAVIOR_EVENT_PARAMS.reason - BY_MOUSE_CLICK | BY_KEY_CLICK
CONTEXT_MENU_SETUP   = 0xF
CONTEXT_MENU_REQUEST = 0x10
# "right-click", BEHAVIOR_EVENT_PARAMS::he is current popup menu HELEMENT being processed or NULL.
# application can provide its own HELEMENT here (if it is NULL) or modify current menu element.
VISIUAL_STATUS_CHANGED = 0x11
# broadcast notification, sent to all elements of some container being shown or hidden
# "grey" event codes  - notfications from behaviors from this SDK
HYPERLINK_CLICK = 0x80

# click on some cell in table header,
## //     target = the cell,
## //     reason = index of the cell (column number, 0..n)
TABLE_HEADER_CLICK = 0x81
# click on data row in the table, target is the row
## //     target = the row,
## //     reason = index of the row (fixed_rows..n)
TABLE_ROW_CLICK = 0x82
# mouse dbl click on data row in the table, target is the row
## //     target = the row,
## //     reason = index of the row (fixed_rows..n)
TABLE_ROW_DBL_CLICK = 0x83

ELEMENT_COLLAPSED = 0x90
# element was collapsed, so far only behavior:tabs is sending these two to the panels
ELEMENT_EXPANDED = 0x91 # element was expanded,
ACTIVATE_CHILD = 0x92 # activate (select) child,
# used for example by accesskeys behaviors to send activation request, e.g. tab on behavior:tabs.

DO_SWITCH_TAB = ACTIVATE_CHILD
# command to switch tab programmatically, handled by behavior:tabs
# use it as HTMLayoutPostEvent(tabsElementOrItsChild, DO_SWITCH_TAB, tabElementToShow, 0);

# request to virtual grid to initialize its view
INIT_DATA_VIEW = 0x094
# request from virtual grid to data source behavior to fill data in the table
# parameters passed throug DATA_ROWS_PARAMS structure
ROWS_DATA_REQUEST = 0x095

FIRST_APPLICATION_EVENT_CODE = 0x100
# all custom event codes shall be greater
# than this number. All codes below this will be used
# solely by application - HTMLayout will not intrepret it
# and will do just dispatching.
# To send event notifications with  these codes use
# HTMLayoutSend/PostEvent API.

TABLE_SET_CURRENT_ROW = 0x0107
TABLE_REFRESH = 0x0109
TABLE_SORT_COLUMN = 0x110
TABLE_INIT_DATA = 0x111
TABLE_SHOW_FILTER = 0x112
ELEMENT_FOCUS = 0x113
TABLE_EDIT_CURRENT = 0x114
TABLE_ID_CHANGED = 0x115
TABLE_SET_ACTIVE = 0x116
TABLE_SET_CURRENT_ID = 0x117
TABLE_SCROLL_TO_CURRENT = 0x118
TABLE_RECREATE = 0x119
TABLE_UPDATE_CURRENT = 0x11A
TABLE_DATA_WAIT = 0x11B
TABLE_RECORDCOUNT_WAIT = 0x11D
TABLE_UPDATE_RECORDCOUNT = 0x11E
TABLE_SET_READONLY = 0x11F
TABLE_ROW_INSERT = 0x120

# устанавливает фокус на ячейке и переводит в режим редактирования
CELL_DATA_EDIT = 0x124
CELL_DATA_CHANGED = 0x125
ACTIVE_CELL_CHANGED = 0x126
TABLE_ROW_DELETE = 0x130
TABLE_GET_ROWS_CHECKED = 0x140
TABLE_SET_ROWS_CHECKED = 0x150

TABLE_ROW_MARK = 0x155
REASON_MARK = 1
REASON_UNMARK = 0
ROW_MARK_ALL = 0b010
ROW_MARK_RANGE = 0b100

# table filter
TWIN_VALUE_CHANGED = 0x160

SKIP_INIT = 1

# Если в документе встречается ссылка типа
# <A HREF="/xmldocs/delete" csstarget="#xmldocs_table">Удалить документ</A>
# то всем элементам, которые удовлетворяют csstarget
# посылается событие EXECUTE_HREF_ACTION в поле target указывается hElement этой ссылки
EXECUTE_HREF_ACTION = 0x108

SCROLL_MOVE = 0x170
VGRID_SET_SCROLL_POSITION = 0x171
VGRID_SCROLL = 0x172
VGRID_SCROLL_POS = 0x173

DOCUMENT_COMPLETE = 0x200
DOCUMENT_CLOSE = 0x201
WINDOW_SHOW = 0x203

BEHAVIOR_EVENT_NAMES = {
    BUTTON_CLICK : 'BUTTON_CLICK',
    BUTTON_PRESS : 'BUTTON_PRESS',
    BUTTON_STATE_CHANGED : 'BUTTON_STATE_CHANGED',
    EDIT_VALUE_CHANGING : 'EDIT_VALUE_CHANGING',
    EDIT_VALUE_CHANGED : 'EDIT_VALUE_CHANGED',
    SELECT_SELECTION_CHANGED : 'SELECT_SELECTION_CHANGED',
    SELECT_STATE_CHANGED : 'SELECT_STATE_CHANGED',
    POPUP_REQUEST : 'POPUP_REQUEST',
    POPUP_READY : 'POPUP_READY',
    POPUP_DISMISSED : 'POPUP_DISMISSED',
    MENU_ITEM_ACTIVE : 'MENU_ITEM_ACTIVE',
    MENU_ITEM_CLICK : 'MENU_ITEM_CLICK',
    CONTEXT_MENU_SETUP : 'CONTEXT_MENU_SETUP',
    CONTEXT_MENU_REQUEST : 'CONTEXT_MENU_REQUEST',
    VISIUAL_STATUS_CHANGED : 'VISIUAL_STATUS_CHANGED',
    HYPERLINK_CLICK : 'HYPERLINK_CLICK',
    TABLE_HEADER_CLICK : 'TABLE_HEADER_CLICK',
    TABLE_ROW_CLICK : 'TABLE_ROW_CLICK',
    TABLE_ROW_DBL_CLICK : 'TABLE_ROW_DBL_CLICK',
    ELEMENT_COLLAPSED : 'ELEMENT_COLLAPSED',
    ELEMENT_EXPANDED : 'ELEMENT_EXPANDED',
    ACTIVATE_CHILD : 'ACTIVATE_CHILD',
    INIT_DATA_VIEW : 'INIT_DATA_VIEW',
    ROWS_DATA_REQUEST : 'ROWS_DATA_REQUEST',
    FIRST_APPLICATION_EVENT_CODE : 'FIRST_APPLICATION_EVENT_CODE',
    TABLE_SORT_COLUMN : 'TABLE_SORT_COLUMN',
    TABLE_ROW_INSERT : 'TABLE_ROW_INSERT',
    TABLE_GET_ROWS_CHECKED : 'TABLE_GET_ROWS_CHECKED',
    TABLE_SET_ROWS_CHECKED : 'TABLE_SET_ROWS_CHECKED',
    SCROLL_MOVE : 'SCROLL_MOVE',
    TABLE_SET_CURRENT_ROW : 'TABLE_SET_CURRENT_ROW',
    EXECUTE_HREF_ACTION : 'EXECUTE_HREF_ACTION',
}

# enum EVENT_REASON
BY_MOUSE_CLICK, BY_KEY_CLICK, SYNTHESIZED = range(3)

# с этого кода начинаются сообщения, которые обрабатываются "локально" самими объектами
FIRST_PRIVATE_EVENT_CODE = 0x500

#  TElement_STATE_BITS
# selector :link,    any element having href attribute
STATE_LINK = 0x0001
# selector :hover,   element is under the cursor, mouse hover
STATE_HOVER = 0x0002
# selector :active,  element is activated, e.g. pressed
STATE_ACTIVE = 0x0004
# selector :focus,   element is in focus
STATE_FOCUS = 0x0008
# selector :visited, aux flag - not used internally now.
STATE_VISITED = 0x0010
# selector :current, current item in collection, e.g. current <option> in <select>
STATE_CURRENT = 0x0020
# selector :checked, element is checked (or selected), e.g. check box or itme in multiselect
STATE_CHECKED = 0x0040
# selector :disabled, element is disabled, behavior related flag.
STATE_DISABLED = 0x0080
# selector :read-only, element is read-only, behavior related flag.
STATE_READONLY = 0x0100
# selector :expanded, element is in expanded state - nodes in tree view e.g. <options> in <select>
STATE_EXPANDED = 0x0200
# selector :collapsed, mutually exclusive with EXPANDED
STATE_COLLAPSED = 0x0400
# selector :incomplete, element has images (back/fore/bullet) requested but not delivered.
STATE_INCOMPLETE = 0x0800
# selector :animating, is currently animating
STATE_ANIMATING = 0x00001000
STATE_FOCUSABLE = 0x00002000
# selector :anchor, first element in selection (<select miltiple>), STATE_CURRENT is the current.
STATE_ANCHOR = 0x00004000
# selector :synthetic, synthesized DOM elements - e.g. all missed cells in tables (<td>) are getting this flag
STATE_SYNTHETIC = 0x00008000
#  selector :owns-popup, anchor(owner) element of visible popup.
STATE_OWNS_POPUP = 0x00010000
# selector :tab-focus, element got focus by tab traversal. engine set it together with :focus.
STATE_TABFOCUS = 0x00020000
# selector :empty - element is empty.
STATE_EMPTY = 0x00040000
# selector :busy, element is busy. HTMLayoutRequestElementData will set this flag if
STATE_BUSY = 0x00080000
# selector :busy, element is busy. HTMLayoutRequestElementData will set this flag if
STATE_POPUP = 0x40000000
# pressed - close to active but has wider life span - e.g. in MOUSE_UP it
# is still on, so behavior can check it in MOUSE_UP to discover CLICK condition.
STATE_PRESSED = 0x04000000

STATES_DESC = {
    STATE_LINK: 'STATE_LINK',
    STATE_HOVER: 'STATE_HOVER',
    STATE_ACTIVE: 'STATE_ACTIVE',
    STATE_FOCUS: 'STATE_FOCUS',
    STATE_VISITED: 'STATE_VISITED',
    STATE_CURRENT: 'STATE_CURRENT',
    STATE_CHECKED: 'STATE_CHECKED',
    STATE_DISABLED: 'STATE_DISABLED',
    STATE_READONLY: 'STATE_READONLY',
    STATE_EXPANDED: 'STATE_EXPANDED',
    STATE_COLLAPSED: 'STATE_COLLAPSED',
    STATE_INCOMPLETE: 'STATE_INCOMPLETE',
    STATE_ANIMATING: 'STATE_ANIMATING',
    STATE_FOCUSABLE: 'STATE_FOCUSABLE',
    STATE_ANCHOR: 'STATE_ANCHOR',
    STATE_SYNTHETIC: 'STATE_SYNTHETIC',
    STATE_OWNS_POPUP: 'STATE_OWNS_POPUP',
    STATE_TABFOCUS: 'STATE_TABFOCUS',
    STATE_EMPTY: 'STATE_EMPTY',
    STATE_BUSY: 'STATE_BUSY',
    STATE_POPUP: 'STATE_POPUP',
    STATE_PRESSED: 'STATE_PRESSED',
}

# enum UPDATE_ELEMENT_FLAGS
# reset styles - this may require if you have styles dependent from attributes,
RESET_STYLE_THIS = 0x20
# use these flags after SetAttribute then. RESET_STYLE_THIS is faster than RESET_STYLE_DEEP.
RESET_STYLE_DEEP = 0x10
# use this flag if you do not expect any dimensional changes - this is faster than REMEASURE
MEASURE_INPLACE = 0x0001
# use this flag if changes of some attributes/content may cause change of dimensions of the element
MEASURE_DEEP    = 0x0002
# invoke ::UpdateWindow function after applying changes
REDRAW_NOW = 0x8000


V_UNDEFINED = 0
V_NULL = 1
V_BOOL = 2
V_INT = 3
V_FLOAT = 4
V_STRING = 5
# INT64 - contains a 64-bit value representing the number of 100-nanosecond intervals since January 1, 1601 (UTC), a.k.a. FILETIME on Windows
V_DATE = 6
# INT64 - 14.4 fixed number. E.g. dollars = int64 / 10000;
V_CURRENCY = 7
# length units, value is int or float, units are VALUE_UNIT_TYPE
V_LENGTH = 8
V_ARRAY = 9
V_MAP = 10
V_FUNCTION = 11
# sequence of bytes - e.g. image data
V_BYTES = 12
# scripting object proxy (TISCRIPT/SCITER)
V_OBJECT = 13
# DOM object (CSSS!), use get_object_data to get HELEMENT
V_DOM_OBJECT = 14


# constants for inserting html
# replace content of the element
SIH_REPLACE_CONTENT = 0
# insert html before first child of the element
SIH_INSERT_AT_START = 1
# insert html after last child of the element
SIH_APPEND_AFTER_LAST = 2
# ATTN: SOH_*** operations do not work for inline elements like <SPAN>
# replace element by html, a.k.a. element.outerHtml = "something"
SOH_REPLACE = 3
# insert html before the element
SOH_INSERT_BEFORE = 4
# insert html after the element
SOH_INSERT_AFTER = 5

MOUSE_ENTER = 0
MOUSE_LEAVE = 1
MOUSE_MOVE = 2
MOUSE_UP = 3
MOUSE_DOWN = 4
MOUSE_DCLICK = 5
MOUSE_WHEEL = 6
MOUSE_TICK = 7
MOUSE_IDLE = 8 # mouse stay idle for some time
MOUSE_CLICK = 0xFF

DROP = 9 # item dropped, target is that dropped item
DRAG_ENTER = 0xA # drag arrived to the target element that is one of current drop targets.
DRAG_LEAVE = 0xB # drag left one of current drop targets. target is the drop target element.
DRAG_REQUEST = 0xC # drag src notification before drag start. To cancel - return true from handler.

# This flag is 'ORed' with MOUSE_ENTER..MOUSE_DOWN codes if dragging operation is in effect.
# E.g. event DRAGGING | MOUSE_MOVE is sent to underlying DOM elements while dragging.
DRAGGING = 0x100


MOUSE_CMD = {
    MOUSE_ENTER: 'MOUSE_ENTER',
    MOUSE_LEAVE: 'MOUSE_LEAVE',
    MOUSE_MOVE: 'MOUSE_MOVE',
    MOUSE_UP: 'MOUSE_UP',
    MOUSE_DOWN: 'MOUSE_DOWN',
    MOUSE_CLICK: 'MOUSE_CLICK',
    MOUSE_DCLICK: 'MOUSE_DCLICK',
    MOUSE_WHEEL: 'MOUSE_WHEEL',
    MOUSE_TICK: 'MOUSE_TICK',
    MOUSE_IDLE: 'MOUSE_IDLE',
}


#  PHASE_MASK
#  http://www.w3.org/TR/xml-events/Overview.html#s_intro
#
# source_he -> sinking, sinking -> target -> bubbling, bubbling -> source_he
# source_he -> sinking, sinking -> target -> bubbling (return True), handled -> source_he
# source_he -> sinking (return True), handled -> target -> handled, handled -> source_he

# bubbling (emersion) phase
BUBBLING = 0
# capture (immersion) phase, this flag is or'ed with EVENTS codes below
SINKING = 0x08000
# event already processed.
HANDLED = 0x10000

FOCUS_LOST = 0
FOCUS_GOT = 1

# aka left button
MAIN_MOUSE_BUTTON = 1
# aka right button
PROP_MOUSE_BUTTON = 2
MIDDLE_MOUSE_BUTTON = 4

# KEYBOARD_STATES
CONTROL_KEY_PRESSED = 0x1
SHIFT_KEY_PRESSED = 0x2
ALT_KEY_PRESSED = 0x4

KEYBOARD_STATES = {
    'CTRL': CONTROL_KEY_PRESSED,
    'SHIFT': SHIFT_KEY_PRESSED,
    'ALT': ALT_KEY_PRESSED,
}

# HTMLAYOUT_SCROLL_FLAGS
SCROLL_TO_TOP = 0x01
SCROLL_SMOOTH = 0x10

# KEY_EVENTS
KEY_DOWN = 0
KEY_UP = 1
KEY_CHAR = 2

# SCROLL_EVENTS
SCROLL_HOME = 0
SCROLL_END = 1
SCROLL_STEP_PLUS = 2
SCROLL_STEP_MINUS = 3
SCROLL_PAGE_PLUS = 4
SCROLL_PAGE_MINUS = 5
SCROLL_POS = 6
SCROLL_SLIDER_RELEASED = 7

# enum BEHAVIOR_METHOD_IDENTIFIERS
DO_CLICK = 0
SCROLL_BAR_GET_VALUE = 6
SCROLL_BAR_SET_VALUE = 7
XCALL = 0xFF

# Позиция полосы прокрутки
# для divmod
SCROLL_POSITION_MOD = 10

# Признак сортировки в обратную сторону
# для divmod
SORT_DIRECTION_MOD = 1000


# areas for HTMLayoutGetElementLocation

# - or this flag if you want to get HTMLayout window relative coordinates,
#   otherwise it will use nearest windowed container e.g. popup window.
ROOT_RELATIVE = 0x01
# - "or" this flag if you want to get coordinates relative to the origin
#   of element iself.
SELF_RELATIVE = 0x02
# - position inside immediate container.
CONTAINER_RELATIVE = 0x03
# - position relative to view - HTMLayout window
VIEW_RELATIVE = 0x04
# content (inner)  box
CONTENT_BOX = 0x00
# content + paddings
PADDING_BOX = 0x10
# content + paddings + border
BORDER_BOX  = 0x20
# content + paddings + border + margins
MARGIN_BOX  = 0x30
# relative to content origin - location of background image (if it set no-repeat)
BACK_IMAGE_AREA = 0x40
# relative to content origin - location of foreground image (if it set no-repeat)
FORE_IMAGE_AREA = 0x50
# scroll_area - scrollable area in content box
SCROLLABLE_AREA = 0x60


## Scroll Info
SI_POSITION = 0
SI_VIEWRECT = 1
SI_CONTENTSIZE = 2

P_LEFT = 0
P_TOP = 1
P_RIGHT = 2
P_BOTTOM = 3

P_X = 0
P_Y = 1

V_LEFT = 0
V_TOP = 1
V_WIDTH =  2
V_HEIGHT =  3

C_WIDTH = 0
C_HEIGHT = 1


EXTRA_SPACE = 10

## postype in HTMLayoutEnumerationCallback
POSTYPE_HEAD = 0
POSTYPE_TAIL = 1
POSTYPE_CHAR = 2

class METHOD_PARAMS(Structure):
    _fields_ = [("methodID", c_uint),]

class SCROLLBAR_VALUE_PARAMS(Structure):
    _fields_ = [("methodID", c_uint),
                ("value", c_int),
                ("min_value", c_int),
                ("max_value", c_int),
                ("page_value", c_int),
                ("step_value", c_int)]


DECL_RESOURCE_TYPE = 'decl'
DECL_URL_STARTER = 'decl://'

BASE_PATH_TYPE = 'base'
BASE_URL_STARTER = 'base://'


class reasons(dict):
    """ глобальный словарик  - используется для передачи значений по post_event через reason """
    obj = None
    refcount = 0
    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = dict.__new__(cls, *args, **kwargs)
        return cls.obj

    def get_refcount(self):
        self.refcount += 1
        return self.refcount


def vk_from_shortcut(shortcut):
    """
    :param shortcut: 'CTRL+K'
    :return: (VK_K, CONTROL_KEY_PRESSED)
    """
    vk = None
    alt_state = 0
    for pos, k in enumerate(reversed(shortcut.split('+'))):
        if pos:
            try:
                alt_state |= KEYBOARD_STATES[k.upper()]
            except KeyError:
                raise Exception('Неизвестная клавиша-модификатор %s в комбинации быстрого вызова %s' % (repr(k), repr(shortcut)))
        else:
            try:
                vk = eval('VK_' + k)
            except:
                raise Exception('Неизвестная клавиша %s в быстром вызове %s' % (repr(k), repr(shortcut)))
    if vk:
        return vk, alt_state


def html_format_value(v, t = '', *args, **kwargs):
    """ форматирование значения для использования в htmlayout """
    if isinstance(v, tuple) or isinstance(v, time.struct_time):
        if (v[3] == 0 and v[4] == 0 and v[5] == 0) or t == 'D':
            return u'%-2.2d.%-2.2d.%d' % (v[2], v[1], v[0])
        else:
            return u'%-2.2d.%-2.2d.%d %-2.2d:%-2.2d:%-2.2d' % (v[2], v[1], v[0], v[3], v[4], v[5])
    elif isinstance(v, unicode):
        return v
    elif isinstance(v, basestring):
        return unicode(v, 'cp1251')
    elif isinstance(v, datetime.datetime):
        return u'{:%Y.%m.%d %H:%M}'.format(v)
    elif isinstance(v, datetime.date):
        return u'%-2.2d.%-2.2d.%d' % (v.day, v.month, v.year)
    elif v is not None:
        return unicode(str(v), 'cp1251')
    else:
        return u''


def focus_log(cmd):
    t = []
    if cmd & FOCUS_GOT == FOCUS_GOT:
        t.append('got')
    elif cmd & FOCUS_LOST == FOCUS_LOST:
        t.append('lost')

    if cmd & SINKING == SINKING:
        t.append('sinking')
    elif cmd & BUBBLING == BUBBLING:
        t.append('bubbling')

    if cmd & HANDLED == HANDLED:
        t.append('handled')

    return ' '.join(t)


def test_css(he, css_selector):
    return HTMLayoutSelectParent(he, css_selector, 1) > 0


def get_parent(he):
    return HTMLayoutGetParentElement(he)


class element(baseobject):

    def beforeInit(self, he = 0, use_element = True, *args, **kwargs):
        self.he = he
        self.usecount = 0
        self.encoding = 'cp1251'
        self.use_element = use_element
        self.log_init()

    def afterInit(self, *args, **kwargs):
        if self.use_element:
            self.use()

    def use(self):
        if self.he and (HTMLayout_UseElement(self.he) == HLDOM_OK):
            self.usecount += 1
            return self.he
        else:
            return 0

    def unuse(self):
        if self.he:
            if self.usecount > 0 and (HTMLayout_UnuseElement(self.he) == HLDOM_OK):
                self.usecount -= 1
            if self.usecount == 0:
                self.he = 0

    def __del__(self):
        self.unuse()

    def set_state(self, toset, toclear = 0, update = True):
        if self.he and self.valid():
            return HTMLayoutSetElementState(self.he, toset, toclear, update)
        else:
            return False

    def get_state(self, state):
        if self.he and self.valid():
            return state & HTMLayoutGetElementState(self.he) == state
        else:
            return False

    def debug_states(self):
        r = []
        if self.he and self.valid():
            for state in STATES_DESC:
                if state & HTMLayoutGetElementState(self.he) == state:
                    r.append(STATES_DESC[state])
        return r

    def get_type(self):
        try:
            return HTMLayoutGetElementType(self.he)
        except:
            log_error(debug=True)

    def set_checked(self, value):
        if value:
            self.set_state(STATE_CHECKED)
        else:
            self.set_state(0, STATE_CHECKED)

    def get_checked(self):
        return self.get_state(STATE_CHECKED)

    def get_enabled(self):
        return not self.get_state(STATE_DISABLED)

    def set_enabled(self, value):
        if value:
            self.set_state(0, STATE_DISABLED)
        else:
            self.set_state(STATE_DISABLED)

    def get_visited(self):
        return self.get_state(STATE_VISITED)

    def set_visited(self, value):
        if value:
            self.set_state(STATE_VISITED)
        else:
            self.set_state(0, STATE_VISITED)

    def get_style_attr(self, name):
        return HTMLayoutGetStyleAttribute(self.he, name)

    def set_style_attr(self, name, value, append = False):
        if append:
            v = self.get_style_attr(name)
            if v:
                return HTMLayoutSetStyleAttribute(self.he, name, ' '.join((v, value)))
        return HTMLayoutSetStyleAttribute(self.he, name, value)

    def get_visible(self):
        return self.get_style_attr('visibility')

    def set_visible(self, value):
        if not isinstance(value, basestring):
            value = 'visible' if value else 'collapse'
        return self.set_style_attr('visibility', value)

    def get_display(self):
        return self.get_style_attr('display')

    def set_display(self, value):
        return self.set_style_attr('display', value)

    def get_attr(self, name):
        return HTMLayoutGetAttributeByName(self.he, name)

    def set_attr(self, name, value):
        return HTMLayoutSetAttributeByName(self.he, name, value)

    def append_attr(self, name, value_add = '', value_remove = ''):
        attrvalue = self.get_attr(name)
        if attrvalue:
            a = [att for att in attrvalue.split(' ') if att != value_remove]
            if value_add and value_add not in a:
                a.append(value_add)
            return self.set_attr(name, ' '.join(a))
        return self.set_attr(name, value_add)

    def addclass(self, value):
        return self.append_attr('class', value)

    def removeclass(self, value):
        return self.append_attr('class', None, value)

    def switchclass(self, value_add, value_remove):
        return self.append_attr('class', value_add, value_remove)

    def __getitem__(self, key):
        return self.get_attr(key)

    def __setitem__(self, key, value):
        return self.set_attr(key, value)

    def get_child(self, index):
        return element(HTMLayoutGetNthChild(self.he, index))
        #try:
            #return element(HTMLayoutGetNthChild(self.he, index))
        #except:
            #log_error(debug=True)

    def get_child_count(self):
        try:
            return HTMLayoutGetChildrenCount(self.he)
        except:
            log_error(debug=True)

    def index(self):
        try:
            return HTMLayoutGetElementIndex(self.he)
        except:
            log_error(debug=True)

    def update(self, flags = MEASURE_INPLACE | REDRAW_NOW):
        try:
            return HTMLayoutUpdateElementEx(self.he, flags)
        except:
            log_error(debug=True)

    def set_value(self, value, notify=True):
        r = None
        if notify:
            self.send_event(EDIT_VALUE_CHANGING)
        try:
            r = HTMLayoutControlSetValue(self.he, value)
        except:
            log_error(debug=True)
        if notify:
            self.send_event(EDIT_VALUE_CHANGED)
        return r

    def get_value(self):
        try:
            return HTMLayoutControlGetValue(self.he)
        except:
            log_error(debug=True)

    def set_values(self, **kwargs):
        pass

    def get_datatype(self):
        try:
            return HTMLayoutGetElementDataType(self.he)
        except:
            log_error(debug=True)

    def create_element(self, tagName, Text = None, parent_element = None, use = True, insert_point = -1):
        """ HTMLayoutCreateElement(tagName, Text = None) -> HElement """
        if Text:
            if isinstance(Text, unicode):
                self.he = HTMLayoutCreateElement(tagName, Text)
            else:
                self.he = HTMLayoutCreateElement(tagName, unicode(Text, 'cp1251'))
        else:
            self.he = HTMLayoutCreateElement(tagName)

        if parent_element:
            if insert_point == -1:
                parent_element.insert(self, parent_element.get_child_count())
            else:
                parent_element.insert(self, insert_point)
        elif use:
            self.use()

        return self

    def insert_elements(self, elements):
        for e in elements:
            el = element().create_element(e[0], e[1], self)
            try:
                if e[2]:
                    for s in e[2].keys():
                        el.set_attr(s, e[2][s])
                if e[3]:
                    for s in e[3].keys():
                        el.set_style_attr(s, e[3][s])
            finally:
                del el

    def clone(self):
        """ HTMLayoutCloneElement(he) -> HElement """
        return element(HTMLayoutCloneElement(self.he), False)

    def insert(self, el, index):
        """ HTMLayoutInsertElement(he, he_parent, index) -> HLDOM_RESULT
        счетчик ссылок увеличивается на единицу
        """
        try:
            HTMLayoutInsertElement(el.he, self.he, index)
            el.usecount += 1
            return True
        except:
            log_error(debug=True)
            return False

    def detach(self):
        """ HTMLayoutDetachElement(he) -> HLDOM_RESULT
        счетчик ссылок уменьшается на единицу
        """
        try:
            HTMLayoutDetachElement(self.he)
            self.usecount -= 1
            return True
        except:
            log_error(debug=True)
            return False

    def delete(self):
        """ HTMLayoutDeleteElement(he) -> HLDOM_RESULT
            Элемент должен использоваться
        """
        he = self.usecount and self.he
        self.unuse()
        if he:
            try:
                HTMLayoutDeleteElement(he)
                return True
            except:
                log_error()
        else:
            self.log_whereami('usecount=0')
        return False

    def delete_children(self):
        for i in reversed(xrange(self.get_child_count())):
            self.get_child(i).delete()

    def get_innertext(self):
        """ HTMLayoutGetElementInnerText(he) -> string """
        try:
            return unicode(HTMLayoutGetElementInnerText(self.he), 'UTF-8').encode(self.encoding)
        except:
            log_error(debug=True)

    def set_innertext(self, text):
        """ HTMLayoutSetElementInnerText(he, string) -> HLDOM_RESULT """
        s = text
        if s is not None and not isinstance(s, unicode):
            s = unicode(str(s), self.encoding)
        try:
            return HTMLayoutSetElementInnerText(self.he, s.encode('UTF-8'))
        except:
            log_error(debug=True)

    def get_html(self, outer = True):
        """ HTMLayoutGetElementHtml(he, outer) -> string """
        try:
            return unicode(HTMLayoutGetElementHtml(self.he, outer), 'UTF-8').encode(self.encoding)
        except:
            log_error(debug=True)
            return ''

    def set_html(self, htmltext, where = SIH_REPLACE_CONTENT):
        """ HTMLayoutSetElementHtml(he, string, where) -> HLDOM_RESULT """
        # htmltext не может быть пустым
        s = htmltext or u'&nbsp;'
        if not isinstance(s, unicode):
            s = unicode(s, self.encoding)
        try:
            return HTMLayoutSetElementHtml(self.he, s.encode('UTF-8'), where)
        except:
            log_error(debug=True)
            raise

    def select_parent(self, css_selector, depth = 0):
        try:
            phe = HTMLayoutSelectParent(self.he, css_selector, depth)
            if phe:
                return element(phe)
        except:
            log_error(debug=True)

    def test_css(self, css_selector):
        """ Проверяет, соответвует ли элемент css selector у """
        return test_css(self.he, css_selector)

    def parent(self):
        try:
            he = HTMLayoutGetParentElement(self.he)
            if he:
                return element(he)
        except:
            log_error(debug=True)

    def post_event(self, event_code, reason = 0, target = None):
        """
        Вызывает handle_event(event_code, sender.he, target, reason) у всех элементов цепочки от root до target
        html -> table -> tr -> td
        td.post_event(EVENT, target=table) вызывает событие только у html и table
        """
        try:
            if isinstance(event_code, list) or isinstance(event_code, tuple):
                for ev in event_code:
                    HTMLayoutPostEvent(self.he, ev, target and target.he or self.he, reason)
                return True
            return HTMLayoutPostEvent(self.he, event_code, target and target.he or self.he, reason) == HLDOM_OK
        except:
            log_error(debug=True)

    def send_event(self, event_code, reason = 0, source = None):
        return HTMLayoutSendEvent(self.he, event_code, source and source.he or self.he, reason)

    def set_timer(self, milliseconds=0, timerid=0):
        try:
            return HTMLayoutSetTimer(self.he, milliseconds)
        except:
            log_error(debug=0)

    def get_current(self):
        return self.get_state(STATE_CURRENT)

    def set_current(self, value):
        if value:
            self.set_state(STATE_CURRENT)
        else:
            self.set_state(0, STATE_CURRENT)

    def scroll_to_view(self, toTopOfView = False, smooth = False):
        flags = 0
        if toTopOfView:
            flags |= SCROLL_TO_TOP
        if smooth:
            flags |= SCROLL_SMOOTH
        try:
            return HTMLayoutScrollToView(self.he, flags)
        except:
            log_error(debug=True)

    def set_scroll_pos(self, posx, posy, smooth = False):
        flags = 0
        try:
            if smooth:
                flags |= SCROLL_SMOOTH
            return HTMLayoutSetScrollPos(self.he, posx, posy, flags) == HLDOM_OK
        except:
            log_error(debug=True)
            return False

    def get_scroll_info(self):
        ''' tuple((left, top), #Position
                  (left, top, width, height), #ViewRect
                  (width, height) #ContentSize
                 )
        '''
        try:
            return HTMLayoutGetScrollInfo(self.he)
        except:
            log_error(debug=True)
            return ((-1, -1), (0, 0, 0, 0), (0, 0))

    def get_scroll_Position(self):
        ''' tuple(left, top) '''
        return self.get_scroll_info()[SI_POSITION]

    def get_scroll_ViewRect(self):
        ''' tuple(left, top, width, height) '''
        return self.get_scroll_info()[SI_VIEWRECT]

    def get_scroll_ContentSize(self):
        ''' tuple(width, height) '''
        return self.get_scroll_info()[SI_CONTENTSIZE]

    def handle(self, rootWindow = True):
        try:
            return HTMLayoutGetElementHwnd(self.he, rootWindow)
        except:
            log_error(debug=True)
            return 0

    def valid(self):
        """
        H>Вопрос: как надежно проверить, входит ли dom::element в разметку при условии,
        что HELEMENT, лежащий внутри, может быть не нулевым?
        elem.get_element_hwnd(true) != 0
        Когда элемент находится в отсоединенной ветке DOM tree его view (HWND) уже недоступно.
        """
        return self.handle() <> 0

    def visible(self):
        try:
            return HTMLayoutIsElementVisible(self.he)
        except:
            log_error(debug=True)
            return False

    def is_enabled(self):
        """
        Deep visibility.
        Determines if element visible - has no visiblity:hidden and no display:none defined
        for itself or for any its parents.
        """
        try:
            return HTMLayoutIsElementEnabled(self.he)
        except:
            log_error(debug=True)
            return False

    def sort(self, comp_obj, fi = 0, li = -1):
        """ сортировка дочерних элементов
            comp_obj - объект, который имеет метод compare(r1, r2)
            fi - first index - индекс, начиная с которого сравниваются элементы
            li - last index - индекс, заканчивая которым сравниваются элементы
        """
        try:
            return HTMLayoutSortElements(self.he, fi, li, comp_obj.compare)
        except:
            log_error(debug=True)

    def focus(self):
        return self.set_state(STATE_FOCUS, 0)

    def get_rect(self, area = ROOT_RELATIVE | CONTENT_BOX):
        """ get element area tuple(left, top, right, bottom) """
        try:
            return HTMLayoutGetElementLocation(self.he, area)
        except:
            log_error(debug=True)
            return (0, 0, 0, 0)

    def get_width(self):
        """ get element width (right - left) """
        r = self.get_rect()
        if r:
            return r[P_RIGHT] - r[P_LEFT]
        else:
            return 0

    def get_height(self):
        """ get element height (bottom - top) """
        r = self.get_rect()
        if r:
            return r[P_BOTTOM] - r[P_TOP]
        else:
            return 0

    def get_text_width(self):
        """ суммарная ширина отрендеренных символов """
        def callback(he, pos, postype, code):
            if postype == POSTYPE_CHAR:
                box = HTMLayoutGetCharacterRect(he, pos)
                callback.width += box[P_RIGHT] - box[P_LEFT]
            return False

        callback.width = 0
        HTMLayoutEnumerate(self.he, callback, True)
        return callback.width

    def run_xcall(self, method_name, argv):
        """
        примеры параметров для вызова

        выделить все:
        method_name = 'selectAll'
        argv = [True]

        выделить фрагмент:
        method_name = 'setSelection'
        argv = [3, 5]
        """
        XCall(self.he, method_name, argv)

    def set_selection(self, s_start, s_end):
        setSelection(self.he, s_start, s_end)

    def get_uid(self):
        try:
            return HTMLayoutGetElementUID(self.he)
        except:
            log_error(debug=True)
            return 0

    enabled = property(get_enabled, set_enabled, None, "enabled property")
    checked = property(get_checked, set_checked, None, "checked property")
    visited = property(get_visited, set_visited, None, "visited property")
    visibility = property(get_visible, set_visible, None, "visibility property")
    display = property(get_display, set_display, None, "display property")
    value = property(get_value, set_value, None, "value property")
    innertext = property(get_innertext, set_innertext, None, "inner text property")
    current = property(get_current, set_current, None, "current state")
    html = property(get_html, set_html, None, "html text inside")

    def get_sibling(self, idx):
        r = None
        pel = self.parent()
        if pel and idx >= 0 and idx < pel.get_child_count():
            r = pel.get_child(idx)
        return r

    def next_sibling(self):
        return self.get_sibling(self.index() + 1)

    def prev_sibling(self):
        return self.get_sibling(self.index() - 1)

    def find_nearest(self):
        return self.next_sibling() or self.prev_sibling()

    def first_sibling(self):
        return self.get_sibling(0)

    def last_sibling(self):
        r = None
        pel = self.parent()
        if pel:
            r = pel.get_child(pel.get_child_count() - 1)
        return r

    def children(self, cur=0, stop=None):
        if not self.he:
            return

        count = self.get_child_count()
        if not count:
            return

        stop = stop and min(stop, count - 1) or count - 1
        while cur <= stop:
            he = HTMLayoutGetNthChild(self.he, cur)
            if he:
                yield element(he)
            cur += 1

    def descendants(self, parent_first=True):
        for child in self.children():
            if parent_first:
                yield child
            for grandson in child.descendants(parent_first):
                yield grandson
            if not parent_first:
                yield child

    def dompath(self):
        r = [str(self.get_type())]
        p = self.parent()
        p_prev = self
        while p is not None:
            if p.get_child_count() > 1:
                r[-1] += '[%s]' % p_prev.index()
            r.append(str(p.get_type()))
            p_prev = p
            p = p.parent()
        return '/'.join(reversed(r))

    def set_capture(self):
        return HTMLayoutSetCapture(self.he)

    # создание обработчиков событий ==========

    def attach_handler(self, *args, **kwargs):
        return self.attach_handler_cls(event_handler, *args, **kwargs)

    def attach_handler_cls(self, handler_cls, *args, **kwargs):
        return self.attach_handler_obj(handler_cls(*args, **kwargs))

    def attach_handler_obj(self, handler):
        return HTMLayoutAttachHandler(self.he, handler)

    # манипуляции с деревом ==================

    def find(self, css_selector):
        return [element(he) for he in element_selector(self.he).select(css_selector, False, self.he)]

    def find_first(self, css_selector):
        elems = element_selector(self.he).select(css_selector, True, self.he)
        if elems:
            return element(elems[0])
        return None

    def find_last(self, css_selector):
        elems = element_selector(self.he).select(css_selector, False, self.he)
        if elems:
            return element(elems[-1])
        return None

    def do_select(self, act, *args, **kwargs):
        for he in self.select(*args, **kwargs):
            act(element(he))

    def do_select_x(self, act, *args, **kwargs):
        for he in self.select(*args, **kwargs):
            act(element(he), *args, **kwargs)

    def select(self, *args, **kwargs):
        return element_selector(self.he).select(*args, **kwargs)

    def visit(self, *args, **kwargs):
        return element_selector(self.he).visit(*args, **kwargs)

    def query(self, *args, **kwargs):
        return element_query(self.he, *args, **kwargs)

    def call_behavior_method(self, params):
        if not self.valid():
            return False
        return HTMLayoutCallBehaviorMethod(self.he, addressof(params))

    def call_method(self, methodID):
        params = METHOD_PARAMS()
        params.methodID = methodID
        return self.call_behavior_method(params)


class scrollbar(element):

    def set_values(self, value = 0, min_value = 0, max_value = 100, page_value = 10, step_value = 1):
        """ установка параметров scrollbar """
        sbvp = SCROLLBAR_VALUE_PARAMS()
        sbvp.methodID = SCROLL_BAR_SET_VALUE
        sbvp.value = value
        sbvp.min_value = min_value
        sbvp.max_value = max_value
        sbvp.page_value = page_value
        sbvp.step_value = step_value
        return HTMLayoutCallBehaviorMethod(self.he, addressof(sbvp))


class element_iterator(object):

    def __init__(self, element, fromindex = 0, toindex = 0):
        self.element = element
        self.current = fromindex
        self.toindex = toindex or self.element.get_child_count()

    def __del__(self):
        self.element = None

    def __iter__(self):
        return self

    def next(self):
        if self.current >= self.toindex:
            raise StopIteration
        else:
            self.current += 1
            return self.element.get_child(self.current - 1)


class event_handler(baseobject):

    event_types = HANDLE_ALL | HANDLE_TIMER
    verbose_level = VERB_RELEASE

    def beforeInit(self, *args, **kwargs):
        self.subscribe_to = self.event_types
        self.log_object = None
        self.on_init_data = None
        self.event_handlers = {}
        # выполнять или нет self.init_data в finalizeInit
        # полезно, если инициализация данных зависит от параметров
        # которые устанавливаются где-то в другом месте
        self.finalize_init = True
        self.log_init()

    def finalizeInit(self, *args, **kwargs):
        self.before_init_data()
        if self.finalize_init:
            self.init_data()
        if self.on_init_data:
            self.on_init_data(self)

    def before_init_data(self):
        pass

    def get_debug_name(self, *args, **kwargs):
        return self.__class__.__name__

    def add_event_handler(self, evt_type, css_selector, func):
        d = self.event_handlers.get(evt_type, {})
        d[css_selector] = func
        self.event_handlers[evt_type] = d

    def button_click(self, he):
        if hasattr(self, 'on_handle_button_click'):
            return self.on_handle_button_click(self, he)
        return False

    def button_state_changed(self, he, reason):
        if hasattr(self, 'on_handle_button_state_changed'):
            return self.on_handle_button_state_changed(self, he, reason)
        # ToDo сделать такое для всех событий
        #elif element(he)['on_state_changed']:
        #    exec element(he)['on_state_changed'] in globals(), locals()
        #    system.showmessage('state_changed')
        #    return True
        return False

    def hyperlink_click(self, he):
        if hasattr(self, 'on_handle_hyperlink_click'):
            return self.on_handle_hyperlink_click(self, he)
        return False

    def context_menu_setup(self, he, target, reason, *args, **kwargs):
        return False

    def context_menu_request(self, he, target, reason, *args, **kwargs):
        return False

    def select_selection_changed(self, he, target, reason, *args, **kwargs):
        if hasattr(self, 'on_select_selection_changed'):
            return self.on_select_selection_changed(self, he, target, reason, *args, **kwargs)
        return False

    def edit_value_changed(self, he, target, reason, *args, **kwargs):
        if hasattr(self, 'on_handle_value_changed'):
            return self.on_handle_value_changed(self, he, target, reason, *args, **kwargs)
        return False

    def execute_href_action(self, he, target, reason, *args, **kwargs):
        return False

    def handle_event(self, cmd, he, target, reason, *args, **kwargs):
        if hasattr(self, 'on_handle_event'):
            r = self.on_handle_event(self, cmd, he, target, reason, *args, **kwargs)
            if r:
                return r
        if cmd in self.event_handlers:
            for key in self.event_handlers[cmd].keys():
                if HTMLayoutSelectParent(he, key, 1) > 0:
                    if self.event_handlers[cmd][key](cmd, he, target, reason, *args, **kwargs):
                        return True
        if cmd == BUTTON_CLICK:
            return self.button_click(he)
        elif cmd == BUTTON_STATE_CHANGED:
            return self.button_state_changed(he, reason)
        elif cmd == HYPERLINK_CLICK:
            return self.hyperlink_click(he)
        elif cmd == CONTEXT_MENU_SETUP:
            return self.context_menu_setup(he, target, reason, *args, **kwargs)
        elif cmd == CONTEXT_MENU_REQUEST:
            return self.context_menu_request(he, target, reason, *args, **kwargs)
        elif cmd == MENU_ITEM_CLICK:
            return self.menu_item_click(he, target, reason, *args, **kwargs)
        elif cmd == SELECT_SELECTION_CHANGED:
            return self.select_selection_changed(he, target, reason, *args, **kwargs)
        elif cmd == EDIT_VALUE_CHANGED:
            return self.edit_value_changed(he, target, reason, *args, **kwargs)
        elif cmd == EXECUTE_HREF_ACTION:
            return self.execute_href_action(he, target, reason, *args, **kwargs)
        elif cmd == ELEMENT_FOCUS:
            element(target).focus()
            return True
        return False

    def document_complete(self, *args, **kwargs):
        return 0

    def menu_item_click(self, he, target, reason, *args, **kwargs):
        if hasattr(self, 'on_handle_menu_item_click'):
            return self.on_handle_menu_item_click(self, he, target, reason, *args, **kwargs)
        return False

    def on_mouse(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if event_type & ~ SINKING == MOUSE_DOWN:
            return self.mouse_down(he, target, event_type, pt, mouseButtons, keyboardStates)
        elif event_type & ~ SINKING == MOUSE_UP:
            return self.mouse_up(he, target, event_type, pt, mouseButtons, keyboardStates)
        elif mouseButtons == MAIN_MOUSE_BUTTON:
            if event_type & ~SINKING == MOUSE_DCLICK:
                return self.dblclick(he, target, event_type, pt, mouseButtons, keyboardStates)
            elif event_type & ~SINKING == MOUSE_CLICK:
                return self.mouse_click(he, target, event_type, pt, mouseButtons, keyboardStates)
        if event_type & ~ SINKING == MOUSE_WHEEL:
            return self.mouse_wheel(he, target, event_type, pt, mouseButtons, keyboardStates)
        return False

    def mouse_wheel(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if hasattr(self, 'on_handle_mouse_wheel'):
            return self.on_handle_mouse_wheel(he, target, event_type, pt, mouseButtons, keyboardStates)
        return False

    def mouse_click(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if hasattr(self, 'on_handle_mouse_click'):
            return self.on_handle_mouse_click(self, he, target, event_type, pt, mouseButtons, keyboardStates)
        return False

    def mouse_down(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if hasattr(self, 'on_handle_mouse_down'):
            return self.on_handle_mouse_down(self, he, target, event_type, pt, mouseButtons, keyboardStates)
        return False

    def mouse_up(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if hasattr(self, 'on_handle_mouse_up'):
            return self.on_handle_mouse_up(self, he, target, event_type, pt, mouseButtons, keyboardStates)
        return False

    def dblclick(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        if hasattr(self, 'on_handle_dblclick'):
            return self.on_handle_dblclick(self, he, target, event_type, pt, mouseButtons, keyboardStates)
        return False

    def on_key(self, he, cmd, target, key_code, alt_state):
        """ keyboard events """
        if hasattr(self, 'on_handle_key'):
            return self.on_handle_key(self, he, cmd, target, key_code, alt_state)
        elif cmd == KEY_DOWN:
            return self.on_key_down(he, target, key_code, alt_state)
        elif cmd == KEY_UP:
            return self.on_key_up(he, target, key_code, alt_state)
        return False

    def on_key_down(self, he, target, key_code, alt_state):
        if hasattr(self, 'on_handle_key_down'):
            return self.on_handle_key_down(self, he, target, key_code, alt_state)
        if key_code == VK_RETURN and hasattr(self, 'on_handle_enter'):
            return self.on_handle_enter(self, he, target, alt_state)
        return False

    def on_key_up(self, he, target, key_code, alt_state):
        if hasattr(self, 'on_handle_key_up'):
            return self.on_handle_key_up(self, he, target, key_code, alt_state)
        return False

    def on_focus(self, he, cmd, target, by_mouse_click, cancel):
        """ focus event """
        if hasattr(self, 'on_handle_focus'):
            return self.on_handle_focus(self, he, cmd, target, by_mouse_click, cancel)

        return False

    def on_timer(self, he, timerid=0):
        """ timer event """
        if hasattr(self, 'on_handle_timer'):
            return self.on_handle_timer(self, he, timerid)
        return False

    def on_scroll(self, he, target, cmd, pos, isVertical):
        return False

    def on_size(self, he):
        pass

    def info(self, message):
        system.showmessage(message)

    def warning(self, message):
        system.warning(message)

    def error(self, e, message):
        return self.log('%s %s' % (e, message))

    def init_data(self):
        pass

    def deinit_data(self):
        pass

    def do_read_prefs(self, prefs):
        pass

    def do_write_prefs(self, prefs):
        pass

    def deref_reason(self, reason):
        rs = reasons()
        if reason in rs:
            r = rs[reason]
            del rs[reason]
            return r
        return None

    def ref_reason(self, reason):
        rs = reasons()
        rid = rs.get_refcount()
        reasons()[rid] = reason
        return rid


class element_behavior(event_handler):

    behaviors = ()
    event_types = HANDLE_MOUSE | HANDLE_KEY | HANDLE_FOCUS | HANDLE_BEHAVIOR_EVENT

    def beforeInit(self, layout, name='', he=0, on_init=None, *args, **kwargs):
        super(element_behavior, self).beforeInit(*args, **kwargs)
        self.layout = layout
        self.name = name
        self.he = he
        self.on_init = on_init
        self.registered_behaviors = set()

    def get_element(self):
        return element(self.he)

    def afterInit(self, *args, **kwargs):
        super(element_behavior, self).afterInit(*args, **kwargs)
        if self.on_init:
            self.on_init(self)

    def deinit_data(self):
        super(element_behavior, self).deinit_data()
        self.unregister_behaviors()

    def modalresult(self, result, result_obj=None):
        return self.layout.modalresult(result, result_obj)

    def register_behavior(self, beh_cls, beh_name='', *args, **kwargs):
        """
        Если в аргументах передаются объекты или методы, то beh_name должен быть уникален на уровне оъекта, а не класса.
        """
        if not beh_name:
            beh_name = beh_cls.behaviors[0]
        if beh_name not in self.registered_behaviors:
            self.layout.register_behavior(beh_cls, beh_name,  *args, **kwargs)
            self.registered_behaviors.add(beh_name)
        return beh_name

    def unregister_behaviors(self):
        for beh_name in self.registered_behaviors:
            self.layout.unregister_behavior(beh_name)


class element_button(element_behavior):

    behaviors = ('button', )


class element_result(element_behavior):

    behaviors = ('modalresult', )

    def button_click(self, he):
        e = element(he)
        try:
            if self.layout.hwnd != 0:
                self.modalresult(int(e['result']))
            return True
        finally:
            del e
        return False


class element_clickable(element_behavior):
    behaviors = ('clickable', )

    def on_mouse(self, *args, **kwargs):
        r = super(element_clickable, self).on_mouse(*args, **kwargs)
        if r:
            return r
        return self.layout(*args, **kwargs)


class change_size(element_behavior):

    event_types = HANDLE_SIZE
    behaviors = ('change-size', )

    def on_size(self, he):
        pass


class DummyTimer(object):


    def __init__(self, layout, func, mileseconds=0, name=''):
        self.layout = layout
        self.name = '{}_{}'.format(func.__name__, name)
        self.ms = mileseconds
        self.func = func
        self.args = tuple()
        self.kwargs = dict()
        el_timer = self.get_timer_element()
        if el_timer is None:
            el_timer = element().create_element('div', parent_element=layout.find_first('body'), use=0)
            el_timer.display = 'none'
        el_timer['id'] = self.timer_id()
        el_timer.attach_handler(on_handle_timer=self.on_handle_timer)

    def timer_id(self):
        return 'timer_{}'.format(self.name)

    def get_timer_element(self):
        return self.layout.find_first('div#{}'.format(self.timer_id()))

    def __call__(self, *args, **kwargs):
        el_timer = self.get_timer_element()
        if el_timer:
            self.args = args
            self.kwargs = kwargs
            el_timer.set_timer(self.ms)

    def on_handle_timer(self, sender, he, timerid=0):
        element(he).set_timer(0)
        self.func(*self.args, **self.kwargs)


class htmlayout(event_handler):

    def beforeInit(self, *args, **kwargs):
        super(htmlayout, self).beforeInit(*args, **kwargs)
        self.hwnd = 0
        self.log_object = process.ProcessManager().info
        # {'gridcell-edstable': {'cls': GridCell, 'args': *args, 'kwargs': **kwargs}
        self.behaviors = {}
        self.behaviors_obj = []
        self.search_button_css = '#searchbutton'
        self.search_grid_css = ''
        self.search_input_css = 'input#search'
        self.search_text = u''
        self.contextmenu = None
        self.focused_he = 0
        # helpcontext для соответствующего контрола
        self.helpcontext = 0
        # Базовый путь для загрузки ресурсов страницы
        # Если указан, то имена, начинающиеся на ./ будут преобразованы к нему
        self.base_path = ''
        # отправлять сообщения для parent
        self.post_for_parent = True

    def afterInit(self, *args, **kwargs):
        super(htmlayout, self).afterInit(*args, **kwargs)
        self.register_behaviors()

    def inspect(self, *args, **kwargs):
        """ возможность показать object inspector """
        pass

    def get_html(self, hwnd):
        self.hwnd = hwnd
        self.behaviors_obj = []
        return ''

    def register_behaviors(self):
        self.register_behavior(element_result)
        self.register_behavior(element_button)
        self.register_behavior(element_clickable)

    def register_behavior(self, behavior_cls, behavior_name='', *args, **kwargs):
        if not behavior_name:
            behavior_name = behavior_cls.behaviors[0]
        if behavior_name not in self.behaviors:
            self.behaviors[behavior_name] = dict(cls=behavior_cls, args=args, kwargs=kwargs)

    def unregister_behavior(self, name):
        if name in self.behaviors:
            del self.behaviors[name]
            for idx, bo in enumerate(self.behaviors_obj):
                if bo.name == name:
                    bo.deinit_data()
                    del self.behaviors_obj[idx]

    def attach_event_handler(self):
        """ Выдает идентификатор типов сообщений, на которые будет подписан """
        return self.subscribe_to

    def root_post_event(self, cmd, param=None):
        root = self.get_root_element()
        if root:
            return root.post_event(cmd, param)
        return False

    def modalresult(self, result, result_obj = None):
        return postmessage(self.hwnd, WM_MODALRESULT, result, 0, self.post_for_parent)

    def close(self, immediately=False, to_parent=True):
        return postmessage(self.hwnd, WM_DOCUMENTCLOSE, 0, 0, to_parent, immediately)

    def escape(self):
        return postmessage(self.hwnd, WM_KEYDOWN, VK_ESCAPE, 0)

    def get_resource_dir(self, data_type, resource_type):
        if resource_type == DECL_RESOURCE_TYPE:
            return ROOT_PATH
        elif resource_type == BASE_PATH_TYPE and self.base_path:
            return self.base_path
        elif data_type == HLRT_DATA_STYLE:
            return os.path.join(ROOT_PATH, 'styles')
        elif data_type in (HLRT_DATA_IMAGE, HLRT_DATA_CURSOR):
            return os.path.join(ROOT_PATH, 'images')
        elif data_type == HLRT_DATA_HTML and resource_type == 'res':
            return os.path.join(ROOT_PATH, 'html')
        return ROOT_PATH

    def strip_resource_type(self, url):
        if url.startswith(DECL_URL_STARTER):
            return DECL_RESOURCE_TYPE, url[len(DECL_URL_STARTER):]
        elif url.startswith(BASE_URL_STARTER):
            return BASE_PATH_TYPE, url[len(BASE_URL_STARTER):]
        elif url.startswith('res:'):
            return 'res', url[4:]
        else:
            return '', url

    def get_resource_filename(self, url, data_type):
        resource_type, url_filename = self.strip_resource_type(url)
        resource_dir = self.get_resource_dir(data_type, resource_type)
        filename = os.path.join(resource_dir, str(url_filename.replace('/', '\\')))
        # url = base://wizard.css преобразовывается в base://wizard.css/
        # т.к. передается fully-qualified URL (if the URL is just your domain, the trailing / should also be provided)
        # поэтому надо использовать ///
        if filename[-1] == '\\':
            filename = filename[:-1]
        return filename

    def get_resource(self, filename):
        data = ''
        if os.path.exists(filename):
            try:
                f = open(filename, 'rb')
                data = f.read()
                f.close()
            except Exception, e:
                self.log_error(e)
                return None
        return data

    def load_data(self, url, data_type):
        filename = self.get_resource_filename(url, data_type)
        return self.get_resource(filename)

    def load_data_request(self, url, data_type, hwndFrom):
        data = self.load_data(url, data_type)
        if data and HTMLayoutDataReady(hwndFrom, url, data):
            return True
        return False

    def load_data_request_async(self, url, data_type=HLRT_DATA_IMAGE, hwndFrom=None):
        """ Для обновления image bits в кэше
            http://rsdn.ru/forum/htmlayout/5104607.all

            Только надо учитывать, что в кэше хранится fully qualified URL
        """
        if hwndFrom is None:
            hwndFrom = self.hwnd
        data = self.load_data(url, data_type)
        if data and HTMLayoutDataReadyAsync(hwndFrom, url, data, data_type):
            return True
        return False

    def attach_behavior(self, he, name):
        d = self.behaviors.get(name)
        if d:
            obj = d['cls'](self, name, he, log_object=self.log_object, *d['args'], **d['kwargs'])
            self.behaviors_obj.append(obj)
            return obj

    def attach(self, he, cls, *args, **kwargs):
        return HTMLayoutAttachHandler(he, cls(log_object = self.log_object, *args, **kwargs))

    def data_loaded(self, *args, **kwargs):
        return 0

    def isforeground(self):
        return HTMLayoutIsForeground(self.hwnd)

    @error_method_int
    def do_document_complete(self, *args, **kwargs):
        self.focused_he = 0
        self.document_complete(*args, **kwargs)
        self.after_document_complete(*args, **kwargs)
        return 0

    def document_complete(self, *args, **kwargs):
        return 0

    def after_document_complete(self, *args, **kwargs):
        return 0

    def document_close(self, *args, **kwargs):
        # здесь send_event потому что на document_close сохраняются настройки
        self.query('.document_close').send_event(DOCUMENT_CLOSE)
        while self.behaviors_obj:
            o = self.behaviors_obj.pop()
            o.deinit_data()
            del o

    def find(self, css_selector):
        return [element(he) for he in self.select(css_selector, False)]

    def find_first(self, css_selector):
        elems = self.select(css_selector, True)
        if elems:
            return element(elems[0])
        return None

    def find_last(self, css_selector):
        elems = self.select(css_selector, False)
        if elems:
            return element(elems[-1])
        return None

    def do_select(self, act, *args, **kwargs):
        for he in self.select(*args, **kwargs):
            act(element(he))

    def do_select_x(self, act, *args, **kwargs):
        for he in self.select(*args, **kwargs):
            e = element(he)
            try:
                act(e, *args, **kwargs)
            finally:
                del e

    def select(self, *args, **kwargs):
        return hwnd_element_selector(self.hwnd).select(*args, **kwargs)

    def visit(self, *args, **kwargs):
        return hwnd_element_selector(self.hwnd).visit(*args, **kwargs)

    def query(self, *args, **kwargs):
        return query(self.hwnd, *args, **kwargs)

    def init_gui(self):
        pass

    def deinit_gui(self):
        self.focused_he = 0

    def table_row_click(self, behavior, table, *args, **kwargs):
        return False

    def table_row_dbl_click(self, behavior, table, *args, **kwargs):
        return False

    def table_row_insert(self, behavior, table, *args, **kwargs):
        return False

    def format_value(self, v, t = ''):
        """ все значения в формате unicode """
        return html_format_value(v, t)

    def search(self, *args, **kwargs):
        """ поиск в элементах по тексту """
        if self.search_grid_css:
            self.do_select(lambda e: self.search_in_grid(self.search_grid_css, e), self.search_input_css)
            return True
        return False

    def on_return(self, he, cmd, target, key_code, alt_state, *args, **kwargs):
        return False

    def on_key(self, he, cmd, target, key_code, alt_state):
        """ keyboard events """
        r = super(htmlayout, self).on_key(he, cmd, target, key_code, alt_state)
        if r:
            return r
        if cmd == KEY_DOWN:
            if key_code == VK_RETURN:
                if test_css(he, self.search_input_css):
                    return self.search()
                else:
                    return self.on_return(he, cmd, target, key_code, alt_state)
        return False

    def button_click(self, he):
        r = super(htmlayout, self).button_click(he)
        if r:
            return r
        if test_css(he, self.search_button_css):
            return self.search()
        return False

    def search_table_row(self, row, search_text):
        found = False
        for i in range(row.get_child_count()):
            td = row.get_child(i)
            try:
                if unicode(td.innertext, 'cp1251').upper().find(search_text) != -1:
                    row.visibility = 'visible'
                    found = True
                    break
            finally:
                del td
        if not found:
            row.visibility = 'collapse'

    def search_in_grid(self, css_selector, search):
        if search.value:
            self.search_text = search.value
            self.do_select(lambda row: self.search_table_row(row, self.search_text.upper()), css_selector)
        else:
            self.cancel_search(css_selector, search)

    def cancel_search(self, css_selector, search):
        search.value = ''
        self.search_text = u''
        self.do_select(lambda row: row.set_style_attr('visibility', 'visible'), css_selector)

    def shellexecute(self, *args):
        return shellexecute(*args)

    def get_focus(self):
        try:
            return HTMLayoutGetFocusElement(self.hwnd)
        except:
            log_error(debug=True, with_trace=True)

    def renew_focus(self):
        if self.focused_he:
            e = element(self.focused_he)
            if e.valid():
                e.focus()

    def on_focus(self, he, cmd, target, by_mouse_click, cancel):
        """ focus event """
        if cmd == FOCUS_GOT | SINKING:
            self.focused_he = self.get_focus()
        return False

    def get_element(self):
        return self.get_root_element()

    def get_root_element(self):
        try:
            return element(HTMLayoutGetRootElement(self.hwnd))
        except:
            log_error(debug=True, with_trace=True)

    def commit_updates(self):
        try:
            return HTMLayoutCommitUpdates(self.hwnd)
        except:
            log_error(debug=True, with_trace=True)

    def attach_handler(self, css_selector, *args, **kwargs):
        handler = event_handler(layout = self, *args, **kwargs)
        a = self.select(css_selector)
        # if not a:
        #     self.log('attach_handler %s nothing!!!' % (css_selector))
        for he in a:
            HTMLayoutAttachHandler(he, handler)

    def bind(self, bindmap):
        """ Привязывание обработчиков событий
            self.bind({'button#close' : {on_handle_button_click : self.close_button_click}})
        """
        for key in bindmap.keys():
            self.attach_handler(key, **bindmap[key])

    def clipboard_copy(self):
        return HTMLayoutClipboardCopy(self.hwnd)


def test_element_del():

    class test_element(element):

        def __init__(self, *args, **kwargs):
            super(test_element, self).__init__(*args, **kwargs)
            print "test_element.__init__"

        def __del__(self):
            super(test_element, self).__del__()
            print "test_element.__del__"

    def test_func(e):
        print "test_func"

    print "begin test_element_del"
    test_func(test_element())

    e = test_element()
    test_func(e)

    print "end test_element_del"

from query import element_selector, query, hwnd_element_selector, element_query

if __name__ == "__main__":

    test_element_del()
    print "end testing"
