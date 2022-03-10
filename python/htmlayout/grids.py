# -*- coding: cp1251 -*-

"""

   Таблицы.

   Описаны базовые классы для работы с таблицами

"""

import base64

from collections import OrderedDict
from tks.objects import baseobject
from gtd import error_method_none
from columns import *
from gtd.menu.menuitem import MenuItem
from gridcell import *

SORTED_COLUMN = '__sorted_column'


class SelectedRows(baseobject):
    def beforeInit(self, *args, **kwargs):
        super(SelectedRows, self).beforeInit(*args, **kwargs)
        # содержит отмеченные строки при self.allmarked = False и неотмеченные, если self.allmarked = True
        self.data = set()
        self.allmarked = False
        self.on_changed = None

    def changed(self):
        if self.on_changed:
            self.on_changed()

    def any(self):
        return self.allmarked or not not self.data

    def all(self):
        return self.allmarked and not self.data

    def iterator(self, grid_values, format_value=None):
        """
        grid_values: iterable object
        """
        if format_value is None:
            format_value = lambda v: v

        for item in grid_values:
            if self.allmarked:
                if self.data:
                    if format_value(item) not in self.data:
                        yield item
                else:
                    yield item
            elif format_value(item) in self.data:
                yield item

    def check(self, id, reason):
        """
        checkbox click
        """
        if reason == REASON_MARK:
            return self.mark(id)
        elif reason == REASON_UNMARK:
            return self.unmark(id)

    def _mark(self, id):
        if self.allmarked:
            self.data.discard(id)
        else:
            self.data.add(id)

    def _unmark(self, id):
        if self.allmarked:
            self.data.add(id)
        else:
            self.data.discard(id)

    def mark(self, id):
        self._mark(id)
        self.changed()
        return True

    def unmark(self, id):
        self._unmark(id)
        self.changed()
        return True

    def mark_range(self, *ids):
        for _id in ids:
            self._mark(_id)
        self.changed()
        return True

    def unmark_range(self, *ids):
        for _id in ids:
            self._unmark(_id)
        self.changed()
        return True

    def markall(self):
        self.data = set()
        self.allmarked = True
        self.changed()
        return True

    def unmarkall(self):
        self.data = set()
        self.allmarked = False
        self.changed()
        return True


class custom_grid(element_behavior):
    """ заготовка табличек, которая умеет сохранять ширину столбцов """

    event_types = element_behavior.event_types | HANDLE_TIMER

    def beforeInit(self, *args, **kwargs):
        super(custom_grid, self).beforeInit(*args, **kwargs)
        # идентификатор таблицы (ID) используется в css
        self._table_id = ''
        # css класс таблицы
        self.css_class_name = 'express'
        # настройка - сохранять ли ширину колонок
        self.save_prefs = False
        # колонки таблицы
        self.columns = []
        # изначальная колонка для сортировки
        self.init_sort_column = 0
        # направление сортировки
        self.sort_down = False
        # значение поля поиска
        self.search_text = u''
        # настройки
        self.prefs = {}
        # кол. фикс. строк таблицы.
        self.fixedrows = 1
        # кол. первых строк по которым опред. высота строки
        self.fixedlayout = 1
        # выделение строк с помощью колонки select_column
        self.multiselect = False
        # вычислять ширину колонки по заголовку
        self.calc_column_width = True
        # хранилище ID отмеченных строк
        self.selected_rows = SelectedRows(on_changed = self.marks_changed)
        # выполнять refresh() не более 1 раза за указанное кол-во мс.
        self.refresh_threshold = 10
        # для фокусировке на ячейке после refresh
        self.active_column = 0
        # текущий tr, чтобы при refresh текущая запись сохраняла свое относит. положение на экране
        self.tr_current_idx = 0
        # подчиненная таблица
        self.detail = False

    def afterInit(self, *args, **kwargs):
        super(custom_grid, self).afterInit(*args, **kwargs)
        tbl = self.get_element()
        if tbl['ID']:
            self.table_id = tbl['ID']
        elif self.table_id:
            tbl.set_attr('ID', self.table_id)

    def marks_changed(self):
        """ Изменение отмеченных записей """
        pass

    def before_init_data(self):
        super(custom_grid, self).before_init_data()
        if self.multiselect:
            self.layout.register_behavior(RowSelector)
            self.columns.insert(0, select_column())

    @property
    def table_id(self):
        return self._table_id

    @table_id.setter
    def table_id(self, value):
        self._table_id = value
        self.table_id_changed(value)

    def table_id_changed(self, value):
        pass

    def init_data(self, *args, **kwargs):
        super(custom_grid, self).init_data(*args, **kwargs)
        if self.table_id or self.css_class_name:
            tbl = self.get_element()
            try:
                if self.css_class_name:
                    tbl.append_attr('class', self.css_class_name)
                if self.fixedrows > 0:
                    tbl.set_attr('fixedrows', str(self.fixedrows))
                if self.fixedlayout > 0:
                    tbl.set_attr('fixedlayout', str(self.fixedlayout))
            finally:
                del tbl

    def on_timer(self, he, timerid=0):
        element(he).set_timer(0)
        self._refresh_on_time()

    def _refresh_on_time(self):
        self.do_write_prefs(self.prefs)
        self.get_element().post_event(TABLE_RECREATE)

    def refresh(self, *args, **kwargs):
        if self.refresh_threshold:
            e = self.get_element()
            e.set_timer(self.refresh_threshold)
        else:
            self._refresh_on_time()

    def do_refresh_data(self, *args, **kwargs):
        self.refresh(*args, **kwargs)
        return True

    def set_column_width(self, th, width):
        if width:
            th.set_style_attr('width', '%spx' % (width))

    def get_title_width(self, th):
        # ширину текста можно измерять только у отрисованного элемента
        # иначе возвращается 0
        th.update()
        return th.get_text_width() + EXTRA_SPACE

    def get_columns(self):
        return sorted(filter(lambda c: c.enabled, self.columns), key=lambda col: col.pos)

    def can_sort_column(self, idx):
        """ Определяет, можно ли сортировать по колонке с индексом idx """
        cols = self.get_columns()
        if idx >= 0 and idx < len(cols):
            column = cols[idx]
            return column.sortable and not self.is_dummy(column)
        return False

    def first_sortable_column_idx(self):
        for idx, column in enumerate(self.get_columns()):
            if column.sortable and not self.is_dummy(column):
                return idx
        return 0

    def is_dummy(self, column):
        return isinstance(column, dummy_column)

    def init_column_position(self):
        # устанавливаем pos, как они следуют в списке, если добавились новые колонки, мужду refresh
        for idx, col in enumerate(self.columns):
            if col.pos == 0:
                col.pos = (idx + 1) * 10
        for col in self.get_columns():
            pos = self.layout.get_eval_option(self.table_id, col.fieldname, {}).get('pos')
            if pos is not None:
                col.pos = pos

    def init_table_header(self, tbl):
        tr = element().create_element('TR', None, tbl)
        self.init_column_position()
        self.init_sort_column = self.first_sortable_column_idx()
        for idx, column in enumerate(self.get_columns()):
            th = element().create_element('TH', column.get_column_title(), tr)
            column.element_uid = th.get_uid()
            if column.sort_values:
                th.set_attr('sortattr', 'sortvalue')

            if column.rowselector:
                th.set_style_attr('behavior', 'rowselector')
                th.set_attr('rowselected', '0')

            pref_sorted_column = self.layout.get_eval_option(self.table_id, SORTED_COLUMN, {})
            if pref_sorted_column.get('fieldname') is not None and \
               column.fieldname == pref_sorted_column['fieldname']:
               self.init_sort_column = idx
               self.sort_down = pref_sorted_column.get('sort_down', False)

            if not (self.is_dummy(column) and column == self.columns[-1]):
                fp_dict = self.layout.get_eval_option(self.table_id, column.fieldname, {})
                if fp_dict:
                    self.set_column_width(th, fp_dict.get('width'))
                elif self.calc_column_width:
                    if column.width:
                        th.set_style_attr('width', column.width)
                    else:
                        self.set_column_width(th, self.get_title_width(th))
                elif column.width is not None:
                    th.set_style_attr('width', column.width)
            else:
                ## dumy_column для возможности настроить ширину последнего столбца.
                ## устанавливаем ширину до конца строки, иначе видимая часть строки после dummy - tr,
                th.set_style_attr('width', '100%%')
                pass

            for key in column.css:
                th.set_style_attr(key, column.css[key])


            del th
        del tr

    def do_write_prefs(self, prefs):
        if not self.save_prefs or not self.table_id:
            return
        column_prefs = prefs.get(self.table_id, {})

        tbl = self.get_element()
        tbl_width = tbl.get_width() if tbl else 0

        # th генерируеются только для column.enabled = True
        for column in sorted(filter(lambda c: c.enabled and c.fieldname, self.columns), key=lambda c: c.pos):
            if isinstance(column, dummy_column):
                continue
            try:
                col_pref = self.layout.get_eval_value(column_prefs.get(column.fieldname, '{}'))
                assert isinstance(col_pref, dict) == True
            except Exception as e:
                log_error(False, True)
                col_pref = {}
            column_prefs[column.fieldname] = col_pref
            col_pref.update(pos=column.pos)
            th = column.get_element(self.layout.hwnd)
            if th:
                if (th.checked or th.visited) and column.sortable:
                    column_prefs[SORTED_COLUMN] = {'fieldname': column.fieldname, 'sort_down': self.sort_down}
                # если таблица в скрытом блоке, то ее ширина и всех ее дочерних элементов не определяется
                if tbl_width:
                    col_pref.update(width=th.get_width())

        prefs[self.table_id] = column_prefs


# декоратор для методов, которые обрабазывают выбранные записи в таблице
def selected_records(func):
    def func_proxy(self, *args, **kwargs):
        recs = self.get_selected_records()
        if recs:
            for rec in recs:
                func(self, rec, *args, **kwargs)
            return True
        return False
    func_proxy.__doc__ = func.__doc__
    func_proxy.__name__ = func.__name__
    return func_proxy


STATE_GRID_ACTIVE = STATE_VISITED


class element_grid(custom_grid):

    behaviors = ('grid', )

    def beforeInit(self, *args, **kwargs):
        super(element_grid, self).beforeInit(*args, **kwargs)
        self._current_id = self.layout.ids.get(self.name, '')
        self.focus_table = True
        self.readonly = False
        # text-wrap: normal|none|unrestricted|suppress;
        self.text_wrap = 'none'
        # Данные (заполняются в get_data)
        self.data = []
        ## кол-во записей
        self.datalen = 0
        self.on_handle_id_changed = None
        # словарик для генерации контекстного меню
        # {'caption1': function(mi), 'cap2': (func(mi), groupindex), 'cap3': (func(mi), {'mi_param1': value, })}
        self.popup_row_menu = OrderedDict()
        self.on_editcurrent = None
        # Вызов editcurrent по нажатию на enter - может быть нежелателен,
        # если мы хотим обрабатывать VK_RETUN в другом месте
        self.edit_on_return = True
        self.row_behavior = None
        self._datadeffered = None
        self._dataqueue = None
        # выделять первую строку, если current_id задан, а tr не найден
        self.select_first_row = True

    def waitingfordata(self):
        return self._dataqueue is not None

    def get_behavior_name(self, beh_cls):
        return '{}-{}'.format(beh_cls.behaviors[0], self.table_id)

    def register_behavior(self, beh_cls, beh_name='', *args, **kwargs):
        if not beh_name:
            beh_name = self.get_behavior_name(beh_cls)
        return super(element_grid, self).register_behavior(beh_cls, beh_name, **kwargs)

    def on_init_grid_cell(self, gridcell):
        gridcell.table = self
        try:
            gridcell.column = self.get_columns()[int(gridcell.get_element()['column_index'])]
        except:
            gridcell.column = None

    def finalizeInit(self, *args, **kwargs):
        super(element_grid, self).finalizeInit(*args, **kwargs)
        if self.popup_row_menu:
            self.create_popupmenu()

    def format_value(self, *args, **kwargs):
        return html_format_value(*args, **kwargs)

    def get_id(self, rec):
        id_key = self.get_id_key()
        if rec and id_key:
            if hasattr(id_key, '__iter__'):
                return base64.b64encode(repr(tuple([rec[k] for k in id_key])))
            else:
                return rec[id_key]
        return ''

    def key_from_id(self, id):
        ''' обратная операция get_id()'''
        r = {}
        id_key = self.get_id_key()
        if id_key:
            if hasattr(id_key, '__iter__'):
                if id:
                    try:
                        id_values = eval(base64.b64decode(id))
                        r = dict(zip(id_key, id_values))
                    except:
                        self.vlog('Невозможно преобразовать идентификтор записи в ключ', id)
            else:
                r = {id_key: id}
        return r

    def key_from_current_id(self):
        ''' обратная операция get_id() для текущей записи'''
        return self.key_from_id(self.current_id)

    def get_id_key(self):
        return None

    def get_rec_number(self, key):
        """ индекс записи в self.data """
        for i, rec in enumerate(self.data):
            found = False
            for field, value in key.iteritems():
                if rec.get(field) != value:
                    found = False
                    break
                found = True
            if found:
                return i
        return -1

    def init_data_row(self, rec, tr):
        pass

    def init_search_text(self, rec, tr):
        if self.search_text:
            self.layout.search_table_row(tr, self.search_text.upper())

    def init_data_cell(self, rec, td, column):
        self.init_cell_atts(rec, td, column)
        self.init_cell_value(rec, td, column)
        self.init_cell_style(rec, td, column)

    def init_cell_atts(self, rec, td, column):
        if isinstance(column, check_column):
            td.set_attr('ID', 'checkbutton')
        elif isinstance(column, nsi_column):
            td.set_attr('nsiname', column.nsiname)
            td.set_attr('nsispec', column.nsispec)

        if column.css_class:
            # append не подходит, при прокрутке элемент не пересоздается, а менются только его значения и атрибуты
            td.set_attr('class', column.get_css_class(rec))

        if column.sort_values:
            td.set_attr('sortvalue', column.get_sort_value(rec))

        if column.rowselector:
            rowselected = '0'
            if len(self.selected_rows.data):
                tr = td.parent()
                if (tr and tr['ID'] not in self.selected_rows.data) == self.selected_rows.allmarked:
                    rowselected = '1'
            elif self.selected_rows.allmarked:
                rowselected = '1'

            td.set_attr('rowselected', rowselected)

        if column.maxlength:
            td.set_attr('maxlength', column.maxlength)

        if column.col_filter:
            td.set_attr('filter', column.col_filter)

        for key, value in column.atts.iteritems():
            td.set_attr(key, value)

    def init_cell_value(self, rec, td, column):
        column.init_cell_value(rec, td)

    def init_column_behavior(self, rec, td, column):
        column_beh_name = self.get_behavior_name(column.behavior)
        if column_beh_name not in self.registered_behaviors:
            self.register_behavior(column.behavior, column_beh_name, on_init=self.on_init_grid_cell)
        td.set_style_attr('behavior', column_beh_name)
        td.set_attr('edit_mask', column.edit_mask)

    def init_cell_style(self, rec, td, column):

        column.set_editable(False if self.readonly else None)

        if column.editable or column.focusable or column.behavior is not GridCell:
            self.init_column_behavior(rec, td, column)

        # с fixedlayout text-wrap не дружит
        if self.fixedlayout > 0 or not column.wordwrap:
            td.set_style_attr('text-wrap', self.text_wrap)

        if column.text_align:
            td.set_style_attr('text-align', column.text_align)

        if column.text_overflow:
            td.set_style_attr('text-overflow', column.text_overflow)

        for key in column.css:
            td.set_style_attr(key, column.css[key])

        column.init_cell_style(rec, td)

    def set_rec_id(self, tr, rec):
        id_rec = self.get_id(rec)
        tr.set_attr('ID', self.format_value(id_rec))
        return get_str(id_rec)

    def get_list(self, start=0, stop=0):
        """ Выдает slice из self.data
            Делать здесь запросы нельзя, т.к. get_list вызывается из нескольких мест
        """
        if start < stop:
            return self.data[start:stop]
        return self.data

    def data_changed(self):
        if hasattr(self, 'on_data_changed'):
            self.on_data_changed(self)
        if hasattr(self, 'on_init_current_id'):
            self.on_init_current_id(self)

    def prepare_data(self, *args, **kwargs):
        """ Здесь должна делаться выборка (например, select) """
        return []

    def get_data(self, *args, **kwargs):
        if self._datadeffered is not None:
            self.data = self._datadeffered
            self._datadeffered = None
        else:
            self.data = self.prepare_data(*args, **kwargs)
        self.datalen = len(self.data)
        self.data_changed()

    def get_data_list(self, *args, **kwargs):
        """ Вызывается во время построения таблицы. """
        self.get_data(*args, **kwargs)
        return self.get_list()

    def after_init_data(self, tbl):
        return True

    def init_table_header(self, tbl):
        super(element_grid, self).init_table_header(tbl)
        self.clear_groups()

    def clear_groups(self):
        """ Вызывается после формирования заголовка таблицы
            и перед получением данных
            для возможности обнуления информации о группах записей
        """
        return True

    def is_group(self, rec):
        """
           если вернуть True то будет добавлена запись TR с class="grouprow"
        """
        return False

    def init_group_row(self, rec, tr, td):
        """ Здесь можно задать параметры групповой записи. например название """
        return True

    def create_row(self, tbl, rec, position=-1, dindex = 0):
        """
        dindex - индекс записи в self.data
        """
        try:
            tr = element().create_element('TR', None, tbl, insert_point=position)
            if self.row_behavior:
                tr.set_style_attr('behavior', self.row_behavior)
            id_rec = self.set_rec_id(tr, rec)
            tr.current = id_rec and id_rec == self.current_id
            tr['dindex'] = dindex
            if self.popup_row_menu:
                tr.set_style_attr('context-menu', 'selector(menu#{table_id}_popup)'.format(table_id=self.table_id))
            self.init_data_row(rec, tr)
            for ind, column in enumerate(self.get_columns()):
                td = element().create_element('TD', None, tr, column)
                td['column_index'] = ind
                self.init_data_cell(rec, td, column)
            self.init_search_text(rec, tr)
            return tr
        except:
            log_error(False, True)

    def init_data(self, *args, **kwargs):
        super(element_grid, self).init_data()
        tbl = element(self.he)
        try:
            self.init_table_header(tbl)
            recs = self.get_data_list(*args, **kwargs)
            for idx, rec in enumerate(recs):
                if self.is_group(rec):
                    grouprow = element().create_element('TR', None, tbl)
                    grouprow.set_attr('class', 'grouprow')
                    grouprow.set_state(STATE_DISABLED, 0)
                    grouptd = element().create_element('TD', None, grouprow)
                    grouptd.set_attr('class', 'grouptd')
                    grouptd.set_attr('colspan', '%d' % (len(self.columns)))
                    self.init_group_row(rec, grouprow, grouptd)
                self.create_row(tbl, rec, dindex = idx)

            if self.init_sort_column is not None:
                tbl.post_event(TABLE_SORT_COLUMN, self.sort_down * SORT_DIRECTION_MOD + self.init_sort_column)

            if self.after_init_data(tbl):
                tbl.post_event(TABLE_SET_CURRENT_ID)
            tbl.post_event(TABLE_ID_CHANGED)

        finally:
            del tbl

    def get_current_id(self):
        return self._current_id

    def set_current_id(self, value, set_current_row=True):
        changed = False
        if self._current_id != value:
            self._current_id = value
            changed = True

        if hasattr(self.layout, 'ids'):
            self.layout.ids[self.table_id] = value

        table = self.get_element()

        if set_current_row:
            row = None
            rowClick = False
            if value:
                # ToDo: Надо переделать
                if isinstance(value, unicode):
                    value = value.encode('cp1251')
                row = table.find_first('tr[id="{}"]'.format(value))
            # если current_id не задан или строка с ним не найденa, выделяем первую строку
            if not row and (not value or self.select_first_row) and table.get_child_count() > self.fixedrows:
                row = table.get_child(self.fixedrows)
                rowClick = True

            if row:
                self.set_current_row(table, row, rowClick=rowClick)

        if changed:
            table.post_event(TABLE_ID_CHANGED)

    def get_current_index(self):
        """
           Текущий индекс текущей строчки таблицы относительно self.data
        """
        row = self.get_current_row(self.get_element())
        if row:
            return row.index()
        return -1

    def get_current_rec(self, idx = -1):
        """ Возвращает текущую запись
            ! idx - это позиция элемента в таблице
            после сортировки эта позиция уже не соответствует индексу в self.data
        """
        if idx == -1:
            idx = self.get_current_index()
        if idx != -1:
            dindex = int(self.get_element().get_child(idx)['dindex'])
            return self.data[dindex]
        return None

    def id_changed(self):
        if self.on_handle_id_changed:
            self.on_handle_id_changed(self)
        if self.current_id:
            rec = self.get_current_rec()
            self.current_record_changed(rec)
        else:
            self.current_record_changed(None)

    def current_record_changed(self, rec):
        pass

    def editcurrent(self, rec):
        """ Редактирование / выбор текущей записи """
        if self.on_editcurrent:
            self.on_editcurrent(self, rec)

    def no_current_record(self):
        self.info('Текущая запись не определена')

    def do_table_row_click(self, table, row, idx, *args, **kwargs):
        if table.he != row.he:
            #                                       mouse_click |
            # set_current_id -> set_current_row -> table_row_click -> set_current_id
            # здесь необходимо вызывать set_current_id без set_current_row
            # TODO: позаботиться о STATE_CHECKED
            self.set_current_id(get_str(row['ID']), set_current_row=False)
        return False

    def do_table_row_dbl_click(self, table, row, idx, *args, **kwargs):
        if table.he != row.he:
            self.editcurrent(self.get_current_rec(idx))
        return False

    def do_table_row_insert(self, table, row, idx, *args, **kwargs):
        return False

    def do_table_row_delete(self, table, row, idx, *args, **kwargs):
        return False

    def do_cell_data_changed(self, table, cell, *args, **kwargs):
        return False

    def do_active_cell_changed(self, table, cell, *args, **kwargs):
        return False

    def get_active(self):
        return self.get_element().get_state(STATE_GRID_ACTIVE)

    def set_active(self, value):
        if value:
            self.get_element().set_state(STATE_GRID_ACTIVE)
        else:
            self.get_element().set_state(0, STATE_GRID_ACTIVE)
        self.do_set_active(value)

    def do_set_active(self, value):
        pass

    current_id = property (get_current_id, set_current_id, None, 'current id property')
    active = property(get_active, set_active)

    def on_column_click(self, table, header_cell, *args, **kwargs):
        return table.post_event(TABLE_HEADER_CLICK, header_cell.index(), header_cell)

    def get_current_row(self, table):
        for element in element_iterator(table):
            if element.current:
                return element
        return None

    def get_checked_cell(self, row):
        for element in element_iterator(row):
            if element.checked:
                return element
        return None

    def set_current_row(self, table, row, keyboardStates=0, rowClick=True, dblClick=False, \
                        smooth=False, cur_row=None, cell_idx=None):
        """ set current row  """
        try:
            if row is None:
                return

            prev = cur_row or self.get_current_row(table)
            if prev:
                if prev.he != row.he:
                    ## drop state flags
                    prev.set_state(0, STATE_CURRENT | STATE_CHECKED)
            row.set_state(STATE_CURRENT | STATE_CHECKED)
            self.tr_current_idx = row.index()

            if not self.detail:
                # фокус на ячейку
                cell_idx = cell_idx if cell_idx is not None else self.active_column
                row.get_child(cell_idx).focus()

            scroll_info = table.get_scroll_info()
            # при возвращении в окно, событие set_current_id приходит до окончательного подсчета scrollinfo
            # высота contentsize может быть отрицательной
            if scroll_info[SI_CONTENTSIZE][C_HEIGHT] < 0 or 0 < scroll_info[SI_VIEWRECT][V_HEIGHT] < scroll_info[SI_CONTENTSIZE][C_HEIGHT]:
                row.scroll_to_view(False, smooth)

            # rowClick == False, если вызов из set_current_id()
            if rowClick:
                table.post_event(dblClick and TABLE_ROW_DBL_CLICK or TABLE_ROW_CLICK, row.index(), row)
        except:
            log_error(True, True)

    def table_row_click(self, table, *args, **kwargs):
        r = self.do_table_row_click(table, *args, **kwargs)
        if not r:
            return self.layout.table_row_click(self, table, *args, **kwargs)
        return r

    def table_row_dbl_click(self, table, *args, **kwargs):
        r = self.do_table_row_dbl_click(table, *args, **kwargs)
        if not r:
            return self.layout.table_row_dbl_click(self, table, *args, **kwargs)
        return r

    def table_row_insert(self, table, *args, **kwargs):
        if self.readonly:
            return False
        r = self.do_table_row_insert(table, *args, **kwargs)
        if not r:
            return self.layout.table_row_insert(self, table, *args, **kwargs)
        return r

    def table_row_delete(self, table, *args, **kwargs):
        if self.readonly:
            return False
        return self.do_table_row_delete(table, *args, **kwargs)

    def cell_data_changed(self, table, cell, *args, **kwargs):
        if self.readonly:
            return False
        return self.do_cell_data_changed(table, cell, *args, **kwargs)

    def active_cell_changed(self, table, cell, *args, **kwargs):
        return self.do_active_cell_changed(table, cell, *args, **kwargs)

    def target_element(self, parent, target):
        target_parent = target and target.parent()
        if target_parent is None:
            return
        if target_parent.he == parent.he:
            return target
        return self.target_element(parent, target_parent)

    def fixed_rows(self, table):
        try:
            return int(table.get_attr('fixedrows'))
        except:
            return 0

    def set_checked_row(self, table, row, toggle = False):
        if toggle:
            if row.get_state(STATE_CHECKED):
                row.set_state(0, STATE_CHECKED)
            else:
                row.set_state(STATE_CHECKED, 0)
        else:
            row.set_state(STATE_CHECKED, 0)

    def get_anchor(self, table):
        row = table.find_first('tr:anchor')
        try:
            if row and row.he:
                return row.index()
            return 0
        finally:
            del row

    def set_anchor(self, table, idx):
        row = table.find_first('tr:anchor')
        try:
            if row:
                row.set_state(0, STATE_ANCHOR, False)
            row = table.get_child(idx)
            if row:
                row.set_state(STATE_ANCHOR, 0, False)
        finally:
            del row

    def check_row(self, el):
        if not el.get_state(STATE_CHECKED):
            el.set_state(STATE_CHECKED, 0)

    def uncheck_row(self, el):
        if el.get_state(STATE_CHECKED):
            el.set_state(0, STATE_CHECKED)

    def checkall(self, table, checked):
        if checked:
            self.layout.do_select(self.check_row, 'tr', he = table.he)
        else:
            self.layout.do_select(self.uncheck_row, 'tr:checked', he = table.he)

    def mark_all_rows(self, select=None):
        if select is None:
            select = not self.selected_rows.allmarked
        self.get_element().post_event(TABLE_ROW_MARK, ROW_MARK_ALL | select)

    def table_row_mark(self, table, target, reason):
        """ Добавление/удаление ID отмеченных строк
            Событие приходит от td или th (он же и target) c bahavior: rowselector
        """
        tbl = self.get_element()
        mark_all = bool(reason & ROW_MARK_ALL)
        if mark_all:
            if reason & REASON_MARK:
                tbl.do_select(lambda e: e.set_attr('rowselected', '1'),
                        '%(tableid)s th[rowselected="0"], %(tableid)s th[rowselected="2"], %(tableid)s td[rowselected="0"]' % \
                        {'tableid': 'table#' + self.table_id}
                )
                return self.selected_rows.markall()
            else:
                tbl.do_select(lambda e: e.set_attr('rowselected', '0'),
                        '%(tableid)s th[rowselected="1"], %(tableid)s th[rowselected="2"], %(tableid)s td[rowselected="1"]' % \
                        {'tableid': 'table#' + self.table_id}
                )
                return self.selected_rows.unmarkall()

        tr = target.parent()
        if tr.get_type() != 'tr':
            tr = self.target_element(table, target)
            if not tr:
                return False

        tr_id = tr['ID']
        if reason & ROW_MARK_RANGE:
            if self.current_id:
                tr_prev = tbl.find_first('tr[id="%s"]' % self.current_id)
                if tr_prev:
                    tr_prev_selected = tr_prev.get_child(0)['rowselected'] == str(REASON_MARK)
                    tr_indexes = (tr.index(), tr_prev.index())
                    ids = [tr['ID'] for tr in tbl.children(min(tr_indexes), max(tr_indexes))]
                    for _id in ids:
                        tbl.do_select(lambda e: e.set_attr('rowselected', '1' if tr_prev_selected else '0'),
                                      'table#{tblid} tr[id="{trid}"] td:first-child'.format(tblid=self.table_id, trid=_id))

                    return self.selected_rows.mark_range(*ids) if tr_prev_selected else self.selected_rows.unmark_range(*ids)

        if reason & REASON_MARK:
            return self.selected_rows.mark(tr_id)
        else:
            if self.selected_rows.allmarked:
                # th checkbox indeterminate
                tbl.do_select(lambda e: e.set_attr('rowselected', '2'), 'table#%s th[rowselected="1"]' % self.table_id)
            return self.selected_rows.unmark(tr_id)

    def handle_event(self, cmd, he, target, reason, *args, **kwargs):
        el = element(he)
        t_el = element(target)
        if cmd == TABLE_ROW_DBL_CLICK:
            return self.table_row_dbl_click(el, t_el, reason)
        elif cmd == TABLE_ROW_CLICK:
            return self.table_row_click(el, t_el, reason)
        elif cmd == TABLE_ROW_INSERT:
            return self.table_row_insert(el, t_el, reason)
        elif cmd == TABLE_ROW_DELETE:
            return self.table_row_delete(el, t_el, reason)
        elif cmd == TABLE_SET_CURRENT_ROW:
            self._table_row_click(el, t_el)
            return True
        elif cmd == TABLE_ROW_MARK:
            return self.table_row_mark(el, t_el, reason)
        elif cmd == TABLE_REFRESH:
            if reason == SKIP_INIT:
                self.do_refresh_data()
            else:
                self.refresh()
            return True
        elif cmd == TABLE_INIT_DATA:
            self.init_data()
            return True
        elif cmd == CELL_DATA_CHANGED:
            return self.cell_data_changed(el, t_el)
        elif cmd == ACTIVE_CELL_CHANGED:
            return self.active_cell_changed(el, t_el)
        elif cmd == TABLE_EDIT_CURRENT:
            rec = self.get_current_rec()
            if rec:
                self.editcurrent(rec)
            else:
                self.no_current_record()
            return True
        elif cmd == TABLE_ID_CHANGED:
            self.id_changed()
            # Возвращаем False, чтобы остальные тоже смогли это обработать
            return False
        elif cmd == TABLE_SET_ACTIVE:
            self.active = (reason == 1)
            return True
        elif cmd == TABLE_SET_CURRENT_ID:
            self.current_id = self._current_id
            return True
        elif cmd == TABLE_SCROLL_TO_CURRENT:
            return self.scroll_to_current()
        elif cmd == TABLE_RECREATE:
            self.get_element().delete_children()
            self.init_data()
        elif cmd == TABLE_DATA_WAIT:
            self.waitfordata(self._dataqueue)
        elif cmd == TABLE_SET_READONLY:
            self.readonly = (reason == 1)
        else:
            return super(element_grid, self).handle_event(cmd, he, target, reason, *args, **kwargs)
        return False

    def gotdata(self, data):
        self._datadeffered = data
        self.get_element().post_event(TABLE_REFRESH, reason=SKIP_INIT)
        self.layout.end_update(True)

    def user_filter_changed(self, *args, **kwargs):
        self.selected_rows.unmarkall()

    def scroll_to_current(self):
        ctr = self.get_current_row(self.get_element())
        if ctr:
            ctr.scroll_to_view()
            return True
        return False

    def on_mouse(self, he, target, event_type, pt, mouseButtons, keyboardStates):
        r = super(element_grid, self).on_mouse(he, target, event_type, pt, mouseButtons, keyboardStates)
        if r:
            return r
        if not he:
            return False
        if event_type == MOUSE_WHEEL:
            return self.on_scroll(he, \
                                  target, \
                                  mouseButtons < 0 and SCROLL_STEP_PLUS or SCROLL_STEP_MINUS, \
                                  0, \
                                  True)

        if event_type not in (MOUSE_DOWN, MOUSE_DCLICK):
            return False
        return self._table_row_click(element(he), element(target), event_type, pt, mouseButtons, keyboardStates)

    def _table_row_click(self, table, t_el, event_type = 0, pt = None, mouseButtons = MAIN_MOUSE_BUTTON, keyboardStates = 0):
        """ внутренняя обработка нажатия на строку таблицы """
        row = self.target_element(table, t_el)
        if row:
            td_el = None
            if row.index() < self.fixed_rows(table):
                #click on the header cell
                header_cell = self.target_element(row, t_el)
                if header_cell:
                    self.on_column_click(table, header_cell)
                return mouseButtons == MAIN_MOUSE_BUTTON
            else:
                td_el = self.target_element(row, t_el)
            dblclick = mouseButtons == MAIN_MOUSE_BUTTON and event_type == MOUSE_DCLICK
            self.set_current_row(table, row, keyboardStates, dblClick=dblclick, cell_idx=td_el.index() if  td_el else 0)
            HTMLayoutUpdateWindow(table.handle(False))
        return False

    def on_key_down(self, he, target, key_code, alt_state):
        r = super(element_grid, self).on_key_down(he, target, key_code, alt_state)
        if r:
            return r
        table = element(he)
        el_target = element(target)
        if el_target.get_type() == 'tr':
            row = el_target
        else:
            row = self.get_current_row(table)
        try:
            if key_code == VK_DOWN:
                return self.row_down(row, alt_state)

            elif key_code == VK_UP:
                return self.row_up(row, alt_state)

            elif key_code == VK_HOME:
                if alt_state == CONTROL_KEY_PRESSED:
                    return self.first_row(alt_state)
                else:
                    return self.first_cell(row)

            elif key_code == VK_END:
                if alt_state == CONTROL_KEY_PRESSED:
                    return self.last_row(alt_state)
                else:
                    return self.last_cell(row)
            elif key_code == VK_PRIOR:
                return self.page_up(alt_state)

            elif key_code == VK_NEXT:
                return self.page_down(alt_state)

            elif key_code == VK_RETURN:
                if self.edit_on_return or self.readonly:
                    row and table.post_event(TABLE_ROW_DBL_CLICK, row.index(), row)
                    return True
                else:
                    return False

            elif key_code == VK_INSERT and not alt_state:
                if row:
                    table.post_event(TABLE_ROW_INSERT, row.index(), row)
                else:
                    table.post_event(TABLE_ROW_INSERT, 0, None)
                return True

            elif key_code == VK_DELETE and alt_state == CONTROL_KEY_PRESSED:
                row and table.post_event(TABLE_ROW_DELETE, row.index(), row)
                return True

            elif key_code == VK_LEFT:
                if row:
                    self.offset_left(row, alt_state)
                return True

            elif key_code == VK_RIGHT:
                if row:
                    self.offset_right(row, alt_state)
                return True

            elif key_code == VK_A and alt_state == CONTROL_KEY_PRESSED:
                self.mark_all_rows()

        finally:
            del row
            del table

    def row_down(self, cur_row, alt_state, *args):
        table = element(self.he)
        idx = cur_row and cur_row.index() + 1 or self.fixed_rows(table)
        row = None
        while idx < table.get_child_count():
            row = table.get_child(idx)
            if not row.visible():
                idx += 1
                continue
            self.set_current_row(table, row, alt_state)
            break
        del row
        return True

    def row_up(self, cur_row, alt_state, *args):
        table = element(self.he)
        if cur_row:
            idx = cur_row.index() - 1
        else:
            idx = table.get_child_count() - 1
        row = None
        while idx >= self.fixed_rows(table):
            row = table.get_child(idx)
            if not row.visible():
                idx -= 1
                continue
            self.set_current_row(table, row, alt_state)
            break
        del row
        return True

    def first_row(self, alt_state=0):
        table = element(self.he)
        idx = self.fixed_rows(table)
        while idx < table.get_child_count():
            row = table.get_child(idx)
            if not row.visible():
                idx += 1
                continue
            self.set_current_row(table, row, alt_state, smooth=True)
            break
        return True

    def first_cell(self, row):
        pass

    def last_row(self, alt_state=0):
        table = element(self.he)
        idx = table.get_child_count() - 1
        while idx >= self.fixed_rows(table):
            row = table.get_child(idx)
            if not row.visible():
                idx -= 1
                continue
            self.set_current_row(table, row, alt_state, smooth=True)
            break
        return True

    def last_cell(self, row):
        pass

    def page_up(self, alt_state=0):
        table = element(self.he)
        trc = table.get_rect(ROOT_RELATIVE | SCROLLABLE_AREA)
        y = trc[1] - (trc[3] - trc[1])
        first = self.fixed_rows(table)
        r, pr, nr = None, None, None
        for i in range(table.get_child_count() - 1, first - 1, -1):
            nr = table.get_child(i)
            if not nr.visible():
                continue
            pr = r
            r = nr
            if r.get_rect(ROOT_RELATIVE | BORDER_BOX)[1] < y:
                if pr:
                    r = pr
                break
        self.set_current_row(table, r, alt_state, smooth=True)
        del r
        del pr
        del nr
        return True

    def page_down(self, alt_state=0):
        table = element(self.he)
        trc = table.get_rect(ROOT_RELATIVE | SCROLLABLE_AREA)
        y = trc[3] + (trc[3] - trc[1])
        r = pr = nr = None
        for i in xrange(self.fixed_rows(table), table.get_child_count()):
            nr = table.get_child(i)
            if not nr.visible():
                continue
            pr = r
            r = nr
            if r.get_rect(ROOT_RELATIVE | BORDER_BOX)[3] > y:
                if pr:
                    r = pr
                break
        self.set_current_row(table, r, alt_state, smooth=True)
        del r
        del pr
        del nr
        return True

    def offset_left(self, row, alt_state=0):
        pass

    def offset_right(self, row, alt_state=0):
        pass

    @error_method_none
    def get_selected_records(self, *args, **kwargs):
        """Получить список выделенных записей"""
        if self.selected_rows.all():
            return self.data
        elif self.selected_rows.any():
            if self.selected_rows.allmarked:
                return [rec for rec in self.data if self.format_value(self.get_id(rec)) not in self.selected_rows.data]
            else:
                return [rec for rec in self.data if self.format_value(self.get_id(rec)) in self.selected_rows.data]
        else:
            currec = self.get_current_rec()
            return [] if currec is None else [currec, ]

    def create_popupmenu(self):
        body = self.layout.find_first('body')
        e = element()
        e.create_element('menu', None, body, True)
        e['ID'] = self.get_popupmenu_id()
        e.addclass('popup')
        root = self.get_popupmenu(MenuItem(None))
        if root.items:
            self.layout.convert_menu(root, e)
        return e

    def get_popupmenu_id(self):
        return '%s_popup' % (self.table_id)

    def get_popupmenu(self, root):
        for caption, value in self.popup_row_menu.iteritems():
            if hasattr(value, '__iter__'):
                on_click, params = value
                if isinstance(params, int):
                    params = {'groupindex': params}
            else:
                on_click = value
                params = {'groupindex': 100}
            MenuItem(root, caption, on_click, rec=self.get_current_rec, **params)
        return root

    def update_check_state(self, id, fieldname, state):
        """Изменилось состояние checkbox-а"""
        pass


class row_sorter(baseobject):

    def beforeInit(self, column_no, down = False, attr = None, *args, **kwargs):
        super(row_sorter, self).beforeInit(*args, **kwargs)
        self.column_no = column_no
        self.down = down
        self.attr = attr
        self.log_init()

    def compare(self, r1, r2):
        try:
            if not r1 or not r2:
                return 0
            c1 = HTMLayoutGetNthChild(r1, self.column_no)
            c2 = HTMLayoutGetNthChild(r2, self.column_no)
            if self.attr:
                t1 = HTMLayoutGetAttributeByName(c1, self.attr)
                t2 = HTMLayoutGetAttributeByName(c2, self.attr)
            else:
                t1 = HTMLayoutGetElementInnerText(c1)
                t2 = HTMLayoutGetElementInnerText(c2)
            return cmp(t1, t2) * (self.down and -1 or 1) or \
                   HTMLayoutGetElementIndex(r1) - HTMLayoutGetElementIndex(r2)
        except:
            return 0


class sortable_grid(element_grid):
    behaviors = ('sortable-grid', )

    def beforeInit(self, *args, **kwargs):
        super(sortable_grid, self).beforeInit(*args, **kwargs)
        self.sortable = True

    def on_column_click(self, table, header_cell, force_down = False, *args, **kwargs):
        super(sortable_grid, self).on_column_click(table, header_cell, *args, **kwargs)
        if not (self.sortable and self.can_sort_column(header_cell.index())):
            return False
        down = False
        for column in table.find('th:checked, th:visited'):
            if column.he == header_cell.he:
                down = column.get_state(STATE_CHECKED)
            column.set_state(0, STATE_CHECKED | STATE_VISITED)
        down = force_down or down
        header_cell.set_state(down and STATE_VISITED or STATE_CHECKED)
        ctr = self.get_current_row(table)
        try:
            self.sort_rows( table, header_cell.index(), down, header_cell['sortattr'] )
            if ctr:
                ctr.scroll_to_view()
            else:
                tr = table.find_first('tr[id]')
                try:
                    if tr:
                        self.set_current_row(table, tr, 0)
                finally:
                    del tr
        finally:
            del ctr
        return True

    def sort_rows(self, table, column_no, down = False, attr = None):
        rs = row_sorter(column_no, down, attr)
        fr = self.fixed_rows(table)
        self.init_sort_column = int(column_no)
        self.sort_down = down
        return table.sort(rs, fr)

    def handle_event(self, cmd, he, target, reason, *args, **kwargs):
        if cmd == TABLE_SORT_COLUMN:
            table = element(he)
            if table.get_child_count():
                down, columnindex = divmod(reason, SORT_DIRECTION_MOD)
                column = table.get_child(0).get_child(columnindex)
                self.on_column_click(table, column, force_down = not not down)
                table.update(REDRAW_NOW)
        else:
            return super(sortable_grid, self).handle_event(cmd, he, target, reason, *args, **kwargs)

    def update_current_row(self, new_values):
        table = self.get_element()
        row = self.get_current_row(table)
        if row:
            dindex = int(row['dindex'])
            current_rec = self.data[dindex]
            if current_rec:
                current_rec.update(new_values)
                row_idx = row.index()
                row.delete()
                tr = self.create_row(table, current_rec, position=row_idx, dindex=dindex)
                tr.get_child(self.active_column).focus()
                return True
        return False
