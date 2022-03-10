# -*- coding: cp1251 -*-

"""

    Описан класс для вставки в страницы - с фильтром и настройкой колонок

"""
from gtd.db.record_counter import RecordCounterJob
from gtd.html.vgrid import VirtualGrid
from gtd.html.columns import dummy_column
from gtd.html.table_filter import *
from gtd import error_method_bool, error_method_none
from gtd.html.layout import *
from gtd.html.columns_settings import *
from tks.russian import num_suffix


class custom_vgrid(VirtualGrid):
    def beforeInit(self, *args, **kwargs):
        super(custom_vgrid, self).beforeInit(*args, **kwargs)
        # Применение пользовательских опций - фильтра и окна настройки колонок
        self.custom_options = True
        # Обработчик событий пользовательского фильтра
        self.user_filter = None
        # Настройка колонок
        self.columns_settings = None
        # Элемент для отображения количества записей
        self.rowsnumber_selector = '#rowsnumber'
        # Элемент для очитки фильтра
        self.clearfilter_css = CLEARFILTER_CSS
        self.append_dummy_column = True
        # Сохраняем настройки
        self.save_prefs = True
        self.filter_window_id = ''
        self.filter_id = ''
        self.filter_title = 'Фильтр'
        self.show_filter_css = 'a[href="filter_show"]'
        self.columns_window_id = ''
        self.show_columns_setting_css = 'a[href="columns_settings_show"]'
        self.custom_data = None
        ## общее кол-во записей
        self._totallen = None
        ## подсчитывать общее количество в фоне
        self.totallenusejob = False # True

    def afterInit(self, *args, **kwargs):
        super(custom_vgrid, self).afterInit(*args, **kwargs)
        self.init_columns()
        if self.append_dummy_column:
            self.columns.append(dummy_column())

    @property
    def totallen(self):
        return (self._totallen if self._totallen else 0)

    @totallen.setter
    def totallen(self, value):
        self._totallen = value

    @property
    def totallenok(self):
        """
        True - общая длина набора данных определена
        False - общая длина набора данных в процессе определения
        """
        return (self._totallen is not None)

    def prepare_data(self, *args, **kwargs):
        if self.custom_data is not None:
            return self.custom_data
        return super(custom_vgrid, self).prepare_data(*args, **kwargs)

    def table_id_changed(self, value):
        super(custom_vgrid, self).table_id_changed(value)
        self.filter_window_id = '%s_filterwindow' % (value)
        self.filter_id = '%s_filter' % (value)
        self.columns_window_id = '%s_columns_settings' % (value)

    def init_columns(self):
        pass

    def before_init_data(self):
        super(custom_vgrid, self).before_init_data()
        if self.custom_options:
            self.init_user_filter()
            self.init_column_settings()

    def do_write_prefs(self, prefs):
        super(custom_vgrid, self).do_write_prefs(prefs)
        if self.user_filter:
            self.user_filter.do_write_prefs(prefs)
        if self.columns_settings:
            self.columns_settings.do_write_prefs(prefs)

    @error_method_bool
    def filter_show(self, *args, **kwargs):
        if self.user_filter:
            self.user_filter.show()
            return True
        return False

    def handle_event(self, cmd, he, target, reason, *args, **kwargs):
        if cmd == TABLE_SHOW_FILTER:
            return self.filter_show()
        return super(custom_vgrid, self).handle_event(cmd, he, target, reason, *args, **kwargs)

    @error_method_bool
    def columns_settings_show(self, *args, **kwargs):
        self.columns_settings.show()
        return True

    def get_filter_cls(self):
        return table_filter

    def get_search_fields(self):
        return []

    def init_user_filter(self):
        """ Инициализация фильтра """
        self.user_filter = self.layout.insert_window_element(
            self.filter_window_id, self.show_filter_css, self.filter_show, self.get_filter_cls(),
            custom_filters=self.get_custom_filters(),
            text_search_fields=self.get_search_fields(),
            filter_id=self.filter_id,
            title=self.filter_title,
            table=self,
            clearfilter_css=self.clearfilter_css,
            # into_element_css='#body'
            )

    def get_custom_filters(self):
        return []

    def user_filter_changed(self, *args, **kwargs):
        """ Фильтр изменился """
        super(custom_vgrid, self).user_filter_changed(*args, **kwargs)
        self.do_refresh_data(*args, **kwargs)

    def user_filter_enabled(self):
        return self.user_filter and self.user_filter.filter and self.user_filter.enabled

    def get_where(self):
        where = []
        if self.filter_key:
            where.append(self.filter_key)
        return where

    def data_changed(self):
        if self.totallenusejob:
            # если разрешен подсчет в фоне, то начнем определять общее количество записей при изменении набора данных
            self.totallen = self.get_recordcount(where=None, rcdone=self.on_recordcountdone, default_result=None)
        super(custom_vgrid, self).data_changed()

    def update_rows_number(self):
        waitimage = '<img src="common/busy.png"/>'
        if not self.totallenusejob:
            # подсчет в фоне запрещен - считаем записи синхронно
            self.totallen = self.get_recordcount(where=None, rcdone=None, default_result=None)
        if self.datalenok:
            msglist = ['В списке {0} запис{1}'.format(
                self.datalen,
                num_suffix(self.datalen, suffix24='и', suffix5='ей', suffix1='ь'))]
        else:
            msglist = ['В списке {0} записей'.format(waitimage)]
        if self.totallenok:
            if self.totallen != self.datalen:
                msglist.append('из {0}'.format(self.totallen))
        else:
            msglist.append('из {0}'.format(waitimage))
        self.layout.query(self.rowsnumber_selector).set_html(' '.join(msglist))

    def init_column_settings_profiles(self, cols):
        return {COLS_PROFILE_DEF: dict([(column.fieldname, column.visible) for column in cols])}

    def init_column_settings(self):
        """ Инициализация настроки колонок """
        cols = filter(lambda column: column.fieldname and column.column_setting, self.columns)
        self.columns_settings = self.layout.insert_window_element(
            self.columns_window_id, self.show_columns_setting_css, self.columns_settings_show, ColumnsSettings,
            profiles=self.init_column_settings_profiles(cols),
            columns=cols,
            table=self,
            prefs_section_profile='%s_columns_profile' % self.table_id,
            prefs_section_userprofile='%s_columns_userprofile' % self.table_id,
            # into_element_css='#body'
            )

    def get_recordcount(self, where=None, rcdone=None, default_result=0, *args, **kwargs):
        if self.custom_data is not None:
            return len(self.custom_data)
        w = self.get_where()
        if where:
            w.append(where)
        if self.totallenusejob and rcdone:
            params = {}
            _, count_sql = self.dm.get_select_clause_2(tblname=self.tablename, fieldnames='*',
                                                       where=tuple(w), order_by=None, group_by=None,
                                                       distinct=False, params=params,
                                                       *args, **kwargs)
            rcjob = RecordCounterJob(jobid=id(self),
                                     alias=self.dm.cfg.databasename,
                                     tblname=self.tablename,
                                     sql=count_sql,
                                     params=params)
            return rcjob.get_result(rcdone, default_result, 0)
        else:
            return self.get_datamanager().locate(self.tablename, tuple(w), *args, **kwargs)

    def on_recordcountdone(self, recordcount):
        """
        Callback подсчета общего количества записей (без учета фильтра)
        """
        if isinstance(recordcount, list):
            # бывает, что и набор данных возвращается. возьмем его длину.
            self.totallen = len(recordcount)
        else:
            self.totallen = recordcount if recordcount else 0
        self.update_rows_number()

    def get_filters_where(self):
        where = self.get_where()
        if self.user_filter and self.user_filter.filter and self.user_filter.enabled:
            where.append(self.user_filter.filter)
        return tuple(where)

