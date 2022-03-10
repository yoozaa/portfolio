# -*- coding: cp1251 -*-

"""

   Мой личный модуль доступа к SQLITE

   sqlite3.Binary

"""

import cdecimal
import datetime
import os
import re
import time

from sqlite3 import dbapi2 as sqlite
from gtd.db.manager import *
from gtd.db.dbstruct import *
from gtd.db.dbconsts import *
from gtd.db import get_struct_info
from gtd.mutex import *
from manager import *

from tks.strutils import to_ustr

# импорт для получения списка
try:
    import database
    from DB import *
except:
    ftAutoInc = 14
    ftBCD = 8
    ftBlob = 15
    ftBoolean = 5
    ftBytes = 12
    ftCurrency = 7
    ftCursor = 22
    ftDBaseOle = 20
    ftDate = 9
    ftDateTime = 11
    ftFloat = 6
    ftFmtMemo = 18
    ftGraphic = 17
    ftInteger = 3
    ftMemo = 16
    ftParadoxOle = 19
    ftSmallint = 2
    ftString = 1
    ftTime = 10
    ftTypedBinary = 21
    ftUnknown = 0
    ftVarBytes = 13
    ftWord = 4
    ftGUID = 35

from gtd.db import domains

from collections import OrderedDict

SQLITE_TIMEOUT = 30

SQLITE_LOCKS = {
    ALIAS_DATA: LOCK_DB_SQLITE_DATA,
    ALIAS_EXPRESS: LOCK_DB_SQLITE_EXPRESS,
}


RE_DATE_PATTERN = re.compile('(\d{4})-(\d{2})-(\d{2})')
# генерация GUID средствами самого SQLITE
SQLITE_GEN_GUID = "upper(hex(randomblob(4))) || '-' || upper(hex(randomblob(2))) || '-4' || substr(upper(hex(randomblob(2))),2) || '-' || substr('89AB',abs(random()) % 4 + 1, 1) || substr(upper(hex(randomblob(2))),2) || '-' || upper(hex(randomblob(6)))"


def str_to_date(value):
    if value and isinstance(value, basestring):
        m = RE_DATE_PATTERN.match(value)
        if m:
            return datetime.date(*(int(v) for v in m.groups()))
        else:
            return None
    else:
        return value


class SQLiteBinaryField(BinaryField):

    def get_value(self, value):
        if value:
            try:
                return str(value)
            except UnicodeEncodeError:
                return ''
        return value


def sqlite_upper(s):
    return to_ustr(s).upper()


def sqlite_lower(s):
    return to_ustr(s).lower()

def sqlite_highlight(value, substring, startsel, stopsel):
    # заменяет в строке value все вхождения substring на <startsel><substring><stopsel>
    # для подсвечивания результатов поиска
    if value:
        RE_ESCAPE_PATTERN = r'([[\](){}.+*^$|\\?-])'
        RE_ESCAPE_REPL = r'\\\1'
        pattern = u'({0})'.format(re.sub(RE_ESCAPE_PATTERN, RE_ESCAPE_REPL, substring))
        repl = ur'{0}\1{1}'.format(startsel, stopsel)
        res = re.sub(pattern, repl, value, flags=re.IGNORECASE + re.MULTILINE + re.UNICODE)
        return res
    return value


class sqlite_manager(sql_datamanager):
    # символы, запрещенные в строке для FTS поиска
    FTS_NOT_ALLOWED_CHARS = {ord(c): u' ' for c in u"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""}

    SQLITE_FTS_FTS4 = 'FTS4'
    SQLITE_FTS_FTS5 = 'FTS5'

    SQLITE_MASTER_TABLE = 'sqlite_master'
    SQLITE_MASTER_NAME = 'NAME'
    SQLITE_MASTER_ROOTPAGE = 'ROOTPAGE'
    SQLITE_MASTER_TYPE = 'TYPE'
    SQLITE_MASTER_TYPE_TABLE = 'table'
    SQLITE_MASTER_TYPE_INDEX = 'index'
    SQLITE_MASTER_TYPE_TRIGGER = 'trigger'
    SQLITE_MASTER_TBL_NAME = 'TBL_NAME'
    SQLITE_MASTER_SQL = 'SQL'
    SQLITE_AUTO_INDEX_PREFIX = 'sqlite_auto'
    SQLITE_SHADOW_CONTENT = '_content'
    SQLITE_SHADOW_SEGDIR = '_segdir'
    SQLITE_SHADOW_SEGMENTS = '_segments'
    SQLITE_SHADOW_STAT = '_stat'
    SQLITE_SHADOW_DOCSIZE = '_docsize'
    SQLITE_SHADOW_DATA = '_data'
    SQLITE_SHADOW_IDX = '_idx'
    SQLITE_SHADOW_CONFIG = '_config'
    TRIGGER_BEFORE = 'BEFORE'
    TRIGGER_AFTER = 'AFTER'
    TRIGGER_DELETE = 'DELETE'
    TRIGGER_INSERT = 'INSERT'
    TRIGGER_UPDATE = 'UPDATE'
    TRIGGER_TYPE_BD = (TRIGGER_BEFORE, TRIGGER_DELETE)
    TRIGGER_TYPE_BU = (TRIGGER_BEFORE, TRIGGER_UPDATE)
    TRIGGER_TYPE_AU = (TRIGGER_AFTER, TRIGGER_UPDATE)
    TRIGGER_TYPE_AI = (TRIGGER_AFTER, TRIGGER_INSERT)

    TRIGGER_AI = '_ai'

    SQLITE_FTS_TRIGGER_TYPE_2_NAME_SUFFIX = {
        SQLITE_FTS_FTS4:
            {
                TRIGGER_TYPE_BD: '_bd',
                TRIGGER_TYPE_BU: '_bu',
                TRIGGER_TYPE_AU: '_au',
                TRIGGER_TYPE_AI: '_ai'
            },
        SQLITE_FTS_FTS5:
            {
                TRIGGER_TYPE_BD: '_bd',
                TRIGGER_TYPE_BU: '_bu',
                TRIGGER_TYPE_AU: '_au',
                TRIGGER_TYPE_AI: '_ai'
            }
    }

    SQLITE_CREATE_FTS_FMT = {
        SQLITE_FTS_FTS4:
            u'''CREATE VIRTUAL TABLE {fts_table_name} USING FTS4(content='{table_name}', tokenize=icu, {field_list})''',
        SQLITE_FTS_FTS5:
            u'''CREATE VIRTUAL TABLE {fts_table_name} USING 
            FTS5(content='{table_name}', tokenize=unicode61, {field_list})'''
    }

    SQLITE_REBUILD_FTS4_FMT = u'''INSERT INTO {fts_table_name}({fts_table_name}) VALUES('rebuild')'''
    SQLITE_REBUILD_FTS_FMT = {
        SQLITE_FTS_FTS4: SQLITE_REBUILD_FTS4_FMT,
        SQLITE_FTS_FTS5: SQLITE_REBUILD_FTS4_FMT
    }

    SQLITE_TRIGGER_FTS_FMT = {
        SQLITE_FTS_FTS4:
            {
                TRIGGER_TYPE_BD:
                    """
                      CREATE TRIGGER {trigger_name} BEFORE DELETE ON {table_name} FOR EACH ROW 
                      BEGIN
                        DELETE FROM {fts_table_name} WHERE DOCID = OLD.ROWID; 
                      END
                    """,
                TRIGGER_TYPE_BU:
                    """
                      CREATE TRIGGER {trigger_name} BEFORE UPDATE OF {field_list} ON {table_name} FOR EACH ROW 
                      BEGIN
                        DELETE FROM {fts_table_name} WHERE DOCID = OLD.ROWID; 
                      END
                    """,
                TRIGGER_TYPE_AU:
                    """
                      CREATE TRIGGER {trigger_name} AFTER UPDATE OF {field_list} ON {table_name} FOR EACH ROW 
                      BEGIN
                        INSERT INTO {fts_table_name} (DOCID, {field_list}) VALUES (NEW.ROWID, {new_field_list}); 
                      END
                    """,
                TRIGGER_TYPE_AI:
                    """
                      CREATE TRIGGER {trigger_name} AFTER INSERT ON {table_name} FOR EACH ROW 
                      BEGIN
                        INSERT INTO {fts_table_name} (DOCID, {field_list}) VALUES (NEW.ROWID, {new_field_list}); 
                      END
                    """
            },
        SQLITE_FTS_FTS5:
            {
                TRIGGER_TYPE_BD:
                    """
                      CREATE TRIGGER {trigger_name} BEFORE DELETE ON {table_name} FOR EACH ROW 
                      BEGIN
                        INSERT INTO {fts_table_name} ({fts_table_name}, rowid, {field_list})
                          VALUES ('delete', old.rowid, {old_field_list});
                      END
                    """,
                TRIGGER_TYPE_BU:
                    """
                      CREATE TRIGGER {trigger_name} BEFORE UPDATE OF {field_list} ON {table_name} FOR EACH ROW 
                      BEGIN
                        INSERT INTO {fts_table_name} ({fts_table_name}, rowid, {field_list})
                          VALUES ('delete', old.rowid, {old_field_list});
                      END
                    """,
                TRIGGER_TYPE_AU:
                    """
                      CREATE TRIGGER {trigger_name} AFTER UPDATE OF {field_list} ON {table_name} FOR EACH ROW 
                      BEGIN
                        INSERT INTO {fts_table_name} (rowid, {field_list}) VALUES (new.rowid, {new_field_list}); 
                      END
                    """,
                TRIGGER_TYPE_AI:
                    """
                      CREATE TRIGGER {trigger_name} AFTER INSERT ON {table_name} FOR EACH ROW 
                      BEGIN
                        INSERT INTO {fts_table_name} (rowid, {field_list}) VALUES (new.rowid, {new_field_list}); 
                      END
                    """
            }
    }

    # re для выделения из описания индекса FTS имен полей
    # CREATE VIRTUAL TABLE f1 using FTS4(content='articles', tokenize=icu, g312c, group_name)
    SQLITE_CREATE_FTS_CRE = re.compile(r"""CREATE\s+VIRTUAL\s+TABLE\s+(?P<index_name>\w+)\s+
        USING\s+(?P<fts_name>\w+)\s*\(content=\'(?P<table_name>\w+)\'\s*,\s*tokenize=(?P<tokenize_name>[^,]+),
        \s*(?P<field_list>[^)]+)\)""", re.VERBOSE + re.IGNORECASE)

    # re для выделения из описания триггера имени и типа триггера, имени FTS индекса и списка полей.
    # смотри само описание триггера в add_ftstriggers
    SQLITE_TRIGGER_FTS_CRE = {
        SQLITE_FTS_FTS4: [
            re.compile(
                r"""CREATE\s+TRIGGER\s+(?P<trigger_name>\w+)\s+(?P<trigger_ba>BEFORE)
                    \s+(?P<trigger_crud>DELETE)\s+ON\s+(?P<table_name>\w+)\s+FOR\s+EACH\s+ROW\s+ 
                    BEGIN\s+
                        DELETE\s+FROM\s+(?P<fts_table_name>\w+)\s+WHERE\s+DOCID\s+=\s+OLD\.ROWID;\s+ 
                    END
                """, re.VERBOSE + re.IGNORECASE),
            re.compile(
                r"""CREATE\s+TRIGGER\s+(?P<trigger_name>\w+)\s+(?P<trigger_ba>AFTER)
                        \s+(?P<trigger_crud>INSERT)\s+ON\s+(?P<table_name>\w+)\s+FOR\s+EACH\s+ROW\s+ 
                        BEGIN\s+
                            INSERT\s+INTO\s+(?P<fts_table_name>\w+)\s+\(\s*DOCID,
                            \s*(?P<field_list>.*)\s*\)\s+VALUES\s+.*;\s+ 
                        END
                """, re.VERBOSE + re.IGNORECASE),
            re.compile(
                r"""CREATE\s+TRIGGER\s+(?P<trigger_name>\w+)\s+(?P<trigger_ba>BEFORE|AFTER)
                        \s+(?P<trigger_crud>UPDATE)\s+OF\s+(?P<field_list>.+)\s+ON\s+(?P<table_name>\w+)
                        \s+FOR\s+EACH\s+ROW\s+ 
                        BEGIN\s+
                            (?:(?:DELETE\s+FROM)|(?:INSERT\s+INTO))\s+(?P<fts_table_name>\w+)\s+.*\s+ 
                        END
                """, re.VERBOSE + re.IGNORECASE)
        ],
        SQLITE_FTS_FTS5: [
            re.compile(
                r"""CREATE\s+TRIGGER\s+(?P<trigger_name>\w+)\s+(?P<trigger_ba>BEFORE)
                    \s+(?P<trigger_crud>DELETE)\s+ON\s+(?P<table_name>\w+)\s+FOR\s+EACH\s+ROW\s+ 
                    BEGIN\s+
                        INSERT\s+INTO\s+(?P<fts_table_name>\w+)\s+\(\s*(?P<fts_table_name_1>\w+),\s*rowid,
                        \s*(?P<field_list>.*)\s*\)\s+VALUES\s+.*;\s+
                    END
                """, re.VERBOSE + re.IGNORECASE),
            re.compile(
                r"""CREATE\s+TRIGGER\s+(?P<trigger_name>\w+)\s+(?P<trigger_ba>AFTER)
                        \s+(?P<trigger_crud>INSERT)\s+ON\s+(?P<table_name>\w+)\s+FOR\s+EACH\s+ROW\s+ 
                        BEGIN\s+
                            INSERT\s+INTO\s+(?P<fts_table_name>\w+)\s+\(\s*rowid,
                            \s*(?P<field_list>.*)\s*\)\s+VALUES\s+.*;\s+ 
                        END
                """, re.VERBOSE + re.IGNORECASE),
            re.compile(
                r"""CREATE\s+TRIGGER\s+(?P<trigger_name>\w+)\s+(?P<trigger_ba>BEFORE|AFTER)
                        \s+(?P<trigger_crud>UPDATE)\s+OF\s+(?P<field_list>.+)\s+ON\s+(?P<table_name>\w+)
                        \s+FOR\s+EACH\s+ROW\s+ 
                        BEGIN\s+
                            INSERT\s+INTO\s+(?P<fts_table_name>\w+)\s+\(\s*(?P<field_list_1>.+)\s*\)\s+VALUES\s+.*;\s+
                        END
                """, re.VERBOSE + re.IGNORECASE)
        ],
    }

    SQLITE_TKS_HIGHLIGHT_FN = 'tks_highlight'  # имя пользовательской функции для подсветки результата поиска
    SQLITE_FTS_HIGHLIGHT_FMT = {
        SQLITE_FTS_FTS4:
            u"snippet({fts_table_name}, {start_match_text}, {end_match_text}, {ellipses_text}, {column_number}, {fragments})",
        SQLITE_FTS_FTS5:
            u"highlight({fts_table_name}, {column_number}, {start_match_text}, {end_match_text})"
    }
    SQLITE_LIKE_HIGHLIGHT_FMT = u"{function_name}({value}, {substring}, {start_match_text}, {end_match_text})"

    def beforeInit(self, *args, **kwargs):
        super(sqlite_manager, self).beforeInit(*args, **kwargs)
        self.alias = ''
        if self.cfg:
            self.dbname = self.cfg.get(PARAM_SQLITE_FILENAME)
            if hasattr(self.cfg, 'databasename'):
                self.alias = self.cfg.databasename
        else:
            self.dbname = ''
        self.conn = None
        self.db_type = DB_SQLITE2
        self.count_records = True
        # Реализованный query_records не дает возможности изменять данные
        self.supports_query_records = False
        # Есть ли реализация autoinc полей
        self.autoinc_enabled = False
        self.adapt_unicode = True
        # нужно ли заполнять стые поля в ключе значениями по умолчанию
        self.allow_fill_defaults = True
        # mutex
        self.lock_name = SQLITE_LOCKS.get(self.alias, LOCK_DB_SQLITE)
        # FTS - какой использовать
        self.fts = sqlite_manager.SQLITE_FTS_FTS5
        # использовать pragmas
        self.pragmas = True
        # ToDo убрать - для тестирования
        # self.can_delete_columns = True

    def afterInit(self, *args, **kwargs):
        super(sqlite_manager, self).afterInit(*args, **kwargs)
        if self.dbname is None:
            self.dbname = ''
        if self.conn is None and self.auto_connect:
            self.connect()

    def __del__(self):
        self.disconnect()

    def dict_factory(self, cursor, row):
        d = self.get_rec_factory()()
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def adapt_time(v):
        return sqlite.Timestamp(*v[:6])

    adapt_time = staticmethod(adapt_time)

    def convert_date(s):
        return str_to_date(s)

    convert_date = staticmethod(convert_date)

    def adapt_decimal(d):
        return str(d)

    adapt_decimal = staticmethod(adapt_decimal)

    def connect(self, just_test=False, *args, **kwargs):
        try:
            sqlite.register_converter('DATE', self.convert_date)
            sqlite.register_adapter(cdecimal.Decimal, self.adapt_decimal)
            self.conn = sqlite.connect(self.get_connection_string(just_test), timeout=SQLITE_TIMEOUT, detect_types=sqlite.PARSE_DECLTYPES)
            self.conn.row_factory = self.dict_factory
            #self.conn.create_function('upper', 1, sqlite_upper)
            #self.conn.create_function('lower', 1, sqlite_lower)
            self.conn.create_function(self.SQLITE_TKS_HIGHLIGHT_FN, 4, sqlite_highlight)
            self.do_set_force_str(self.force_str)
        except Exception, e:
            self.log('connection failed')
            if just_test:
                return self.format_error(e)
            self.show_error(e, 'sqlite connect')

    def do_set_force_str(self, value):
        if self.conn:
            if value:
                self.conn.text_factory = str
            else:
                self.conn.text_factory = unicode

    def disconnect(self, *args, **kwargs):
        if self.conn:
            try:
                try:
                    self.conn.close()
                except:
                    pass
            finally:
                self.conn = None

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def commit(self):
        if self.conn:
            self.conn.commit()

    def get_connection_string(self, just_test=False):
        r = self.dbname
        if r and not isinstance(r, unicode):
            r = unicode(r, self.encoding)
        if just_test:
            import os
            if not os.path.exists(r):
                raise Exception(u'Файл %s не существует' % (r))
        return r

    def cursor(self, *args, **kwargs):
        return self.conn.cursor(*args, **kwargs)

    def execute(self, sql, params=(), close_cursor=False):
        """ возвращает cursor с записями в виде массивов, если надо """
        if params is None:
            params = ()
        cur = self.cursor()
        cur.execute(sql, params)
        if close_cursor:
            cur.close()
            cur = None
        return cur

    def get_table_columns(self, tblname):
        r = OrderedDict()
        d = self.select_sql('table_info', 'PRAGMA table_info(%s)' % (tblname))
        if d:
            for rec in d:
                stype = rec[self.SQLITE_MASTER_TYPE]
                fname = rec[self.SQLITE_MASTER_NAME].lower()
                typesizematch = re.match(r'''(?P<type>.+)\s*\(\s*(?P<size>\d+)\s*\)''', stype)
                if typesizematch:
                    # тип с размером, например: varchar(10)
                    r[fname] = {
                        'data_type': typesizematch.group('type').strip().lower(),
                        'size': int(typesizematch.group('size'))}
                    continue
                typesize2match = re.match(r'''(?P<name>.+)\s*\(\s*(?P<size1>\d+),\s*(?P<size2>\d+)\s*\)''', stype)
                if typesize2match:
                    # тип с двумя размерами, например: numeric(10, 2). не используется?
                    r[fname] = {
                        'data_type': typesizematch.group('type').strip().lower(),
                        'size': int(typesizematch.group('size1'))}
                    continue
                # обычный тип
                r[fname] = {
                    'data_type': stype.strip().lower(),
                    'size': 0}
        return r

    def add_columns(self, tblname, tbl_info, columns):
        """ добавление полей таблицы """
        r = False
        for column in columns:
            if column.pk or column.required:
                raise ETableRecreatePending(tblname, column.fldname)
        for column in columns:
            self.execute('ALTER TABLE %s ADD %s' % (tblname, self.get_ddl_field_spec(tbl_info, column, typeconvert=self.typeconvert, keywords=self.KEYWORD_LIST)), None, True)
            self.log('creating field %s' % (column.fldname))
            r = True
        return r

    def delete_columns(self, tblname, columns):
        """ удаление полей таблицы """
        if columns:
            raise ETableRecreatePending(tblname, columns[0])
        return True

    def update_columns(self, tblname, si=None, just_check=False, reindex=False):
        """ обновление полей для существующей таблицы
            пока реализовано добавление и удаление полей
            just_check - просто проверить на наличие необходимых полей
        """
        #if tblname in ('tnvlook', 'edizm') and not reindex:
        #    raise ETableRecreatePending(tblname, 'VERSION')
        si = si or get_struct_info()
        columnswithsize = self.get_table_columns(tblname)
        columns = self.get_column_names(tblname)
        # добавление необходимых колонок
        columns_to_add = []
        for ind, field in enumerate(si.tables[tblname].fields):
            l_fieldname = field.fldname.lower()
            if l_fieldname not in columns:
                columns_to_add.append(field)
            elif field.pk and (ind < len(columns)) and (columns[ind] != l_fieldname):
                raise ETableRecreatePending(tblname, field.fldname)
        if columns_to_add:
            if just_check:
                # Проверка не пройдена
                self.log(u'Таблица %s. Не найдены поля %s. Требуется обновление.' % (tblname, ', '.join([field.fldname for field in columns_to_add])))
                return False
            self.add_columns(tblname, si.tables[tblname], columns_to_add)
        columns_to_delete = None
        if self.can_delete_columns:
            columns_to_delete = [column for column in columns if column.upper() not in si.tables[tblname].fieldnames]
            if columns_to_delete:
                if just_check:
                    # Проверка не пройдена
                    error = u'Таблица %s. Найдены неиспользуемые поля %s. Требуется обновление.' % (tblname, ', '.join(columns_to_delete))
                    self.errors.append(error)
                    self.log(error)
                    return False
                self.delete_columns(tblname, columns_to_delete)
        columns_to_resize = self.get_columns_to_resize(tblname, columnswithsize, si)
        if columns_to_resize:
            raise ETableRecreatePending(tblname, columns_to_resize[0].fldname)
        if columns_to_add or columns_to_delete:
            self.conn.commit()
        return True

    def get_columns_to_resize(self, tblname, columns, si):
        r = []
        for field in si.tables[tblname].fieldnames.itervalues():
            if (field.pdoxtype == ftString) and field.size:
                column = columns.get(field.fldname.lower())
                try:
                    if column and (int(column['size']) < int(field.size)):
                        r.append(field)
                except ValueError:
                    pass
            elif field.pdoxtype == ftMemo:
                column = columns.get(field.fldname.lower())
                if column and column['size'] and (int(column['size']) > 0):
                    # меняем тип поля если поле было varchar(n) (только оно имеет размер) а стало text
                    r.append(field)
            elif field.pdoxtype in [ftAutoInc, ftInteger]:
                column = columns.get(field.fldname.lower())
                if column and column['data_type'] and column['data_type'] != 'integer':
                    # меняем тип поля, видимо было smallint
                    r.append(field)
        return r

    def typeconvert(self, fieldspec):
        r = None
        if fieldspec.pdoxtype == ftString:
            r = domains.varchar(fieldspec.size)
        elif fieldspec.pdoxtype == ftMemo:
            r = domains.T_TEXT
        elif fieldspec.pdoxtype == ftAutoInc:
            r = domains.T_INT
        elif fieldspec.pdoxtype == ftSmallint:
            r = domains.T_SMALLINT
        elif fieldspec.pdoxtype == ftInteger:
            r = domains.T_INT
        elif fieldspec.pdoxtype == ftDate:
            r = domains.T_DATE
        elif fieldspec.pdoxtype == ftDateTime:
            r = domains.T_DATETIME
        elif fieldspec.pdoxtype == ftFloat:
            r = 'REAL'
        elif fieldspec.pdoxtype == ftBoolean:
            r = domains.T_BOOLEAN
        elif fieldspec.pdoxtype in (ftBlob, ftGraphic):
            r = 'BLOB'
        elif fieldspec.pdoxtype == ftGUID:
            r = domains.varchar(fieldspec.size)
        return r

    def create_tables(self, tblname='', si=None, just_check=False, reindex=True, allow_triggers_on_reindex=False, *args, **kwargs):
        create_ddl = 'no statement'
        si = si or get_struct_info()
        try:
            if self.conn:
                if tblname:
                    tbllist = (tblname in si.tables) and (tblname, ) or ()
                else:
                    tbllist = si.tables.keys()
                for tname in tbllist:
                    tbl_info = si.tables[tname]
                    if not self.table_exists(tname):
                        if just_check:
                            # проверка не пройдена - таблица не существует
                            error = u'Таблица %s не существует. Требуется обновление.' % tname
                            self.errors.append(error)
                            self.log(error)
                            return False
                        self.log(u'Создание таблицы %s' % tbl_info.tblname)
                        create_ddl = self.get_create_ddl(tbl_info, typeconvert=self.typeconvert, keywords=self.KEYWORD_LIST)
                        self.execute(create_ddl, None, close_cursor=True)
                        # нам нужны guid триггеры в любом случае
                        if not self.create_guidobjects(tname, tbl_info):
                            return False
                        if reindex:
                            self.index_table(tbl_info)
                            if not self.update_ftsobjects(tname, si, just_check):
                                return False
                    else:
                        self.vlog(u'Таблица %s существует' % tname)
                        if not self.update_columns(tname, si, just_check, reindex):
                            return False
                        if reindex or just_check:
                            if not self.check_indexes(tbl_info, False, just_check):
                                return False
                        if not self.update_ftsobjects(tname, si, just_check):
                            return False
                        if not self.check_guidobjects(tname, tbl_info, just_check):
                            if just_check:
                                return False
                            if reindex and allow_triggers_on_reindex:
                                return self.create_guidobjects(tname, tbl_info)
                            raise ETableRecreatePending(tname, '')
            else:
                raise Exception, 'Соединение с БД закрыто.'
        except ETableRecreatePending, e:
            self.errors.append(uformat(u'Требуется пересоздание таблицы %s', e.args[0]))
            raise
        except Exception, e:
            self.log(create_ddl)
            self.log(str(e))
            self.errors.append(str(e))
            raise
        return True

    def check_table_structure(self, tblname='', si=None):
        si = si or get_struct_info()
        return self.create_tables(tblname, si, just_check=True, reindex=False)

    def update_tables(self, tblname='', si=None, reindex=True, *args, **kwargs):
        super(sqlite_manager, self).update_tables(tblname, si, reindex)
        try:
            si = si or get_struct_info()
            return self.create_tables(tblname, si, just_check=False, reindex=reindex, *args, **kwargs)
        except ETableRecreatePending:
            return self.recreate_table(tblname, si)

    def get_tables(self, tblname = ''):
        """
         Получение списка таблиц
         get_table_list уже занято в db\manager.py
        """
        #ToDo: переделать на caseinsensitive
        key = {self.SQLITE_MASTER_TYPE : self.SQLITE_MASTER_TYPE_TABLE}
        if tblname:
            key[self.SQLITE_MASTER_NAME] = tblname.lower()
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_NAME, ), key)
        if d:
            virtualtables = self.get_virtual_tables()
            return [rec[self.SQLITE_MASTER_NAME] for rec in d if rec[self.SQLITE_MASTER_NAME] not in virtualtables]
        return []

    def get_virtual_tables(self, tblname=None, withshadow=True):
        """
         Получение списка виртуальных таблиц и таблиц их реализующих.
         FTS в sqlite реализуется с помощью виртуальных таблиц:
            Например:
            CREATE VIRTUAL TABLE apu USING FTS3(ID integer PRIMARY KEY, CODE char(13) , NAME text )
            На каждую виртуальную таблицу создается несколько (зависит от FTS3, FTS4 или FTS5)
            теневых (shadow) обычных таблицы с именами:
            "%_content", "%_segdir", "%_segments", - для FTS3
            "%_stat", and "%_docsize",  - дополнительно для FTS4
            %_data, %_idx, %_content, %_docsize, %_config  - для FTS5
        """
        # считаем, что виртуальная таблица содержит 0 в поле ROOTPAGE. Может быть это не так?
        key = {self.SQLITE_MASTER_TYPE: self.SQLITE_MASTER_TYPE_TABLE, self.SQLITE_MASTER_ROOTPAGE: 0}
        if tblname:
            key[self.SQLITE_MASTER_NAME] = tblname.lower()
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_NAME,), key)
        shadowpostfixes = \
            ['', '_content', '_segdir', '_segments', '_stat', '_docsize', '_data', '_idx', '_config'] if \
                withshadow else ['']
        if d:
            return ['{0}{1}'.format(rec[self.SQLITE_MASTER_NAME], postfix) for rec in d for postfix in shadowpostfixes]
        return []

    def get_indexes(self, tblname='', primary=False):
        key = {self.SQLITE_MASTER_TYPE : self.SQLITE_MASTER_TYPE_INDEX}
        if tblname:
            key[self.SQLITE_MASTER_TBL_NAME] = tblname.lower()
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_NAME, ), key)
        if d:
            return [rec[self.SQLITE_MASTER_NAME] for rec in d
                    if primary or not rec[self.SQLITE_MASTER_NAME].startswith('sqlite_auto')]
        return super(sqlite_manager, self).get_indexes(tblname, primary)

    def get_indexfieldnames(self, tblname, indexname):
        """Получение списка полей для индекса"""
        key = {self.SQLITE_MASTER_TYPE: self.SQLITE_MASTER_TYPE_INDEX}
        if tblname:
            key[self.SQLITE_MASTER_NAME] = indexname
            key[self.SQLITE_MASTER_TBL_NAME] = tblname.lower()
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_SQL, ), key)
        if d:
            sql = d[0][self.SQLITE_MASTER_SQL]
            return self.parse_index_sql(sql)
        return super(sqlite_manager, self).get_indexfieldnames(tblname, indexname)

    def get_table_info(self, tblname):
        d = self.select(self.SQLITE_MASTER_TABLE, ('*', ),
                        {self.SQLITE_MASTER_TYPE: self.SQLITE_MASTER_TYPE_TABLE,
                         self.SQLITE_MASTER_NAME: tblname})
        return d and d[0] or {}

    def filter_params_value(self, value, fieldobj=None, allow_adapt=True):
        # надо перенести в pdox
        # здесь должно быть False
        return True

    def get_param_value(self, key, value, fieldobj = None):
        value = super(sqlite_manager, self).get_param_value(key, value, fieldobj)
        if fieldobj or self.is_datafield(key):
            return value
        if isinstance(value, time.struct_time) or (isinstance(value, tuple) and len(value) > 5):
            return sqlite.Timestamp(*value[:6])
        elif isinstance(value, str) and not self.force_str:
            try:
                return unicode(value, self.get_field_encoding(key))
            except:
                return value
        elif isinstance(value, datetime.datetime):
            return sqlite.Timestamp(*value.timetuple()[:6])
        elif isinstance(value, datetime.date):
            return sqlite.Date(value.year, value.month, value.day)
        return value

    def dosql(self, tblname, sql, values=None, fields=None, ti=None, *args, **kwargs):
        r = 0
        q = self.create_query(tblname)
        try:
            try:
                q.SQL = [sql, ]
                q.params = self.get_params(values, fields, ti)
                with LockBlock(self.lock_name):
                    q.ExecSQL()
                    if q.cursor.rowcount <= 0:
                        return 0
                    else:
                        r = q.cursor.rowcount
                        self.conn.commit()
                        return r
            except EXMLCompressException, e:
                self.log_whereami(e, tblname)
            except sqlite.IntegrityError, e:
                self.log_whereami(e, tblname, sql)
                raise EKeyViolation(*e.args)
            except Exception, e:
                self.log_whereami(e, tblname, sql)
                self.show_error(e, sql)
                if self.raise_error:
                    raise
                return 0
        finally:
            del q

    def create_query(self, tblname, enable_cache=True):
        if self.conn:
            return sqlite_query(self.conn.cursor(), enable_cache)
        else:
            return None

    def get_records(self, tblname, sql, where=None, start=0, limit=0, count_sql=None, serverside=False, *args, **kwargs):
        q = self.create_query(tblname, not serverside)
        try:
            q.SQL = [sql, ]
            if limit:
                q.SQL.append(' LIMIT %d' % limit)
            if start > 0:
                q.SQL.append(' OFFSET %d' % start)
            q.params = self.get_params(where)
            if count_sql:
                cur = self.conn.cursor()
                if q.params:
                    cur.execute(''.join(count_sql), q.params)
                else:
                    cur.execute(''.join(count_sql))
                record = cur.fetchone()
                q.rcount = record.values()[0]
            q.Open()
        except Exception, e:
            self.rollback()
            self.show_error(e, sql)
            if self.raise_error:
                raise
            return None
        return sqlite_records(self, q, 0, 0, *args, **kwargs)

    def get_binary_param_value(self, key, value):
        return sqlite.Binary(key.set_value(value))

    def xmlcompressedfield(self, *args, **kwargs):
        return self.binaryfield(*args, **kwargs)

    def binaryfield(self, *args, **kwargs):
        return SQLiteBinaryField(*args, **kwargs)

    def connection_ok(self):
        """ Определяет, что подключение к базе данных присутствует """
        return self.conn is not None

    def check_database(self):
        return os.path.exists(self.dbname)

    def set_journal_mode(self, journal_mode):
        if self.conn and self.pragmas:
            with LockBlock(self.lock_name):
                if not journal_mode:
                    self.conn.execute('PRAGMA journal_mode = OFF')
                    self.conn.execute('PRAGMA synchronous = OFF')
                else:
                    self.conn.execute('PRAGMA journal_mode = MEMORY')
                    self.conn.execute('PRAGMA synchronous = NORMAL')

    def set_autocommit(self, autocommit):
        if self.conn:
            if autocommit:
                self.conn.isolation_level = None
            else:
                self.conn.isolation_level = 'DEFERRED'

    def create_database(self, si=None):
        return self.create_tables('', si, False)

    def get_column_names(self, tblname):
        return self.get_table_columns(tblname).keys()

    def process_match_expr(self, parentmatchexpr=None, parentmatchop=None, childmatchexpr=None, childmatchop=None,
                           otherexpr=None, params=None, **kwargs):
        """
        Обработать собранные условия match в поддереве: слить с родительским или уже вернуть SQL
        """
        if childmatchexpr:
            # был match. надо объединить с родительскими выражениями, если возможно.
            if parentmatchexpr is None:
                # верхний уровень, просто вернем SQL
                return self.get_match_sql(matchexpr=childmatchexpr, matchop=childmatchop, params=params, **kwargs)
            else:
                # где-то в середине дерева
                self.merge_match_expr(parentmatchexpr=parentmatchexpr, parentmatchop=parentmatchop,
                                      childmatchexpr=childmatchexpr, childmatchop=childmatchop,
                                      otherexpr=otherexpr, params=params, **kwargs)
        return None

    def get_match_sql(self, matchexpr=None, matchop=None, params=None, **kwargs):
        """
        :param matchexpr: Словарь <имя FTS таблицы>-><выражение для match - строка>
        :param params: Словарь параметров, куда будем добавлять выражения
        :param kwargs:
        :return: строка SQL
        """
        if matchexpr and matchop:
            sql = matchop.join([
                u'match({0}, {1})'.format(
                    self.format_param_key(ftsindexname, match_param_value, params=params, from_where=True),
                    ftsindexname)
                for ftsindexname, match_param_value in matchexpr.iteritems()
            ])
            return sql
        return

    def merge_match_expr(self, parentmatchexpr=None, parentmatchop=None, childmatchexpr=None, childmatchop=None,
                         otherexpr=None, params=None, **kwargs):
        """
        Пытаемся слить два дерева - родительское и детское с использованием родительской операции. Если родительская
        операция не совпадает с операцией в детском дереве и были еще какие-то условия (otherexpr),
        то мы такое не умеем и ломаемся.
        """
        if parentmatchexpr is not None:
            if childmatchexpr:
                if (parentmatchop != childmatchop) and otherexpr:
                    raise NotImplementedError('SQLite match tree problem!')
                else:
                    for ftsindexname, match_param_value in childmatchexpr.iteritems():
                        # собираем все выражения в matchexpr
                        self.matchexpr_add_value(parentmatchexpr, parentmatchop, ftsindexname, match_param_value)

    @staticmethod
    def matchexpr_add_value(matchexpr, matchop, ftsindexname, value):
        """
        Добавить (соединить оператором matchop) новое значение для match выражения по таблице ftsindexname.
        """
        new_match_param_value = u'({0})'.format(value)
        old_match_param_value = matchexpr.get(ftsindexname, None)
        if old_match_param_value:
            # старое значение уже в скобках
            new_match_param_value = u'({0} {1} {2})'.format(old_match_param_value, matchop, new_match_param_value)
        matchexpr[ftsindexname] = new_match_param_value

    def format_where_match_tnv_db(self, key, sign, value, emptystr_is_null=None, params=None, **kwargs):
        # MATCH sqlite - свой синтаксис
        if isinstance(value, basestring):
            value = [value]
        if isinstance(value, list):
            searchstring = u' AND '.join([u'{0}*'.format(word.lower()) for word in value])
            param_key = self.format_param_key(key, searchstring, params=params, from_where=True)
            return u'({0} {1} {2})'.format(key, sign, param_key)
        else:
            return ''

    def format_where_match(self, key, sign, value, emptystr_is_null=None, params=None,
                           tblexpr=None, fieldexpr=None, rankexpr=None, osign=sql_datamanager.OS_MATCH_START,
                           ftsconcatfieldsdict=None, highlightfieldnamesuffix='',
                           highlight=False, startsel='', stopsel='', tblname=None,
                           matchexpr=None, matchop=None, **kwargs):
        """
        MATCH в SQLITE - свой синтаксис:
            match(<query_string>, <fts_table_name>)

        По умолчанию поиск идет по всем полям таблицы <fts_table_name>.
        Для одной таблицы в SQL запросе может быть только ОДИН вызов match!!!
        Если нужен поиск по конкретному полю, то нужно использовать конструкцию:
            match('description:блаблабла', articles_g31_1_fts_fts4) для поиска по полю description.

        <query_string> должна быть разбита на слова и они должны быть соединены с помощью
        AND, OR, NOT (верхний регистр обязателен!!!) и скобок.
        Каждое слово может завершаться *, тогда будет поиск по началу слова. Если необходим поиск по фразе,
        то слова ее образующие должны быть заключены в двойные кавычки. Примеры:
            "водка без пива"  - будет искаться тест содержащий фрагмент "водка без пива"
            "пив* вод*" - поиск по началу слов.

        FTS4: Для выделения найденного фрагмента в тексте используется функция snippet со следующими аргументами:
            snippet(<fts_table_name>, <start_match_text>, <end_match_text>, <ellipses_text>, <column_number>, <fragments>)
            <column_number> - номер колонки в <fts_table_name> от 0. -1 - использовать текст из любой колонки.
            <fragments> - будем использовать -64.
        FTS5: Для выделения найденного фрагмента используется функция highlight о следующими аргументами:
            highlight(<fts_table_name>, <column_number>, <start_match_text>, <end_match_text>)

        В части FROM <fts_table_name> должна объединяться с базовой <table_name> inner join'ом по полям rowid:
        ... FROM articles INNER JOIN articles_g31_1_fts_fts4 on articles.rowid = articles_g31_1_fts_fts4.rowid ...


        Если поле, по которому ищем, составное FTS поле, то можем добавить подсветку результатов для составляющих его
        полей.
        Для этого надо передать словарь ftsconcatfieldsdict, <имя составного FTS поля>-><список имен полей,
        требующих подсветки>.
        Тогда в словарь fieldexpr будут добавлены выражения для полей из соответствующего списка, а к имени поля
        будет добавлен
        суффикс highlightfieldnamesuffix (чтобы можно было получать оригинальное и подсвеченное значение поля). При
        использовании суффикса имена полей с суффиксами должны присутствовать в запрашиваемом списке полей.
        """
        SNIPPET_ELLIPSES = '...'
        SNIPPET_TOKENS = -64
        ROWID_FIELDNAME = 'rowid'
        LIKE_ESCAPE_CHAR = '\\'
        ftsconcatfieldsdict = {} if ftsconcatfieldsdict is None else ftsconcatfieldsdict
        fieldname = DataManager.unqualify_field_name(key)
        ftsindexname, ftsmainfield, ftsfieldlist = self.get_ftsindexinfo_by_fieldname(tblname, fieldname)
        siindexes = self.get_ftsindexes_from_struct_info(None, tblname)
        if siindexes is None:
            # Описание таблицы не найдено, считаем, что это модуль tnved (см. gtd/modules/tnved/htmldoc.py), который
            # использует статические таблицы fts4 напрямую (tnv.db3), и вызовем для него старую версию
            # format_where_match
            return self.format_where_match_tnv_db(key, sign, value, emptystr_is_null, params, **kwargs)
        words_match, words_like = self.parse_value_for_format_where_match(value)
        sql_list = []
        if words_match or words_like:
            # Общие для match и like параметры и join
            if highlight:
                startsel_param_key = self.format_param_key('startsel', startsel, params=params, from_where=True)
                stopsel_param_key = self.format_param_key('stopsel', stopsel, params=params, from_where=True)
            field_qualification = tblname
            if words_match:
                # добавим JOIN для нашей FTS таблицы.
                tblexpr[ftsindexname] = {
                    DataManager.JD_TABLE: ftsindexname,
                    DataManager.JD_JOIN_TYPE: DataManager.JD_JOIN_TYPE_INNER,
                    DataManager.JD_JOIN_CONDITION: {
                        '{0}{1}.{2}'.format(DataManager.OS_FIELD, tblname, ROWID_FIELDNAME):
                            '{0}.{1}'.format(ftsindexname, ROWID_FIELDNAME)}
                }
                field_qualification = ftsindexname
                # сформировать аргумент для вызова match:
                # если поле, по которому мы ищем составное, то будем искать по всей таблице,
                # если мы ищем по конкретному полю, то строка поиска должна иметь вид:
                # <field_name>:<SPACE><search_string>[*]
                # !!!
                # Пробел после двоеточия очень важен, так как если <search_string> заключена в "",
                # то в FTS4 возникает ошибка SQLite: malformed MATCH expression
                # А с пробелом в FTS4 <field_name> не работает - поиск происходит по всем полям.
                # В FTS5 - все хорошо.
                # !!!
                # OS_MATCH_PHRASE - поиск полной фразы, просто заключаем строку в кавычки
                match_param_value = u' AND '.join([
                    u'{field_name}{quote}{value}{quote}{value_postfix}'.format(
                        field_name=u'' if fieldname in ftsconcatfieldsdict else fieldname.lower() + u': ',
                        value=onevalue,
                        value_postfix=u'*' if osign == self.OS_MATCH_START else u'',
                        quote=u'"' if osign == self.OS_MATCH_PHRASE else u'')
                    for onevalue in words_match])
                if match_param_value:
                    if matchexpr is None:
                        param_key = self.format_param_key(fieldname, match_param_value, params=params, from_where=True)
                        sql_list.append('match({0}, {1})'.format(param_key, ftsindexname))
                    else:
                        # собираем все выражения в matchexpr
                        self.matchexpr_add_value(matchexpr, matchop, ftsindexname, match_param_value)
                #TODO: RANK!!!
                #rankexpr.append("ts_rank(to_tsvector({0}, {1}), {2})".format(PGFTS_REGCONFIG, key, table_key))
                if highlight:
                    # Составное FTS поле, используется только для поиска, в результирующей таблице не показывается,
                    # поэтому надо добавить подсветку только для полей, составляющих FTS поле.
                    # А если поле не составное, то добавляем подстветку только для него.
                    # snippet(articles_g31_1_fts_fts4, "<emp>", "</emp>", "...", <field_index>, -64) as g312c_hl,
                    ellipses_param_key = self.format_param_key('ellipses', SNIPPET_ELLIPSES, params=params,
                                                               from_where=True)
                    concatfields = ftsconcatfieldsdict.get(fieldname, [fieldname])
                    fieldexpr.update({cf + highlightfieldnamesuffix:
                        self.SQLITE_FTS_HIGHLIGHT_FMT[self.fts].format(
                            fts_table_name=ftsindexname,
                            start_match_text=startsel_param_key,
                            end_match_text=stopsel_param_key,
                            ellipses_text=ellipses_param_key,
                            column_number=ftsfieldlist.index(cf) if cf in ftsfieldlist else -1,
                            fragments=SNIPPET_TOKENS
                        ) for cf in concatfields})
            if words_like:
                # в запросе есть текст для LIKE, текст будем заключать в %...%
                escaped_word_param_keys = []
                word_param_keys = []
                escape_param_key = self.format_param_key('likeescape', LIKE_ESCAPE_CHAR, params=params, from_where=True)
                for onevalue in words_like:
                    word_param_keys.append(self.format_param_key(fieldname, onevalue, params=params, from_where=True))
                    # экранируем %,_ и LIKE_ESCAPE в строке поиска и добавляем wild-символы
                    onevalue = u'%{0}%'.format(re.sub(r'([%_\{0}])'.format(LIKE_ESCAPE_CHAR),
                                                     r'{0}\\1'.format(LIKE_ESCAPE_CHAR), onevalue))
                    escaped_word_param_keys.append(self.format_param_key(
                        fieldname, onevalue, params=params, from_where=True))
                concatfields = ftsconcatfieldsdict.get(fieldname, [fieldname])
                if concatfields:
                    # Составное FTS поле (FTS4 таблица целиком), поскольку мы можем использовать его только
                    # для match, нам надо ручками сделать конструкцию
                    # ((f1 like word1) or (f2 like word1)) and ((f1 like word2) or (f2 like word2))
                    and_list = []
                    for param_key in escaped_word_param_keys:
                        and_list.append('({0})'.format(' OR '.join([
                            '({0}.{1} LIKE {2} ESCAPE {3})'.format(
                                field_qualification, cf, param_key, escape_param_key) for cf in concatfields
                        ])))
                    sql_list.append('({0})'.format(' AND '.join(and_list)))
                if highlight:
                    # используем пользовательскую функцию sqlite_highlight
                    for param_key in word_param_keys:
                        for cf in concatfields:
                            concatfieldname = cf + highlightfieldnamesuffix
                            inner_value = fieldexpr.get(concatfieldname, '{0}.{1}'.format(field_qualification, cf))
                            fieldexpr[concatfieldname] = self.SQLITE_LIKE_HIGHLIGHT_FMT.format(
                                function_name=self.SQLITE_TKS_HIGHLIGHT_FN,
                                value=inner_value,
                                substring=param_key,
                                start_match_text=startsel_param_key,
                                end_match_text=stopsel_param_key)
        res = ' AND '.join(sql_list)
        return res

    def format_where_date(self, key, sign, value):
        if isinstance(value, datetime.datetime):
            return ''
        elif isinstance(value, datetime.date):
            format_str = '%Y-%m-%d'
            v = '%-4.4d-%-2.2d-%-2.2d' % (value.year, value.month, value.day)
            r = "(strftime('%s', %s) %s '%s')" % (format_str, key, sign, v)
            return r
        return super(sqlite_manager, self).format_where_date(key, sign, value)

    def check_guidobjects(self, tblname, tinfo, just_check=False):
        """ Проверка триггеров для генерации GUID в соответствующих полях """
        for ind, field in enumerate(tinfo.fields):
            if field.pdoxtype != ftGUID:
                continue
            l_fieldname = field.fldname.lower()
            trigger_name = self.get_guidtriggername(tblname, l_fieldname, self.TRIGGER_AI)
            triggers = self.get_triggers(tblname)
            if trigger_name not in triggers:
                if just_check:
                    # Проверка не пройдена
                    self.log(u'Таблица %s. Не найден триггер %s. Требуется обновление.' % (tblname, trigger_name))
                return False
        return True

    def create_guidobjects(self, tblname, tinfo):
        """ Создание триггеров для генерации GUID в соответствующих полях """
        r = True
        for ind, field in enumerate(tinfo.fields):
            if field.pdoxtype != ftGUID:
                continue
            r = False
            l_fieldname = field.fldname.lower()
            trigger_name = self.get_guidtriggername(tblname, l_fieldname, self.TRIGGER_AI)
            triggers = self.get_triggers(tblname)
            if trigger_name not in triggers:
                ddl = """CREATE TRIGGER {trigger_name} AFTER INSERT ON {table_name} 
                      FOR EACH ROW WHEN (new.{guid_fieldname} IS NULL) 
                      BEGIN
                        UPDATE {table_name} SET {guid_fieldname} = {guid_expr} WHERE rowid=new.rowid; 
                      END
                      """.format(trigger_name=trigger_name,
                                 table_name=tblname,
                                 guid_fieldname=l_fieldname,
                                 guid_expr=SQLITE_GEN_GUID
                                 )
                self.execute(ddl, None, True)
                r = True
            # Поле только одно
            break
        return r

    def update_ftsobjects(self, tblname, si=None, just_check=False):
        """ Обновление FullTextSearch полей для существующей таблицы.
            Список полей, которые должны быть включены в индекс для полнотекстового поиска, содержится
              в свойстве Indexes соответствующего объекта TCdsTable с префиксом /t. Пример описания для
              таблицы articles:
                /tG31_1_FTS=G312C,G312OUTSIDE,GROUP_NAME,G31_11,G31_12,G31_14,G31_15,G31_15_MOD,G31_16,G31_17,G31_18,
                G31_19,G31_20;G312C;G312OUTSIDE;GROUP_NAME;G31_11;G31_12;G31_14;G31_15;G31_15_MOD;G31_16;G31_17
                ;G31_18;G31_19;G31_20
            Конструкция G31_1_FTS=G312C,G312OUTSIDE,... используется для организации поиска по всем полям, путем
             поддержания содержимого объединенного поля (G31_1_FTS) равного конкатенации значений всех полей из
             списка (G312C,G312OUTSIDE,...). В pg это реализовано с помощью триггера. В sqlite при создании виртуальной
             таблицы FTS поиск по всем полям реализуется "бесплатно" (поиском по всей таблице) и
             необходимость автоматического поддержания содержимого этого поля с помощью триггера отпадает.
             Если список полей, образующих составное поле (G31_1_FTS) совпадает со списком полей, по которым требуется
             организовать FTS поиск (как в данном примере), то в sqlite будет создана одна виртуальная таблица.
             Имя виртуальной таблицы: <имя таблицы>_<имя составного поля>_fts4 или, если составное поле отсутствует, то
             <имя таблицы>_<имя первого поля из списка полей>_fts4
            В sqlite для полнотекстового поиска будем использовать "External Content FTSN Tables":
                CREATE VIRTUAL TABLE  <fts_table_name> USING FTSN(content='<table_name>', tokenize=icu,
                <field_name_1>,...,<field_name_n>))
            После создания виртуальной таблицы необходимо перестроить индекс:
                INSERT INTO <fts_table_name>(<fts_table_name>) VALUES('rebuild')
            just_check - просто проверить наличие необходимых индексов
        """
        si = si or get_struct_info()
        # индексы из структуры
        siindexes = {self.get_ftsindex_name(tblname, mainfield): fieldlist
                     for mainfield, fieldlist in self.get_ftsindexes_from_struct_info(si, tblname).items()}
        # получить существующие в базе индексы
        dbindexes = self.get_table_ftsindexes(tblname)
        # теперь определим, какие индексы надо создать, а какие - удалить
        indexes_to_add = {indexname: indexfields for indexname, indexfields in siindexes.items()
                          if indexname not in dbindexes.keys() or   # если такого индекса нет совсем
                          (indexname in dbindexes.keys() and indexfields != dbindexes[indexname])}  # если список полей не совпадает
        indexes_to_delete = [indexname for indexname, indexfields in dbindexes.items()  # просто список имен индексов
                             if indexname not in siindexes.keys() or
                             (indexname in siindexes.keys() and indexfields != siindexes[indexname])]
        # сначала надо удалить, поскольку имена создаваемых индексов могут совпадать с удаляемыми (отличается список полей)
        if indexes_to_delete:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица {0}. Найдены неиспользуемые FTS таблицы {1}. Требуется обновление.'.\
                    format(tblname, ', '.join(indexes_to_delete))
                self.errors.append(error)
                self.log(error)
                return False
            self.delete_ftsindexes(tblname, indexes_to_delete)
        if indexes_to_add:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица {0}. Не найдены FTS таблицы {1}. Требуется обновление.'.\
                    format(tblname, ', '.join(indexes_to_add))
                self.errors.append(error)
                self.log(error)
                return False
            self.add_ftsindexes(tblname, indexes_to_add)
        # а теперь проверим триггера
        sitriggers = self.get_ftstriggers_from_ftsindexes(tblname, siindexes, self.fts)
        dbtriggers = self.get_table_ftstriggers(tblname)
        triggers_to_add = {
            (indexname, trigger_type): (field_list, trigger_name)
            for (indexname, trigger_type), (field_list, trigger_name) in sitriggers.items()
                if
                    (indexname, trigger_type) not in dbtriggers or
                    dbtriggers[(indexname, trigger_type)] != (field_list, trigger_name)
        }
        triggers_to_delete = [
            trigger_name
            for (indexname, trigger_type), (fieldlist, trigger_name) in dbtriggers.items()
                if (indexname, trigger_type) not in sitriggers or
                   sitriggers[(indexname, trigger_type)] != (fieldlist, trigger_name)
        ]
        # удаление лишних триггеров
        if triggers_to_delete:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица {0}. Найдены неиспользуемые FTS триггеры ({1}). Требуется обновление.'.format(
                    tblname, ', '.join(trigger[0] for trigger in triggers_to_delete))
                self.errors.append(error)
                self.log(error)
                return False
            self.delete_ftstriggers(tblname, triggers_to_delete)
        # добавление необходимых триггеров
        if triggers_to_add:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица {0}. Не найдены FTS триггеры ({1}). Требуется обновление.'.format(
                    tblname, ', '.join([trigger_name for (_, trigger_name) in triggers_to_add.values()]))
                self.errors.append(error)
                self.log(error)
                return False
            self.add_ftstriggers(tblname, triggers_to_add)
        if (indexes_to_add or indexes_to_delete or triggers_to_add or triggers_to_delete) and (not just_check):
            self.conn.commit()
        return True

    def get_ftsindex_name(self, tblname, fldname):
        """
            Имя виртуальной таблицы:
            <имя таблицы>_<имя составного поля>_ftsN или, если составное поле отсутствует, то
            <имя таблицы>_<имя первого поля из списка полей>_ftsN
        """
        return '{0}_{1}_{2}'.format(tblname, fldname, self.fts).lower()

    def get_ftsindexinfo_by_fieldname(self, tblname, fldname):
        """
        :param tblname: Имя основной таблицы
        :param fldname: Имя поля, по которому осуществляется поиск
        :return: кортеж (имя таблицы FTS, имя составного поля или первого поля, список полей),
        в которой содержится индекс для поля fldname или (None, None, None), если для поля нет FTS индекса
        """
        siindexes = self.get_ftsindexes_from_struct_info(None, tblname)
        if siindexes:
            for mainfield, fieldlist in siindexes.items():
                if (fldname == mainfield) or (fldname  #.lower()
                                              in fieldlist):
                    return self.get_ftsindex_name(tblname, mainfield), mainfield, fieldlist
        return None, None, None

    def get_ftsindexes_from_struct_info(self, si, tblname):
        """
        # построить словарь требуемых индексов:
        :param si: структура БД
        :param tblname: имя таблицы
        :return: словарь {<fts_index_main_field>: <field_list>} имя "главного" поля индекса -> список полей индекса
           имя индекса можно получить из имени "главного" поля индекса методом get_ftsindex_name
        """
        si = si or get_struct_info()
        tbl = si.tables.get(tblname.lower(), None)
        if tbl:
            fields = tbl.fields
            # 1. Список индексов для составных полей
            siindexes = {field.fldname: [fn  #.lower()
                                         for fn in field.ftsconcatfields]
                         for field in fields if field.fts and field.ftsconcatfields}
            # 2. Оставшиеся поля, не вошедшие в составные поля
            restftsfields = []
            for field in fields:
                if field.fts and not field.ftsconcatfields:
                    fn = field.fldname  #.lower()
                    for concatfields in siindexes.values():
                        if fn in concatfields:
                            break
                    else:
                        restftsfields.append(fn)
            if restftsfields:
                siindexes[restftsfields[0]] = restftsfields
            return siindexes
        else:
            return None

    def add_ftsindexes(self, tblname, siindexes):
        """
        Добавление fts-индексов. siindexes - словарь <fts_table_name>: <fields_list>
        Индекс имеет вид
                CREATE VIRTUAL TABLE  <fts_table_name> USING FTS4(content='<table_name>', tokenize=icu,
                <field_name_1>,...,<field_name_n>))
        """
        r = False
        for indexname, fieldslist in siindexes.items():
            self.execute(self.SQLITE_CREATE_FTS_FMT[self.fts].format(fts_table_name=indexname,
                                                                     table_name=tblname,
                                                                     field_list=', '.join(fieldslist)),
                         None, True)
            self.execute(self.SQLITE_REBUILD_FTS_FMT[self.fts].format(fts_table_name=indexname), None, True)
            r = True
        return r

    def delete_ftsindexes(self, tblname, indexes):
        """ удаление ftsN-индексов. indexes - список имен индексов, подлежащих удалению """
        r = False
        for indexname in indexes:
            self.execute('DROP TABLE IF EXISTS {0}'.format(indexname), None, True)
            r = True
        return r

    def drop_ftsobjects_all(self, tblname):
        """
        Удалить все FTS объекты таблицы.
        Это могут быть индексы, триггера, функции и т.д.
        """
        # получить имена существующих в базе FTS индексов, относящихся к заданной таблице
        indexes_to_delete = self.get_table_ftsindexes(tblname).keys()
        if indexes_to_delete:
            self.delete_ftsindexes(tblname, indexes_to_delete)
        # а теперь удалим триггера
        triggers_to_delete = [trigger_name for (fieldlist, trigger_name) in
                              self.get_table_ftstriggers(tblname).values()]
        if triggers_to_delete:
            self.delete_ftstriggers(tblname, triggers_to_delete)
        return True

    def create_ftsobjects_all(self, tblname):
        """ Создать все FTS объекты таблицы """
        return self.update_ftsobjects(tblname)

    def get_table_ftsindexes(self, tblname):
        """
            Возвращает словарь <index_name>: <fields_list> для всех FTS таблиц, существующих для таблицы tblname.
        """
        r = {}
        # получим все виртуальные таблицы с описанием
        key = {self.SQLITE_MASTER_TYPE: self.SQLITE_MASTER_TYPE_TABLE, self.SQLITE_MASTER_ROOTPAGE: 0}
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_NAME, self.SQLITE_MASTER_SQL), key)
        if d:
            for rec in d:
                vtmatch = self.SQLITE_CREATE_FTS_CRE.match(rec[self.SQLITE_MASTER_SQL])
                if vtmatch:
                    if vtmatch.group('table_name').lower() == tblname.lower():
                        # FTS индекс для нашей таблицы, получим список полей
                        flist = [f.strip() for f in vtmatch.group('field_list').split(',')]
                        r[vtmatch.group('index_name').lower()] = flist
        return r

    def get_triggers(self, tblname):
        r = []
        # получим все триггеры с DDL
        key = {self.SQLITE_MASTER_TYPE: self.SQLITE_MASTER_TYPE_TRIGGER,
               self.SQLITE_MASTER_TBL_NAME: tblname.lower()}
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_NAME, self.SQLITE_MASTER_SQL), key)
        if d:
            for rec in d:
                r.append(rec[self.SQLITE_MASTER_NAME])
        return r

    def drop_triggers_all(self, tblname):
        triggers = self.get_triggers(tblname)
        for trigger in triggers:
            self.delete_trigger(tblname, trigger)
        return True

    def get_table_ftstriggers(self, tblname):
        """
            Возвращает словарь (<fts_index_name>, <trigger_type>): (<field_list>, <trigger_name>)
            Для каждого FTS индекса у основной таблицы создаются триггеры для синхронизации индекса с изменениями
            основной таблицы. Описание триггеров смотри в add_ftstriggers.
            <trigger_type> - пара ([BEFORE|AFTER], [DELETE|UPDATE|INSERT])
        """
        r = {}
        # получим все триггеры с DDL
        key = {self.SQLITE_MASTER_TYPE: self.SQLITE_MASTER_TYPE_TRIGGER,
               self.SQLITE_MASTER_TBL_NAME: tblname.lower()}
        d = self.select(self.SQLITE_MASTER_TABLE, (self.SQLITE_MASTER_NAME, self.SQLITE_MASTER_SQL), key)
        if d:
            for rec in d:
                ddl = rec[self.SQLITE_MASTER_SQL].upper()
                for fts in [self.SQLITE_FTS_FTS4, self.SQLITE_FTS_FTS5]:
                    for template in self.SQLITE_TRIGGER_FTS_CRE[fts]:
                        trmatch = template.match(ddl)
                        if trmatch:
                            r[(
                                trmatch.group('fts_table_name').lower(),
                                (trmatch.group('trigger_ba'), trmatch.group('trigger_crud'))
                            )] = (
                                [f.strip() for f in trmatch.group('field_list').split(',')]
                                    if 'field_list' in trmatch.re.groupindex else [],
                                trmatch.group('trigger_name').lower())
                            break
                    else:
                        continue
                    break
        return r

    def add_ftstriggers(self, tblname, sitriggers):
        """
         Добавление ftsN-триггеров.
            sitriggers - словарь (<fts_table_name>, <trigger_type>): (<fields_list>, <trigger_name>).
         Для каждого fts4 индекса создаются следующие триггеры:
            1.
            CREATE TRIGGER <fts_table_name>_bd BEFORE DELETE ON <table_name> FOR EACH ROW
            BEGIN
                DELETE FROM <fts_table_name> WHERE docid = old.rowid;
            END
            2.
            CREATE TRIGGER <fts_table_name>_bu BEFORE UPDATE [OF <fields_list>] ON <table_name> FOR EACH ROW
            [WHEN new.<field1> != old.<field1> AND ... AND new.<fieldN> != old.<fieldN>]
            BEGIN
                DELETE FROM <fts_table_name> WHERE docid=old.rowid;
            END;
            3.
            CREATE TRIGGER <fts_table_name>_au AFTER UPDATE [OF <fields_list>] ON <table_name> FOR EACH ROW
            [WHEN new.<field1> != old.<field1> AND ... AND new.<fieldN> != old.<fieldN>]
            BEGIN
                INSERT INTO <fts_table_name>(docid, <field1>, ..., <fieldN>)
                    VALUES(new.rowid, new.<field1>, ..., new.<fieldN>);
            END;
            4.
            CREATE TRIGGER <fts_table_name>_ai AFTER INSERT ON <table_name> FOR EACH ROW
            BEGIN
                INSERT INTO <fts_table_name>(docid, <field1>, ..., <fieldN>)
                    VALUES(new.rowid, new.<field1>, ..., new.<fieldN>);
            END;

         Для каждого fts5 индекса создаются следующие триггеры:
            1.
            CREATE TRIGGER <fts_table_name>_fts5_bd BEFORE DELETE ON <table_name> FOR EACH ROW
            BEGIN
                -- Remove the same row from the fts5 table.
                INSERT INTO <fts_table_name>(<fts_table_name>, rowid, <field1>, <field2>,..., <fieldN>)
                    VALUES('delete', old.rowid, old.<field1>, old.<field2>,..., old.<fieldN>);
            END
            2.
            CREATE TRIGGER <fts_table_name>_fts5_bu BEFORE UPDATE [OF <fields_list>] ON <table_name> FOR EACH ROW
            [WHEN new.<field1> != old.<field1> AND ... AND new.<fieldN> != old.<fieldN>]
            BEGIN
                INSERT INTO <fts_table_name>(<fts_table_name>, rowid, <field1>, <field2>,..., <fieldN> )
                    VALUES('delete', old.rowid, old.<field1>, old.<field2>,..., old.<fieldN>);
            END;
            3.
            CREATE TRIGGER <fts_table_name>_fts5_au AFTER UPDATE [OF <fields_list>] ON <table_name> FOR EACH ROW
            [WHEN new.<field1> != old.<field1> AND ... AND new.<fieldN> != old.<fieldN>]
            BEGIN
                INSERT INTO <fts_table_name>(rowid, <field1>, ..., <fieldN>)
                    VALUES(new.rowid, new.<field1>, ..., new.<fieldN>);
            END;
            4.
            CREATE TRIGGER <fts_table_name>_fts5_ai AFTER INSERT ON <table_name> FOR EACH ROW
            BEGIN
                INSERT INTO <fts_table_name>(rowid, <field1>, ..., <fieldN>)
                    VALUES(new.rowid, new.<field1>, ..., new.<fieldN>);
            END;


         Перед добавлением удалим триггер с именем <trigger_name>
        """
        for (ftsindexname, trigger_type), (fieldlist, trigger_name) in sitriggers.items():
            # Удалим триггер с этим именем
            self.delete_trigger(tblname, trigger_name)
            # создадим триггер
            ddl = self.SQLITE_TRIGGER_FTS_FMT[self.fts][trigger_type].format(
                    table_name=tblname,
                    trigger_name=trigger_name,
                    fts_table_name=ftsindexname,
                    field_list=', '.join(fieldlist),
                    new_field_list=', '.join(['NEW.{0}'.format(fn) for fn in fieldlist]),
                    old_field_list = ', '.join(['OLD.{0}'.format(fn) for fn in fieldlist])
            )
            self.execute(ddl, None, True)

    def get_ftstriggers_from_ftsindexes(self, tblname, siindexes, fts):
        return {
            (indexname, trigger_type):
                ([] if (trigger_type in [self.TRIGGER_TYPE_BD]) and (fts == self.SQLITE_FTS_FTS4) else fieldlist,
                 self.get_ftstriggername(tblname, indexname, trigger_name_suffix))
                for trigger_type, trigger_name_suffix in self.SQLITE_FTS_TRIGGER_TYPE_2_NAME_SUFFIX[fts].items()
                for indexname, fieldlist in siindexes.items()
        }

    def get_ftstriggername(self, tblname, ftsindexname, suffix):
        return "{0}{1}".format(ftsindexname, suffix)

    def get_guidtriggername(self, tblname, ftsindexname, suffix):
        return "{0}_{1}{2}".format(tblname, ftsindexname, suffix)

    def delete_ftstriggers(self, tblname, triggers):
        """ удаление fts-индексов. triggers - список имен триггеров, подлежащих удалению """
        for trigger_name in triggers:
            self.delete_trigger(tblname, trigger_name)

    def delete_trigger(self, tblname, trigger_name):
        self.execute("DROP TRIGGER IF EXISTS {trigger_name}".format(trigger_name=trigger_name), None, True)


class sqlite_query(object):
    """ используется для queryrecords """
    def __init__(self, cursor, enable_cache=True):
        self.cursor = cursor
        self.SQL = []
        self.params = None
        self.active = False
        self.rcount = -1
        #кэш данных, вместо отсутствующего self.cursor.scroll()
        self.cache = {}
        self.cache_data = None
        self.cache_idx = -1
        self.enable_cache=enable_cache

    def ExecSQL(self):
        if self.params:
            self.cursor.execute(''.join(self.SQL), self.params)
        else:
            self.cursor.execute(''.join(self.SQL))

    def Open(self):
        self.ExecSQL()
        self.active = True

    def Close(self):
        if self.active:
            self.cursor.close()
            self.active = False

    def commit(self):
        pass

    def set_cache_data(self, data):
        if data is not None:
            self.cache_idx += 1
            if self.enable_cache:
                self.cache[self.cache_idx] = data
            else:
                self.cache_data = data
        return data

    def fetch(self, idx):
        if self.enable_cache:
            if idx > self.cache_idx:
                for each in xrange(idx - self.cache_idx):
                    if self.set_cache_data(self.cursor.fetchone()) is None:
                        break
            return self.cache.get(idx)
        else:
            if idx == self.cache_idx:
                return self.cache_data
            else:
                return self.set_cache_data(self.cursor.fetchone())


class sqlite_records(QueryRecords):

    def close_query(self):
        if self.query is not None:
            try:
                try:
                    self.query.Close()
                except Exception, e:
                    self.dm.conn.rollback()
                    show_error(e, 'close_query error')
            finally:
                self.query = None

    def __len__(self):
        # Есть случаи, когда self.query.cursor.rowcount == -1
        # The rowcount attribute is -1 in case no executeXX() has been performed on the cursor
        # or the rowcount of the last operation is not determinable by the interface.
        # This includes SELECT statements because we cannot determine the number of rows a query produced until all rows were fetched.
        # That means all SELECT statements won't have a rowcount.
        if self.query.rcount == -1:
            if self.query.cursor.rowcount > 0:
                return self.query.cursor.rowcount
        else:
            return self.query.rcount
        return 0

    def __iter__(self):
        self.qty = 0
        self.rec_n = self.start
        return self

    def next(self):
        if self.limit > 0 and self.qty == self.limit:
            raise StopIteration
        else:
            record = self.query.fetch(self.rec_n)
            if not record:
                raise StopIteration
            self.qty += 1
            return self.get_record(record)

    def get_record(self, record):
        try:
            r = self.dm.get_rec_factory()()
            for key in record.keys():
                ukey = key.upper()
                if self.fields and ukey in self.fields:
                    ukey = self.fields[ukey]
                r[str(ukey)] = self.dm.adapt(ukey, record[key])
            self.merge_modified(r)
            self.do_calc_record(r)
            self.rec_n += 1
            return r
        except EXMLCompressException, e:
            self.log_whereami(e)
        except Exception:
            raise


class fts3_sqlite_manager(sqlite_manager):

    """
    использование модуля расширений FTS3
    """

    def get_create_ddl(self, table_info, last_delim=True, typeconvert=None, keywords=()):
        """
            Формирование ddl для создания таблицы.
            перенесено из dbstruct для возможности генерации в зависимости от типа базы данных
        """
        ld = last_delim and ';' or ''
        pkey = self.get_primary_key(table_info)
        if pkey:
            pkey = ', {}'.format(pkey)
        else:
            pkey = ''
        return 'CREATE VIRTUAL TABLE %s USING FTS3(tokenize=icu,%s%s)%s' % (
            table_info.tblname,
            self.get_ddl_field_list(table_info, typeconvert, keywords),
            pkey, ld)

class memory_sqlite_manager(sqlite_manager):
    """ менеджер использует """
    def get_connection_string(self, just_test=False):
        return ':memory:'

    def check_database(self):
        return True


def get_test_structinfo():
    si = struct_info()
    tbl = si.addtable('XMLBASE', 'Глобальная база документов в формате XML')
    tbl.addfield('DOCID', domains.T_GUID, True, 'Уникальный идентификатор документа')
    tbl.addfield('DOCNUMBER', domains.varchar(50), dispname = 'Номер документа')
    tbl.addfield('DOCDATE', domains.T_DATETIME, dispname = 'Дата документа')
    tbl.addfield('XML', domains.T_TEXT, dispname = 'Текст документа в сжатом виде')
    return si


class DictStructInfo(custom_struct_info):
    def init_properties(self):
        self.tables = {}


class DictDataManager(memory_sqlite_manager):
    def beforeInit(self, name, data, *args, **kwargs):
        super(DictDataManager, self).beforeInit(*args, **kwargs)
        self.si = DictStructInfo()
        self.data = data
        self.columns_config = {}
        self.name = 'ddm_{}'.format(name.lower())
        self.dispname = ''
        self.keys = set()

    def afterInit(self, *args, **kwargs):
        super(DictDataManager, self).afterInit(*args, **kwargs)
        if self.create_table():
            self.create_database(self.si)
            self.insert_data()

    def create_table(self):
        if not self.data:
            return False

        tbl = self.si.addtable(self.name, self.dispname)
        for k in self.data[0]:
            cfg = self.columns_config.get(k, {})
            required = bool(cfg.get('required'))
            dispname = cfg.get('title', k)
            tbl.addfield(k, cfg.get('domain', domains.get_domain_by_type(self.data[0][k])), required=required, dispname=dispname)

        return True

    def insert_data(self):
        for row in self.data:
            self.insert(self.name, row)

    @property
    def fields(self):
        if not self.data:
            return []
        return self.si.tables[self.name].fields

    def recfields(self):
        r = []
        for field in self.fields:
            r.append('{tbl}."{field}"'.format(tbl=self.name.lower(), field=str(field.fldname.lower())))
        return r

    def required(self):
        return map(lambda f: f.fldname.lower(), (f for f in self.fields if f.required))


def test_memory_manager():
    dm = memory_sqlite_manager()
    print "dm.connection_ok()", dm.connection_ok()
    si = get_test_structinfo()
    dm.create_database(si)
    print "dm.get_table_list()", dm.get_tables()
    print "dm.get_table_info('XMLBASE')"
    d = dm.get_table_info('xmlbase')
    for key in d.keys():
        print key, d[key]

    from gtd import system
    import time

    def create_guid(): return system.create_guid()[1:-1]

    guid = create_guid()
    print "dm.insert('xmlbase', {'DOCID' : create_guid()})"\
        , dm.insert('xmlbase', {'DOCID' : guid,
                                'DOCNUMBER' : '111111',
                                'DOCDATE' : time.localtime(),
                                'XML' : 'Привет Привет Привет'})
    print "dm.locate('xmlbase')", dm.locate('xmlbase')
    d = dm.select('xmlbase', ('*', ), {'DOCID' : guid})
    if d:
        for rec in d:
            for key in rec:
                print key, rec[key]


def test_update_database():
    from data import get_sqlite_config
    dm = sqlite_manager(get_sqlite_config('d:\\test.sqlite'))
    dm.create_database(get_test_structinfo())


def test_cursor_execute():
    from data import get_sqlite_config
    dm = sqlite_manager(get_sqlite_config('d:\\other.db3'))
    print dm.execute('select count(*) as C from kontdop', ()).fetchone()
    print dm.get_tables()
    print dm.get_table_columns('kontdop')

def test_create_table():
    si = get_test_structinfo()
    ti = si.tables['xmlbase']
    from data import get_sqlite_config
    dm = sqlite_manager(get_sqlite_config('d:\\test.sqlite'))
    print ti.get_create_ddl(typeconvert=dm.typeconvert)

def test_date():
    from data import get_sqlite_config
    dm = sqlite_manager(get_sqlite_config('d:\\decl.archive\\test.tksx'))
    d = dm.select('xmlbase2', ('*', ))
    if d:
        print "OK"
    else:
        print "ERROR"

def test_contract():
    from data import get_sqlite_config
    dm = sqlite_manager(get_sqlite_config('d:\\other.db3'))
    d = dm.select_records('kontrakt', ('*', ))
    if d:
        print "OK"
        print len(d)
        print d
        print d[0:1]
        print d[1:2]
        print d[0:1]
    else:
        print "ERROR"

def test_date():
    from data import get_sqlite_config
    dm = sqlite_manager(get_sqlite_config('d:\\data.db3'))
    d = dm.select('decl_pp', ('DATPDOK', ), {'ND': '10221010/15016/0100625'})
    if d:
        print d
    else:
        print "ERROR"



if __name__ == "__main__":

    #test_memory_manager()
    #test_cursor_execute()
    test_date()
