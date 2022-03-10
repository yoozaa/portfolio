# -*- coding: cp1251 -*-

"""

   Страница HTML

   *** html_document - базовый класс для отображения HTML страниц ***

   для того, чтобы html_document сохранял какие-нибудь данные, а потом восстанавливал их
   необходимо задать html_document.prefs_filename

   а затем в своем классе перекрыть

   def do_read_prefs(self, prefs)
   def do_write_prefs(self, prefs)

   prefs - словарь словарей. соответсвует self.prefs

   размеры модальных форм сохраняются в tkshtml.pyd  в файле data3.ini
   только в случае, если html_document.border_style in (bsSizeable, bsSizeToolWin)

   *** Работа с таблицами в документе ****

   Для правильной работы с колонками (изменения ширины колонки)
   необходимо в конец таблицы добавить пустую колонку
   custom_grid.columns.append(dummy_column())

   Для сохранения размеров колонок в таблице надо задать
   custom_grid.table_id - идентификатор таблицы. используется также в css
   custom_grid.save_prefs - флаг сохранения настроек. по умолчанию False

   в момент создания таблицы передать ей в качестве prefs = html_document.prefs

"""

import re

import tkshtml

import urls
from gtd import system, pref, show_error, error_method_none, error_method_bool
from gtd.menu import *
from gtd.menu.menuitem import *
from tks.strutils import to_ustr
from inner import *
from tks.objects import baseobject, maybe

# BorderStyle. имеет смысл для модального окна
bsNone = 0
bsSingle = 1
bsSizeable = 2
bsDialog = 3
bsToolWindow = 4
bsSizeToolWin = 5
# WindowState
wsNormal = 0
wsMinimized = 1
wsMaximized = 2
# Position
poDesigned = 0
poDefault = 1
poDefaultPosOnly = 2
poDefaultSizeOnly = 3
poScreenCenter = 4
poDesktopCenter = 5
poMainFormCenter = 6
poOwnerFormCenter = 7

RESULT_NONE = 0
RESULT_OK = 1
RESULT_CANCEL = 2
RESULT_NO = 3

MENUITEM_ENABLED = FIRST_PRIVATE_EVENT_CODE + 1
MENUITEM_DISABLED = FIRST_PRIVATE_EVENT_CODE + 2
MENUITEM_VISIBLE = FIRST_PRIVATE_EVENT_CODE + 3
MENUITEM_HIDDEN = FIRST_PRIVATE_EVENT_CODE + 4
MENUITEM_CLICK = FIRST_PRIVATE_EVENT_CODE + 5


class html_action(baseobject):
    def beforeInit(self, name, click, *args, **kwargs):
        super(html_action, self).beforeInit(*args, **kwargs)
        self.name = name
        self.click = click


class custom_html_document(htmlayout):
    pass


class html_document(custom_html_document):

    verbose_level = VERB_MAX
    default_html = "<html><body></body></html>"
    default_styled_html = "<html><style>%s</style><body></body></html>"

    def beforeInit(self, *args, **kwargs):
        super(html_document, self).beforeInit(*args, **kwargs)
        self.busy = False
        self._inupdate = 0
        self.busy_window = None
        self.modal = False
        self.result = None
        self.title = ''
        # Показывать диалоговое окно с WS_EX_LAYERED для теней
        self.layered = True

        # Параметры окна. Имеют смысл только при показе страницы в modal режиме
        self.border_style = bsDialog
        self.window_state = wsNormal
        self.position = poMainFormCenter
        self.file_icon = '' # имя файла с иконкой

        self.width = 800
        self.height = 600
        self.filename = ''
        self.prefs_filename = ''
        # все настройки
        self.prefs = {}
        # только опции (под ключем options)
        self.options = {}
        self.prefdata = None
        self.html = ''
        self.url = ''
        self.url_base = ''
        self.history_element = False
        self.refresh_callback = None
        self.ids = {}
        self.current_id_name = ''
        self.show_status_bar = True

        self.on_print = None
        self.on_verify = None
        self.on_unload = None
        self.on_find = None

        # запуск скриптов по умолчанию включен
        self.script_enabled = True
        # секция для сохранения host форм
        self.form_save_section = self.__class__.__name__
        # Нужно ли вообще сохранять форму
        self.save_form = True
        # Если установить этот флажок, то на все A[CSSTARGET] будет повешен обработчик событий
        # который будет рассылать события EXECUTE_HREF_ACTION
        self.css_actions = False
        self.focus_activecontrol = True
        # При показе использует функцию showhtmldialog
        # при этом показывается просто диалоговое окно с WS_EX_LAYERED
        # использование
        # r = html_document(dialog_window = True).select_result()
        self.dialog_window = False
        # Принудительно создавать новые диалоговые окна для отображения в модальном режиме
        # например когда диалоговое окно показывается из диалогового окна
        # get_host_manager(TfmHTMLHost, False) - tkshtml_func.pas
        self.create_new_window = False
        # ITKSWindowManager
        self.iwindow = 0
        # Текущий номер страницы (для тех докуменов, которые это понимают)
        self.tabindex = 0

        # Возможность редактировать файлы встроенным редактором
        self.editor_enabled = False

        self.mainmenu_css = ''
        self.mainmenu = None

        # Названия файлов со стилями, которые надо проимпортировать
        self.styles = []
        self.create_style = False
        # Обработчик в document_complete
        self.on_document_complete = None

    def afterInit(self, *args, **kwargs):
        super(html_document, self).afterInit(*args, **kwargs)
        if self.prefs_filename:
            self.prefdata = pref.prefdata(self.prefs_filename)
        if not self.html and not self.filename:
            if self.styles:
                self.html = self.default_styled_html % (self.get_styles_import())
            else:
                self.html = self.default_html

    def create_style_element(self, css):
        e = self.find_first(css)
        if e:
            return element().create_element('style', self.get_styles_import(), e, insert_point=0)
        return None

    def get_styles_import(self):
        return '\n'.join(['@import url( %s );' % (fname,) for fname in self.styles])

    @property
    def activecontrol(self):
        return self.find_first('.activecontrol')

    @activecontrol.setter
    def activecontrol(self, el):
        ac = self.find_first('.activecontrol')
        if ac:
            if el and ac.he != el.he:
                ac.removeclass('activecontrol')
                el.addclass('activecontrol')
        elif el:
            el.addclass('activecontrol')

    def can_close(self):
        return True

    def get_root_element(self):
        body = self.find_first('body')
        if body:
            return body.parent()
        return None

    def min_width(self):
        return 0

    def min_height(self):
        return 0

    def get_inupdate(self):
        return self._inupdate

    inupdate = property(get_inupdate)

    def get_html_editor(self):
        import editor
        return editor.html_editor(self)

    def get_pref_path(self):
        return self.url_base[1:] or 'options'

    def do_read_prefs(self, prefs):
        super(html_document, self).do_read_prefs(prefs)
        self.options = {}
        d = self.prefs.get('document_options', None)
        if d:
            for key in d.keys():
                try:
                    self.options[key] = eval(d[key])
                except:
                    self.options[key] = d[key]

    def do_write_prefs(self, prefs):
        self.prefs['document_options'] = self.options
        super(html_document, self).do_write_prefs(prefs)

    def find_helement(self, css_selector):
        e = self.find_first(css_selector)
        if e:
            return e.he
        return 0

    def init_gui(self):
        super(html_document, self).init_gui()
        self.read_prefs()

    def deinit_gui(self):
        super(html_document, self).deinit_gui()
        self.write_prefs()

    def get_mainmenu(self):
        return self.mainmenu

    def doinsertmenu(self):
        mainmenu = self.get_mainmenu()
        if mainmenu:
            if self.mainmenu_css:
                return self.insert_menu_into(mainmenu, self.mainmenu_css)
            return self.insertmenu(mainmenu)
        return None

    def insertmenu(self, menu, menumode=MENU_MAINMENU, hlist=0):
        """
         Добавление пунктов меню к окну.
        :param menu: gtd.menu.menuitem.MenuItem
        :param menumode: int
        :param hlist: int
        :return: None
        """
        if menu:
            return HTMInsertMenu(self, menu, menumode, hlist)
        return None

    def read_prefs(self):
        try:
            self.prefs = {}
            if self.prefdata:
                self.prefs = self.prefdata.read_attrs_all(self.get_pref_path())
                self.do_read_prefs(self.prefs)
        except Exception, e:
            self.error(e, 'read_prefs')

    def write_prefs(self):
        if self.prefdata:
            for obj in self.behaviors_obj:
                obj.do_write_prefs(self.prefs)
            self.do_write_prefs(self.prefs)
            p = self.get_pref_path()
            for key in self.prefs.keys():
                self.prefdata.set_attrs('%s/%s' % (p, key), self.prefs[key])
            self.prefdata.write_xmlfile()

    def get_section(self, section):
        return self.prefs.get(section, {})

    def get_option(self, section, key, defvalue):
        """ получение значения настроек """
        return self.get_section(section).get(key, defvalue)

    def get_eval_value(self, v):
        if v and isinstance(v, basestring):
            try:
                v = eval(v)
            except:
                return v
        return v

    def get_eval_option(self, section, key, defvalue):
        """ получение объекта (int, bool, dict и т.д.) из настроек """
        v = self.get_option(section, key, defvalue)
        return self.get_eval_value(v)

    def set_option(self, section, options):
        """ сохранение настроек """
        if section not in self.prefs:
            self.prefs[section] = {}
        return self.prefs[section].update(options)

    def get_markup(self):
        return None

    def get_html(self, *args, **kwargs):
        super(html_document, self).get_html(*args, **kwargs)
        if self.filename:
            return self.load_data(self.filename, HLRT_DATA_HTML)
        else:
            return self.html

    def get_layout(self, refresh_callback = None):
        self.refresh_callback = refresh_callback
        return self

    def run(self, event_name = '', event_data = ''):
        return self.refresh(event_name, event_data)

    def refresh(self, event_name = '', event_data = '', *args, **kwargs):
        if self.refresh_callback:
            self.write_prefs()
            self.refresh_callback.run(event_name, event_data)
            self.read_prefs()
        return True

    def error(self, e, message):
        super(html_document, self).error(e, message)
        return show_error(e, message)

    def warning(self, message):
        return system.warning(message)

    @error_method_none
    def show(self, modal = False, iwindow = 0, config_mode = False, saveprior = False, defaultwindow=False, *args, **kwargs):
        self.modal = modal
        self.setkwargs(**kwargs)
        if self.dialog_window:
            return tkshtml.showhtmldialog(self, config_mode)
        return tkshtml.showhtml(self, modal, iwindow, config_mode, saveprior, defaultwindow)

    def modalresult(self, result, result_obj = None):
        self.result = result_obj
        return super(html_document, self).modalresult(result, result_obj)

    def load_data_request(self, url, data_type, hwndFrom):
        r = super(html_document, self).load_data_request(url, data_type, hwndFrom)
        if not r:
            if data_type == HLRT_DATA_HTML:
                return self.execute_url(url)
        return r

    def execute_url(self, url):
        return urls.urlcaller(self).call_url(url)

    def insert_body_actions(self, *args, **kwargs):
        body = element(self.visit('body')[0])
        try:
            return self.insert_actions(body, *args, **kwargs)
        finally:
            del body

    def insert_actions(self, root, actions):
        div = element().create_element('DIV', None, root)
        try:
            div.set_attr('class', 'toolbar')
            for act in actions:
                a = element().create_element('A', self.format_value(act[0]), div)
                a.set_attr('HREF', act[1])
                del a
        finally:
            del div

    def insert_body_table(self, *args, **kwargs):
        body = element(self.visit('body')[0])
        try:
            return self.insert_table(body, *args, **kwargs)
        finally:
            del body

    def insert_table(self, root, behavior_name, activecontrol = False, attrs = None):
        tbl = element().create_element('TABLE', None, root)
        tbl.set_style_attr('behavior', '%s column-resizer' % behavior_name, True)
        if attrs:
            for key in attrs:
                tbl.set_attr(key, attrs[key])
        if activecontrol:
            self.activecontrol = tbl
        del tbl
        return 0

    def insert_table_into(self, css_selector, behavior_name, activecontrol = False, attrs = None):
        root = self.find_first(css_selector)
        if root:
            return self.insert_table(root, behavior_name, activecontrol, attrs)
        return -1

    def insert_actions_into_element(self, div, actions):
        for act in actions:
            a = element().create_element('a', self.format_value(act[0]), div)
            a.set_attr('href', act[1])
            # css_selector для выполнения действий
            if len(act) > 2:
                a.set_attr('csstarget', act[2])
                if self.css_actions:
                    a.attach_handler(on_handle_event = self.on_handle_href_event)

    def insert_actions_into(self, css_selector, actions):
        div = self.find_first(css_selector)
        if div:
            self.insert_actions_into_element(div, actions)
            return True
        return False

    def insert_actions_into_element2(self, div, actions):
        for act in actions:
            a = element().create_element('a', self.format_value(act.name), div)
            a.set_attr('href', '#')
            a.attach_handler(on_handle_hyperlink_click=act.click)

    def insert_actions_into2(self, css_selector, actions):
        div = self.find_first(css_selector)
        if div:
            self.insert_actions_into_element2(div, actions)
            return True
        return False

    def exec_script(self, script, glb = None, lcl = None):
        try:
            script = '\n'.join(script.split('\r\n'))
            m = re.search('(\s*\n)*', script)
            if m:
                script = script[m.end():]
            m = re.search('^\s+', script)
            if m:
                script = '\n'.join([line[m.end():] for line in script.split('\n') if line[:m.end() + 1].find('#') == -1])
            # init local hear
            exec script in glb, lcl
        except Exception, e:
            self.error(e, 'exec_script')
            return False
        return True

    def run_script(self, script_element, glb = None, lcl = None):
        """ выполняет скрипт в элементе """
        try:
            script = script_element.innertext
            if script:
                return self.exec_script(script, glb, lcl)
            return False
        except Exception, e:
            self.error(e, 'run_script')

    def run_scripts(self):
        """ выполняем все, что находится в тегах script (text/python) """
        if self.script_enabled:
            document = self
            glb = globals()
            lcl = locals().copy()
            for he_script in self.select('script[type="text/python"]'):
                self.run_script(element(he_script), glb, lcl)
        elif self.select('script[type="text/python"]'):
            self.log_errormessage('Документ %s содержит встроенные скрипты. Выполнение отключено' % (self.filename))

    def can_focus_document(self):
        return self.focus_activecontrol and self.isforeground()

    def focus_on_active_control(self):
        if self.can_focus_document():
            maybe(self.activecontrol).focus()

    def document_complete(self, *args, **kwargs):
        super(html_document, self).document_complete(*args, **kwargs)
        if self.on_document_complete is not None:
            self.on_document_complete(self, *args, **kwargs)
        if not self.title:
            self.title = self.query('head title').get_innertext()
        self.doinsertmenu()
        if self.title:
            self.do_select(lambda e: e.set_html(self.title), '#title')
        if self.search_text:
            self.do_select(lambda e: e.set_value(self.search_text), 'input#search')
        self.busy_window = self.insert_window_element('busy', '', None, busy_window, into_element_css='#body')
        return 0

    def after_document_complete(self, *args, **kwargs):
        super(html_document, self).after_document_complete(*args, **kwargs)
        if self.css_actions:
            self.attach_handler('a[csstarget]', on_handle_event = self.on_handle_href_event)
        self.focus_on_active_control()
        self.run_scripts()
        self.query('*').post_event(DOCUMENT_COMPLETE)
        if self.create_style:
            self.create_style_element('body')
        return 0

    def on_handle_href_event(self, sender, cmd, he, target, reason, *args, **kwargs):
        if cmd == HYPERLINK_CLICK:
            e = element(target)
            for he in self.select(e['csstarget']):
                e.post_event(EXECUTE_HREF_ACTION, target = element(he))
            return True
        return False

    def register_behaviors(self):
        super(html_document, self).register_behaviors()
        if self.css_actions:
            from behavior_hyperlink import element_hyperlink
            self.register_behavior(element_hyperlink)
        import behavior_tabs
        self.register_behavior(behavior_tabs.element_tabs2)

    def tbl_select(self, he):
        search = element(he)
        try:
            if search.test_css('select[nsiname] > caption'):
               search = search.parent() 

            if search.test_css('input[nsiname]'):
                invalues =  {search['nsispec']: search.value}
                if search['nsiparams']:
                    try:
                        params = eval(search['nsiparams'])
                        invalues.update(params)
                    except:
                        pass
                d = system.select_nsi(search['nsiname'], invalues)
                if d:
                    value = d[search['nsispec']]
                    proc = search['nsiproc']
                    if proc and hasattr(self, proc):
                        f = getattr(self, proc)
                        search.value = f(value)
                    else:
                        search.value = value
                    desc = search['nsidesc']
                    if desc:
                        search['nsidescvalue'] = d[desc]
                return True

            elif search.test_css('select[nsiname]'):
                d = system.select_nsi(search['nsiname'], {search['nsispec']: search.value})
                if d:
                    value = d[search['nsispec']]
                    proc = search['nsiproc']
                    if proc and hasattr(self, proc):
                        f = getattr(self, proc)
                        search.find_first('caption').value = f(value)
                    else:
                        search.find_first('caption').value = value
                    desc = search['nsidesc']
                    if desc:
                        search['nsidescvalue'] = d[desc]
                return True

            return False
        finally:
            del search

    def nsi_lookup(self, nsiname, retvalue, indexfields, fieldvalues):
        return system.lookup(nsiname, retvalue, indexfields, fieldvalues)

    def on_key(self, he, cmd, target, key_code, alt_state):
        """ keyboard events """
        r = super(html_document, self).on_key(he, cmd, target, key_code, alt_state)
        if r:
            return r
        if cmd == KEY_DOWN:
            if key_code == VK_F4:
                return self.tbl_select(he)
            elif key_code == VK_F11:
                return self.inspect()
        return False

    def get_intrinsic_height(self):
        """ HTMLayoutGetElementIntrinsicHeight """
        body = self.find_first('body')
        if body:
            pbody = body.parent()
            try:
                r = body.get_rect(SELF_RELATIVE | MARGIN_BOX)
                width = r[2] - r[0]
                try:
                    return HTMLayoutGetElementIntrinsicHeight(pbody.he, width)
                except:
                    log_error(debug=True)
            finally:
                del body
                del pbody
        return 0

    def show_notify(self, area_css, root_css, n_message, popup_id = 'network_error', popup_class = 'notify warning'):
        area = self.find_first(area_css)
        try:
            if area:
                root_element = area.find_first(root_css)
                try:
                    if root_element:
                        popup = area.find_first('popup#%s' % (popup_id))
                        try:
                            if not popup:
                                popup = element().create_element('popup', None, area)
                                popup['id'] = popup_id
                                popup['class'] = popup_class
                                popup.set_html('<p>%s</p>' % (n_message))
                            rect = root_element.get_rect()
                            #HTMLayoutShowPopupAt(popup.he, rect[0] + 30, rect[1], 3, True)
                        finally:
                            del popup
                finally:
                    del root_element
        finally:
            del area

    @error_method_bool
    def show_select(self, modal = True, *args, **kwargs):
        return self.show(modal, *args, **kwargs) == RESULT_OK

    def select_result(self, *args, **kwargs):
        # self.log_whereami('before select_result')
        try:
            if self.show_select(*args, **kwargs):
                return self.result
            return None
        finally:
            pass
            # self.log_whereami('after select_result')

    def get_window_id(self):
        return HTMLayout_window_id(self, self.modal)

    def get_status_bar(self):
        from statusbar import statusbar_manager
        return statusbar_manager().get_bar(self.get_window_id())

    def set_status(self, status_html):
        sb = self.get_status_bar()
        return sb and sb.set_status(status_html) or False

    def begin_update(self):
        if self.busy_window:
            self._inupdate += 1
            if self._inupdate == 1:
                self.busy_window.show()

    def end_update(self, force=False):
        self._inupdate -= 1
        if not self._inupdate or force:
            self._inupdate = 0
            if self.busy_window:
                self.busy_window.hide()

    def get_current_id(self):
        if self.current_id_name:
            return self.ids.get(self.current_id_name)
        return None

    def set_current_id(self, value):
        if self.current_id_name:
            self.ids[self.current_id_name] = value

    current_id = property(get_current_id, set_current_id, None, 'default current_id property')

    def inspect(self, *args, **kwargs):
        self.info('inspect')
        return True

    #
    #  menu utils ===================================================================
    #

    def insert_menu_into(self, menu, css_selector):
        """ Вставка меню (gtd.menu.menuitem.MenuItem) в некий элемент (css_selector)
            при этом создается новый элемент внутри ul.menu-bar
            стили отображения находятся в ui/menu.css
        """
        if menu:
            toolbar = self.find_first(css_selector)
            if toolbar:
                menu_bar = element().create_element('UL', None, toolbar)
                menu_bar.addclass('menu-bar')
                self.convert_menu(menu, menu_bar, allow_root_links=True)
        return False

    def menu_property_changed(self, mi, property_index, property_value):
        li = element(mi.menu_id)
        if li and li.valid():
            if property_index == PROP_CAPTION:
                li.innertext = property_value
            elif property_index == PROP_ENABLED:
                if property_value:
                    li.set_state(0, STATE_DISABLED)
                else:
                    li.set_state(STATE_DISABLED, 0)
            elif property_index == PROP_CHECKED:
                if property_value:
                    li.set_state(STATE_CHECKED, 0)
                else:
                    li.set_state(0, STATE_CHECKED)
            elif property_index == PROP_VISIBLE:
                if property_value:
                    li.set_style_attr('visibility', 'visible')
                else:
                    li.set_style_attr('visibility', 'collapse')

    def attach_menu_handler(self, li, mi, *args, **kwargs):
        return li.attach_handler(layout = self, mi = mi, on_handle_menu_item_click = self.menuitem_click, *args, **kwargs)

    def menuitem_click(self, sender, he, target=0, reason=None, *args, **kwargs):
        sender.layout.query('body').post_event(MENUITEM_CLICK, reason=self.ref_reason(sender.mi))
        return True

    def handle_event(self, cmd, he, target, reason, *args, **kwargs):
        if cmd == MENUITEM_CLICK:
            mi = self.deref_reason(reason)
            if mi:
                mi.doclick(mi)
            return True
        return super(html_document, self).handle_event(cmd, he, target, reason, *args, **kwargs)

    def menuitem_handle_event(self, sender, cmd, he, target, reason, *args, **kwargs):
        if cmd == MENUITEM_ENABLED:
            if id(sender.mi) == reason:
                sender.mi.enabled = True
            return True
        elif cmd == MENUITEM_DISABLED:
            if id(sender.mi) == reason:
                sender.mi.enabled = False
            return True
        elif cmd == MENUITEM_VISIBLE:
            if id(sender.mi) == reason:
                sender.mi.visible = True
            return True
        elif cmd == MENUITEM_HIDDEN:
            if id(sender.mi) == reason:
                sender.mi.visible = False
            return True
        return False

    def convert_menu(self, root, root_element, allow_root_links=False):
        """
            создания соотвествия между пунктами меню (MenuItems) и li
            root - корневой элемент меню
            root_element - корневой html элемент меню
        """
        items = root.sortitems()
        items_len = len(items)
        hr = False
        for i in range(items_len):
            mi = items[i]
            if mi.caption == '-':
                if not root_element.test_css('UL') \
                       and 0 < i < (items_len - 1) and not hr:
                    element().create_element('HR', None, root_element, False)
                    hr = True
            else:
                hr = False
                li = None
                menu = None
                if not mi.items and allow_root_links:
                    a = element().create_element('A', mi.caption, root_element)
                    a['HREF'] = '#'
                    a.attach_handler(layout = self, mi = mi, on_handle_hyperlink_click = self.menuitem_click)
                else:
                    if root_element.test_css('ul.menu-bar') and mi.items:
                        li = root_element.find_first(':root>li[caption="%s"]' % (mi.caption))
                    if not li:
                        caption = u'%s<span .accesskey>%s</span>' % (to_ustr(mi.caption), mi.shortcut)
                        li = element().create_element('LI', '', root_element)
                        li.set_html(caption)
                        li['caption'] = mi.caption

                    if mi.html_class:
                        li.addclass(mi.html_class)
                    mi.menu_id = li.he
                    mi.on_property_change = self.menu_property_changed
                    self.menu_property_changed(mi, PROP_ENABLED, mi.enabled)
                    self.menu_property_changed(mi, PROP_VISIBLE, mi.visible)
                    if mi.items:
                        menu = li.find_first('menu')
                        if not menu:
                            menu = element().create_element('MENU', None, li)
                        if menu:
                            self.convert_menu(mi, menu, allow_root_links=False)
                    else:
                        self.attach_menu_handler(li, mi)

        # end menu utils ===========================================================

    def insert_window_element(self, element_id, css_show_element, show_element_proc, handler_cls, into_element_css='body', *args, **kwargs):
        """
            Создается элемент, на него вешается обработчик handler_cls
            показывается по mouse_down на show_element

            Используется для добавления user_filter и columns_settings

        """
        body = self.find_first(into_element_css)
        if body:
            window = element().create_element('div', None, body)
            window.addclass('window_at_center')
            window['id'] = element_id
            # handlers_cls должен наследоваться от element_behavior
            handler = handler_cls(self, he = window.he, *args, **kwargs)
            window.attach_handler_obj(handler)
            if css_show_element and show_element_proc:
                self.query(css_show_element).attach_handler(on_handle_hyperlink_click = show_element_proc)
            return handler
        return None

