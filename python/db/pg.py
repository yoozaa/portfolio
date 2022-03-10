# -*- coding: cp1251 -*-

"""

   модуль доступа к данным PostGreSQL


   TODO:
   1. Создавать базу данных
   2. Обновление структур и данных
   3. Сделать форматирование where через параметры


   conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
   set_client_encoding(enc)

"""

import atexit
import os
import time
import datetime
import psycopg2
import psycopg2.extensions
import psycopg2.extras
from collections import OrderedDict


#psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
#psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

def adapt_struct_time(t):
    return psycopg2.extensions.AsIs("'%d-%.2d-%.2dT%.2d:%.2d:%.2d'" % tuple(t[:6]))

psycopg2.extensions.register_adapter(time.struct_time, adapt_struct_time)


# регистрируем адаптер для используемого нами cdecimal
try:
    from cdecimal import Decimal
except ImportError:
    pass
else:
    try:
        from _psycopg import Decimal as Adapter
    except ImportError:
        # в linux _psycopg.so находится внутри каталога psycopg2
        from psycopg2._psycopg import Decimal as Adapter
    psycopg2.extensions.register_adapter(Decimal, Adapter)
    del Decimal, Adapter

from gtd.db.manager import *
from gtd import show_error, events, create_guid, confirm
from tks import objects
from gtd.db import get_struct_info
from gtd.db.dbconsts import *
from gtd.eventtypes import EVENT_STOPSERVER, EVENT_STOPPROCESSING
from tks.strutils import format_error, to_ustr

CREATE_DATABASE_DDL = "CREATE DATABASE %s WITH OWNER = \"%s\"  TEMPLATE=template0 ENCODING = '%s' TABLESPACE = pg_default LC_COLLATE = 'Russian, Russia' LC_CTYPE = 'Russian, Russia' CONNECTION LIMIT = -1"

# коды ошибок PG (поле pgcode)
PGCODE_UNIQUE_VIOLATION = '23505'
PGCODE_EXTENSION_ALREADY_EXISTS = '42710'

# имя конфигурации FTS
PGFTS_REGCONFIG = "'simple'::regconfig"
# типы индексов, используемых FTS
PGFTS_INDEX_FTS = 'fts'
PGFTS_INDEX_TRGM = 'trgm'
# extension name
PG_EXTENSION_TRGM = 'pg_trgm'
# opclass name
PG_OPCLASS_GIN_TRGM = 'gin_trgm_ops'
# Версия PG, начиная с которой можно проверять extension
PG_VERSION_EXTENSION_START = 90100

# Возможность модификации структур в функциях
# NEW := NEW #= '"some_key"=>"5"'::hstore;
PG_EXTENSION_HSTORE = 'hstore'

# генерация GUID в тригерах
PG_EXTENSION_UUID = 'uuid-ossp'


try:
    import database
    from DB import *
    from gtd.db import domains
except ImportError:
    pass


class PGBinaryField(BinaryField):

    def get_value(self, value):
        if value:
            return str(value)
        return ''


class pq_query(object):
    """ аналог TQuery. Наверное лучше не использовать """
    def __init__(self, cursor):
        self.cursor = cursor
        self.SQL = []
        self.params = None

    def ExecSQL(self):
        self.cursor.execute(''.join(self.SQL), self.params)

    def Open(self):
        self.ExecSQL()

    def Close(self):
        if not self.cursor.closed:
            self.cursor.close()

    def Locate(self, where):
        pass


SYSTEM_DB_NAME = 'postgres'  # имя базы, которая всегда есть
DEFAULT_DB_NAME = 'decl'
DEFAULT_USERNAME = 'postgres'
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = '5432'
DEFAULT_DB_ENCODING = 'WIN1251'
DEFAULT_ENCODING = 'WIN1251'
DEFAULT_SCHEMA = 'public'


class PgConnectionFactory(object):
    """ PgConnectionFactory """

    __shared_data = {}

    def __init__(self):
        self.__dict__ = PgConnectionFactory.__shared_data
        if 'init' not in self.__dict__:
            self.init = True
            self.init_properties()

    def init_properties(self):
        self.connections = {}
        events.subscribe_event(EVENT_STOPSERVER, self.close_connections)
        events.subscribe_event(EVENT_STOPPROCESSING, self.close_connections)
        atexit.register(self.atexit_close_connections)

    def get_connection(self, cfg, keyword_list=(), *args, **kwargs):
        conn = PgConnection(cfg, KEYWORD_LIST=keyword_list, *args, **kwargs)
        connkey = conn.get_connection_key()
        if connkey in self.connections:
            del conn
            conn = self.connections[connkey]
        else:
            self.connections[connkey] = conn
        conn.use()
        return conn

    def put_connection(self, conn):
        conn.unuse()
        if conn.usecount == 0:
            for k, v in self.connections.iteritems():
                if v is conn:
                    del self.connections[k]
                    break

    def close_connections(self, event_name = '', event_data = '', *args, **kwargs):
        for connkey, conn in self.connections.iteritems():
            conn.disconnect()
        return True

    def atexit_close_connections(self, *args, **kwargs):
        self.close_connections()


class PgConnection(objects.baseobject):

    ccount = 0
    TRIGGER_AI = '_ai'

    def beforeInit(self, cfg, *args, **kwargs):
        self.log_init()
        self.cfg = cfg
        self.dbname = self.cfg.get(PARAM_PG_SERVERDBNAME, DEFAULT_DB_NAME)
        self.username = self.cfg.get(PARAM_PG_USERNAME, DEFAULT_USERNAME)
        self.host = self.cfg.get(PARAM_PG_SERVERNAME, DEFAULT_HOST)
        self.port = self.cfg.get(PARAM_PG_SERVERPORT, DEFAULT_PORT)
        self.password = self.cfg.get(PARAM_PG_USERPASS, '')
        self.encoding = DEFAULT_ENCODING
        self.dbencoding = self.cfg.get(PARAM_PG_ENCODNIG, DEFAULT_DB_ENCODING)
        self.schema = self.cfg.get(PARAM_PG_SCHEMA, DEFAULT_SCHEMA)
        self.app_name = self.get_app_name()
        self.isolation_level = None
        self.conn = None
        self.errors = []
        self.usecount = 0
        self.KEYWORD_LIST = ()
        self.allow_lowercase = True

    def afterInit(self, *args, **kwargs):
        super(PgConnection, self).afterInit(*args, **kwargs)
        if self.allow_lowercase:
            if self.dbname:
                self.dbname = self.dbname.lower()

    def clear_errors(self):
        self.errors = []

    def get_app_name(self):
        return '/'.join((
            os.path.basename(os.environ.get('TKSAPPINFO_EXENAME', '')),
            os.environ.get('TKSAPPINFO_VERSION', ''),
            os.environ.get('TKSAPPINFO_COMPCODE', '').replace(' ', ''),
            os.environ.get('TKSAPPINFO_COMPID', ''),
        ))

    def auto_create_database(self):
        if not self.check_database():
            if confirm(u'База данных %s не существует. Создать базу данных' % (self.dbname)):
                self.create_database()
            else:
                raise EAutoCreateCancel()

    def connect(self, just_test=False, setdbname=True, setschema=True, reraise=False, auto_create=False):
        if not self.conn:
            try:
                if auto_create:
                    self.auto_create_database()
                self.conn = psycopg2.connect(self.get_connection_string(setdbname),
                                             connection_factory=psycopg2.extras.DictConnection)
                self.conn.set_client_encoding(self.encoding)
                if setdbname and setschema:
                    if self.isolation_level is None:
                        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                        self.isolation_level = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
                    else:
                        self.conn.set_isolation_level(self.isolation_level)
                    if setschema:
                        self.set_search_path()
                else:
                    # подключение к БД по умолчанию (postgres), например, для создания своей БД.
                    # CREATE DATABASE не может выполняться внутри транзакции.
                    self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                self.encoding = self.conn.encoding
                PgConnection.ccount += 1
                return ''
            except EAutoCreateCancel:
                raise
            except Exception, e: #OperationalError
                self.conn = None
                error_message = format_error(e)
                self.log_whereami('pg', error_message)
                if not just_test:
                    show_error(e, 'pg connect')
                if reraise:
                    raise
                else:
                    return error_message
        else:
            return ''

    def __del__(self):
        self.disconnect()

    def use(self):
        self.usecount += 1

    def unuse(self):
        self.usecount -= 1

    def set_search_path(self):
        if self.schema != DEFAULT_SCHEMA:
            self.execute('SET search_path TO %s, %s' % (self.schema, DEFAULT_SCHEMA), None, close_cursor=True, without_check=True)

    def get_connection_string(self, setdbname=True):
        d = self.get_connection_dict(setdbname)
        return " ".join(["%s=%s" % (key, d[key]) for key in d.keys()])

    def get_connection_key(self):
        d = self.get_connection_dict(True)
        d['schema'] = self.schema
        d['encoding'] = self.encoding
        d['isolation_level'] = self.isolation_level
        return " ".join(["%s=%s" % (key, d[key]) for key in sorted(d.keys())])

    def get_connection_dict(self, setdbname=True):
        d = {}
        d['application_name'] = self.app_name
        if setdbname and self.dbname:
            d['dbname'] = self.dbname
        else:
            d['dbname'] = SYSTEM_DB_NAME
        if self.password:
            d['password'] = self.password
        if self.host:
            d['host'] = self.host
        if self.port:
            d['port'] = self.port
        if self.username:
            d['user'] = self.username
        return d

    def disconnect(self):
        if self.conn:
            self.conn.close()
            PgConnection.ccount -= 1
            self.conn = None

    def check(self):
        """ Проверяет соединение на живучесть. Если надо - переконнектится """
        if not self.conn:
            return not self.connect(True)
        else:
            try:
                cur = self.conn.cursor()
                cur.execute('select 1')
                cur.close()
                return True
            except:
                self.conn = None
                return not self.connect(True)

    def cursor(self, without_check=False, *args, **kwargs):
        if without_check or self.check():
            return self.conn.cursor(*args, **kwargs)
        else:
            return None

    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def get_database_ddl(self):
        return CREATE_DATABASE_DDL % (self.dbname.lower(), self.username, self.dbencoding)

    def create_database(self, check_exists=False):
        self.disconnect()
        self.connect(just_test=True, setdbname=False, reraise=True)
        try:
            if check_exists and (self.dbname.lower() in self.get_database_list()):
                return
            self.execute(self.get_database_ddl(), None, close_cursor=True, without_check=True)
        finally:
            self.disconnect()

    def create_schema(self):
        self.disconnect()
        self.connect(just_test=True, setdbname=True, setschema=False, reraise=True)
        self.execute('CREATE SCHEMA %s' % (self.schema.lower()), None, close_cursor=True, without_check=True)
        self.disconnect()

    def check_schema(self):
        """ Проверяет есть ли нужная нам схема БД.
        Если нет - вернет False.
        """
        self.disconnect()
        self.connect(just_test=True, setdbname=True, setschema=False, reraise=True)
        r = self.schema.lower() in self.get_schema_list()
        self.disconnect()
        return r

    def check_database(self):
        self.disconnect()
        self.connect(just_test=True, setdbname=False, reraise=True)
        r = self.dbname.lower() in self.get_database_list()
        self.disconnect()
        return r

    def check_all(self):
        """
            Проверяет подключение , наличие базы данных и схема
        """
        r = ''
        self.disconnect()
        r = self.connect(just_test=True, setdbname=False, reraise=True)
        if r:
            return r
        if self.dbname.lower() not in self.get_database_list():
            return u"Отсутствует база данных %s" % (self.dbname)
        if self.schema.lower() not in self.get_schema_list():
            return u"Отсутствует схема базы данных %s" % (self.schema)
        self.disconnect()
        return r

    def get_database_list(self):
        r = []
        cur = self.execute('SELECT datname FROM pg_database', None, without_check=True)
        try:
            for rec in cur:
                r.append(rec[0])
        finally:
            cur.close()
        return r

    def check_database_encoding(self):
        cur = self.execute('SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = %(dbname)s',
                           {'dbname': self.dbname.lower()})
        if cur:
            rec = cur.fetchone()
            if rec and rec[0] == self.dbencoding:
                cur.close()
                return True
        return False

    def get_schema_list(self):
        r = []
        cur = self.execute('SELECT nspname FROM pg_namespace', None)
        try:
            for rec in cur:
                r.append(rec[0])
        finally:
            cur.close()
        return r

    def execute(self, sql, params, close_cursor=False, without_check=False):
        """ возвращает cursor с записями в виде массивов, если надо """
        cur = self.cursor(without_check)
        cur.execute(sql, params)
        if close_cursor:
            cur.close()
            cur = None
        return cur

    def get_table_list(self, tblname=''):
        r = []
        params = {}
        params['schemaname'] = self.schema
        sql = 'SELECT tablename FROM pg_tables WHERE (schemaname = %(schemaname)s)'
        if tblname:
            params['tablename'] = tblname.lower()
            sql += ' AND (tablename = %(tablename)s)'
        cur = self.execute(sql, params)
        try:
            for rec in cur:
                r.append(rec[0])
        finally:
            cur.close()
        return r

    def get_table_columns(self, tblname):
        r = OrderedDict()
        cur = self.execute('SELECT lower(column_name) as n, data_type as t, character_maximum_length as l FROM information_schema.columns '
                           'WHERE (table_name = %(table_name)s) AND (table_schema = %(table_schema)s) order by information_schema.columns.ordinal_position',
                           {'table_name': tblname.lower(), 'table_schema': self.schema.lower()})
        try:
            for rec in cur:
                r[rec['n']] = {'data_type': rec['t'], 'size': rec['l']}
        finally:
            cur.close()
        return r

    def get_table_ftsindexes(self, tblname):
        """
            Возвращает словарь (<field_name>,<index_type>): <index_name> для всех FTS полей таблицы tblname.
            <index_type> может быть 'fts', 'trgm' или ''
        """
        r = {}
        # re для выделения из описания индекса FTS имени поля
        re_fts = r"""CREATE\s+INDEX\s+(?:\w+)\s+ON\s+(?:[\w,.]+)\s+USING\s+gin\s+\(to_tsvector\((?:[\w,'',:]+),[\s,(,"]*(\w+)[\s,),"]*\)"""
        # re для выделения из описания индекса по триграмам имени поля
        re_trgm = r"""CREATE\s+INDEX\s+(?:\w+)\s+ON\s+(?:[\w,.]+)\s+USING\s+gin\s+\((\w+)\s+gin_trgm_ops\s*\)"""
        # SELECT regexp_matches нужен, чтобы regexp_matches вернул ровно одну запись
        # а явное приведение к text[] нужно для того, чтобы не было синтаксической ошибки на pegasus2 pg v.9.2.1
        cur = self.execute(r"""
            SELECT idx.indexrelid::regclass::text,
              coalesce(
                ((SELECT regexp_matches(pg_get_indexdef(indexrelid), qre, 'i'))::text[])[1],
                ((SELECT regexp_matches(pg_get_indexdef(indexrelid), qre, 'i'))::text[])[2]) as field_name,
              CASE
                WHEN ((SELECT regexp_matches(pg_get_indexdef(indexrelid), qre, 'i'))::text[])[1] IS NOT NULL THEN %(index_type_fts)s
                WHEN ((SELECT regexp_matches(pg_get_indexdef(indexrelid), qre, 'i'))::text[])[2] IS NOT NULL THEN %(index_type_trgm)s
                ELSE ''
              END as indextype
            FROM
                cast(%(re_fts)s || '|' || %(re_trgm)s as text) qre,
                pg_index AS idx LEFT JOIN
                pg_class AS i ON (i.oid = idx.indexrelid) LEFT JOIN
                pg_namespace AS ns ON i.relnamespace = ns.oid
            WHERE (indrelid::regclass::text = %(table_name)s) AND (ns.nspname = %(table_schema)s)""",
            {'index_type_fts': PGFTS_INDEX_FTS, 'index_type_trgm': PGFTS_INDEX_TRGM,
             're_fts': re_fts, 're_trgm': re_trgm,
             'table_name': tblname.lower(), 'table_schema': self.schema.lower()})
        try:
            r = {(rec[1], rec[2]): rec[0] for rec in cur if rec[2]}
        finally:
            cur.close()
        return r

    def get_table_ftstriggers(self, tblname):
        """
            Возвращает словарь <field_name>: (<concat_field_list>, <trigger_name>, <function_name>)
            для всех FTS полей таблицы tblname, для которых создан триггер для конкатенации полей из <concat_field_list>
            для получения значения поля <field_name>.
            Триггер создается при описании индекса вида:
            /tNAME_FULL=G31_1,GROUP_NAME,G31_15;....
        """
        r = {}
        # re для выделения из триггерной функции имени поля и списка полей. смотри саму триггерную функцию (add_ftstriggers)
        re_concattriggerfunction = r"""\s+BEGIN\s+NEW\.(\w+)\s+=\s+array_to_string\(array\[(.+)\]"""
        re_field = r"""\s*NEW."""
        cur = self.execute(r"""
          SELECT
              (regexp_matches(p.prosrc, qre, 'i'))[1] as resultfield,
              regexp_replace((regexp_matches(p.prosrc, qre, 'i'))[2], qrefield, '', 'ig') as concatfieldlist,
              t.tgname, p.proname
          FROM
            cast(%(re_concattriggerfunction)s as text) qre,
            cast(%(re_field)s as text) qrefield,
            pg_trigger t LEFT JOIN
            pg_class cl ON cl.oid=tgrelid LEFT JOIN
            pg_namespace na ON na.oid=relnamespace LEFT JOIN
            pg_proc p ON p.oid=t.tgfoid
          WHERE
            (NOT t.tgisinternal) AND
            (cl.relname = %(table_name)s) AND
            (na.nspname = %(table_schema)s)
            """,
            {'re_concattriggerfunction': re_concattriggerfunction, 're_field': re_field,
             'table_name': tblname.lower(), 'table_schema': self.schema.lower()})
        try:
            r = {rec[0]: (rec[1].split(','), rec[2], rec[3]) for rec in cur}
        finally:
            cur.close()
        return r

    def check_for_tables(self, si=None):
        si = si or get_struct_info()
        tbllist = self.get_table_list()
        if tbllist:
            for tblname in si.tables.keys():
                if tblname.lower() not in tbllist:
                    return False
            return True
        return False

    def create_sequence(self, sequence_name):
        """ TODO: возвращать тип поля serial вместо ручного создания sequence.
        Если это действительно нужно.
        """
        raise NotImplementedError()

    def table_exists(self, tblname):
        return bool(self.get_table_list(tblname))

    def add_columns(self, dm, tblname, tbl_info, columns):
        """ добавление полей таблицы """
        if not dm.check_exclusive():
            return False
        r = False
        for column in columns:
            if column.pk or column.required:
                raise ETableRecreatePending(tblname, column.fldname)
        for column in columns:
            self.execute('ALTER TABLE %s ADD %s' % (tblname, dm.get_ddl_field_spec(tbl_info, column, typeconvert=self._pdox2sqlFieldType, keywords=self.KEYWORD_LIST)), None, True)
            dispname = psycopg2.extensions.adapt(column.dispname)
            dispname.prepare(self.conn)
            self.execute("COMMENT ON COLUMN %s.%s IS %s" % (str(tblname), str(column.fldname), dispname.getquoted()), None, True)
            r = True
        return r

    def delete_columns(self, dm, tblname, columns):
        """ удаление полей таблицы """
        if not dm.check_exclusive():
            return False
        r = False
        for column in columns:
            self.execute('ALTER TABLE %s DROP %s' % (tblname, column), None, True)
            r = True
        return r

    def resize_columns(self, dm, tblname, columns):
        if not dm.check_exclusive():
            return False
        r = False
        for column in columns:
            sql = 'ALTER TABLE %s ALTER COLUMN %s TYPE %s' % (tblname, column.get_field_name(), self._pdox2sqlFieldType(column))
            self.execute(sql, None, True)
            self.log('resizing field %s to %s' % (column.get_field_name(), column.fldtype))
            r = True
        return r

    def get_columns_to_resize(self, tblname, columns, si):
        r = []
        for field in si.tables[tblname].fieldnames.itervalues():
            if (field.pdoxtype in [ftString, ftGUID]) and field.size:
                column = columns.get(field.fldname.lower())
                if column:
                    try:
                        # Memo -> String (в основном актуально для отката изменений)
                        if column['data_type'] and column['data_type'] == 'text':
                            r.append(field)

                        elif column['size'] and (int(column['size']) < int(field.size)):
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

    def update_columns(self, dm, tblname, si = None, just_check = False):
        """ обновление полей для существующей таблицы
            пока реализовано добавление и удаление полей
            just_check - просто проверить на наличие необходимых полей
        """
        si = si or get_struct_info()
        columns = self.get_table_columns(tblname)
        columns_list = columns.keys()
        # добавление необходимых колонок
        columns_to_add = []
        for ind, field in enumerate(si.tables[tblname].fields):
            l_fieldname = field.fldname.lower()
            if l_fieldname not in columns:
                columns_to_add.append(field)
            elif field.pk and (ind < len(columns_list)) and (columns_list[ind] != l_fieldname):
                raise ETableRecreatePending(tblname, field.fldname)
        if columns_to_add:
            if just_check:
                # Проверка не пройдена
                self.log(u'Таблица %s. Не найдены поля %s. Требуется обновление.' % (tblname, ', '.join([field.fldname for field in columns_to_add])))
                return False
            self.add_columns(dm, tblname, si.tables[tblname], columns_to_add)
        columns_to_delete = None
        if dm.can_delete_columns:
            columns_to_delete = [column for column in columns if column.upper() not in si.tables[tblname].fieldnames]
            if columns_to_delete:
                if just_check:
                    # Проверка не пройдена
                    error = u'Таблица %s. Найдены неиспользуемые поля %s. Требуется обновление.' % (tblname, ', '.join(columns_to_delete))
                    self.errors.append(error)
                    self.log(error)
                    return False
                self.delete_columns(dm, tblname, columns_to_delete)
        columns_to_resize = self.get_columns_to_resize(tblname, columns, si)
        if columns_to_resize:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица %s. Изменился размер полей: %s. Требуется обновление.' % (tblname, ', '.join([field.fldname for field in columns_to_resize]))
                self.errors.append(error)
                self.log(error)
                return False
            self.resize_columns(dm, tblname, columns_to_resize)

        if columns_to_add or columns_to_delete or columns_to_resize:
            self.conn.commit()
        return True

    def _get_pg_version(self):
        """
        Вернуть номер версии в виде числа
        """
        vernum = 0
        cur = self.execute("SHOW server_version_num", None)
        try:
            row = cur.fetchone()
            if row:
                vernum = int(row[0])
        finally:
            cur.close()
        return vernum

    def _extension_is_available(self, extname):
        """
            Возвращает True, если расширение с именем extname доступно для установки в PG
        """
        r = False
        if self._get_pg_version() >= PG_VERSION_EXTENSION_START:
            # Процедура есть (версия Pg >= 9.1), можно продолжать
            cur = self.execute("SELECT count(*) AS c FROM pg_available_extensions WHERE name = %(ext_name)s",
                {'ext_name': extname})
            try:
                row = cur.fetchone()
                r = row and (int(row['c']) == 1)
            finally:
                cur.close()
        return r

    def _extension_is_installed(self, extname):
        """
            Возвращает True, если расширение с именем extname установлено в PG
        """
        r = False
        if self._get_pg_version() >= PG_VERSION_EXTENSION_START:
            # Расширения поддерживаются
            cur = self.execute("SELECT count(*) AS c FROM pg_extension WHERE extname = %(ext_name)s",
                {'ext_name': extname})
            try:
                row = cur.fetchone()
                r = row and (int(row['c']) == 1)
            finally:
                cur.close()
        return r

    def _extension_install(self, extname):
        """
            Возвращает True, если удалось установить расширение с именем extname
        """
        r = False
        if self._get_pg_version() >= PG_VERSION_EXTENSION_START:
            # Расширения поддерживаются
            try:
                self.execute('CREATE EXTENSION "%s"' % (extname,), None, True)
                r = True
            except psycopg2.Error, e:
                if e.pgcode == PGCODE_EXTENSION_ALREADY_EXISTS:
                    r = True
                else:
                    raise
        return r

    def _opclass_is_available(self, opclassname):
        """
            Возвращает True, если оператор присутстует
        """
        r = False
        cur = self.execute("SELECT count(*) AS c FROM pg_opclass WHERE opcname = %(opc_name)s",
             {'opc_name': opclassname})
        try:
            row = cur.fetchone()
            r = row and (int(row['c']) == 1)
        finally:
            cur.close()
        return r

    def update_ftsobjects(self, tblname, si=None, just_check=False):
        """ Обновление FullTextSearch полей для существующей таблицы.
            Для каждого поля, имеющего признак fts=True, должно существовать 2 индекса:
                CREATE INDEX <index_name> ON <table_name> USING gin (to_tsvector('simple'::regconfig, <field_name>)) для FTS
                CREATE INDEX <index_name> ON <table_name> USING gin (<field_name> gin_trgm_ops) для ускорения ILIKE.
            Для каждого поля, значение которого является конкатенацией значений других полей, должен существовать
                триггер и триггерная функция для его обновления.
            just_check - просто проверить на наличие необходимых индексов
        """
        si = si or get_struct_info()
        ftsindexes = self.get_table_ftsindexes(tblname)
        ftstriggers = self.get_table_ftstriggers(tblname)
        # получаем список описаний полей, для которых надо добавить триггер
        triggers_to_add = [field for field in si.tables[tblname].fields
                           if field.fts and (field.ftsconcatfields != ftstriggers.get(field.fldname, ([], None, None))[0])]
        # получаем список существующих триггеров и триггерных функций, которые надо удалить
        triggers_to_delete = [(fldname, ftstriggers[fldname][1], ftstriggers[fldname][2]) for fldname in ftstriggers if
                              (fldname not in si.tables[tblname].fieldnames) or  # поле удалили
                              (not si.tables[tblname].fieldnames[fldname].fts) or # поле уже не предназначено для FTS
                              (si.tables[tblname].fieldnames[fldname].ftsconcatfields != ftstriggers[fldname][0])]  # список конкатенируемых полей не совпадает

        # удаление лишних триггеров - может быть удалено все поле или только снят признак fts
        if triggers_to_delete:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица %s. Найдены неиспользуемые FTS триггеры (%s). Требуется обновление.' % \
                        (tblname, ', '.join(trigger[0] for trigger in triggers_to_delete))
                self.errors.append(error)
                self.log(error)
                return False
            self.delete_ftstriggers(tblname, triggers_to_delete)
        # добавление необходимых триггеров
        if triggers_to_add:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица %s. Не найдены FTS триггеры (%s). Требуется обновление.' % \
                         (tblname, ', '.join(['%s' % (field.fldname, ) for field in triggers_to_add]))
                self.errors.append(error)
                self.log(error)
                return False
            self.add_ftstriggers(tblname, triggers_to_add)
        # добавление необходимых индексов
        # получаем список пар: описание поля и тип отсутствующего индекса
        # но сначала надо проверить можно ли установить extension
        if self._extension_is_available(PG_EXTENSION_TRGM) or self._opclass_is_available(PG_OPCLASS_GIN_TRGM):
            supported_indexes = [PGFTS_INDEX_FTS, PGFTS_INDEX_TRGM]
        else:
            error = u'Таблица %s. Расширение %s не поддерживается или не установлено.' % (tblname, PG_EXTENSION_TRGM)
            self.errors.append(error)
            self.log(error)
            supported_indexes = [PGFTS_INDEX_FTS]
        indexes_to_add = [(field, index_type) for field in si.tables[tblname].fields
                          for index_type in supported_indexes
                          if field.fts and ((field.fldname.lower(), index_type) not in ftsindexes)]
        if indexes_to_add:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица %s. Не найдены FTS индексы %s. Требуется обновление.' % \
                         (tblname, ', '.join(['%s(%s)' % (field.fldname, index_type) for (field, index_type) in indexes_to_add]))
                self.errors.append(error)
                self.log(error)
                return False
            self.add_ftsindexes(tblname, indexes_to_add)
        # удаление лишних индексов - может быть удалено все поле или только снят признак fts
        # получаем список имен индексов, существующих в БД
        indexes_to_delete = [ftsindexes[(field, index_type)] for (field, index_type) in ftsindexes if
                             (field.upper() not in si.tables[tblname].fieldnames) or (not si.tables[tblname].fieldnames[field.upper()].fts)]
        if indexes_to_delete:
            if just_check:
                # Проверка не пройдена
                error = u'Таблица %s. Найдены неиспользуемые FTS индексы %s. Требуется обновление.' % (tblname, ', '.join(indexes_to_delete))
                self.errors.append(error)
                self.log(error)
                return False
            self.delete_ftsindexes(tblname, indexes_to_delete)
        if (indexes_to_add or indexes_to_delete or triggers_to_add or triggers_to_delete) and (not just_check):
            self.conn.commit()
        return True

    def drop_ftsobjects_all(self, tblname):
        """
        Удалить все FTS объекты таблицы.
        Это могут быть индексы, триггера, функции и т.д.
        """
        ftsindexes = self.get_table_ftsindexes(tblname)
        ftstriggers = self.get_table_ftstriggers(tblname)
        # получаем список существующих триггеров и триггерных функций, которые надо удалить
        triggers_to_delete = [(fldname, ftstriggers[fldname][1], ftstriggers[fldname][2]) for fldname in ftstriggers]
        # удаление лишних триггеров - может быть удалено все поле или только снят признак fts
        if triggers_to_delete:
            self.delete_ftstriggers(tblname, triggers_to_delete)
        indexes_to_delete = ftsindexes.values()
        if indexes_to_delete:
            self.delete_ftsindexes(tblname, indexes_to_delete)
        return True

    def create_ftsobjects_all(self, tblname):
        """ Создать все FTS объекты таблицы """
        return self.update_ftsobjects(tblname)

    def add_ftsindexes(self, tblname, columns):
        """
        Добавление fts-индексов. columns - список полей, для которых нужно создать fts и trgm индексы.
        Индексы имеют вид
            CREATE INDEX <index_name> ON <table_name> USING gin (to_tsvector('simple'::regconfig, <field_name>))
            CREATE INDEX <index_name> ON <table_name> USING gin (<field_name> gin_trgm_ops)
        """
        r = False
        for (column, index_type) in columns:
            if index_type == PGFTS_INDEX_FTS:
                self.execute("CREATE INDEX ON %s USING gin (to_tsvector(%s, %s))" %
                    (tblname, PGFTS_REGCONFIG, column.get_field_name(keywords=self.KEYWORD_LIST)), None, True)
                r = True
            elif index_type == PGFTS_INDEX_TRGM:
                # Проверить установлено ли расширение pg_trgm перед добавлением индекса
                if not self._extension_is_installed(PG_EXTENSION_TRGM):
                    # Установить расширение, если возможно
                    if self._extension_is_available(PG_EXTENSION_TRGM):
                        self._extension_install(PG_EXTENSION_TRGM)
                if self._opclass_is_available(PG_OPCLASS_GIN_TRGM):
                    # проверить наличие оператора
                    self.execute("CREATE INDEX ON %s USING gin (%s gin_trgm_ops)" %
                        (tblname, column.get_field_name(keywords=self.KEYWORD_LIST)), None, True)
                r = True
        return r

    def delete_ftsindexes(self, tblname, indexes):
        """ удаление fts-индексов. indexes - список имен индексов, подлежащих удалению """
        r = False
        for indexname in indexes:
            self.execute('DROP INDEX %s' % (indexname,), None, True)
            r = True
        return r

    def add_ftstriggers(self, tblname, columns):
        """
         Добавление fts-триггеров и функций.
            columns - список описаний полей, для которых нужно создать fts триггеры.
         Триггеры имеют вид:
            CREATE TRIGGER <trigger_name> BEFORE INSERT OR UPDATE ON <table_name>
                FOR EACH ROW EXECUTE PROCEDURE <trigger_function>()
         Перед добавлением удалим триггер с именем <trigger_name>
         Триггерная функция имеет вид:
            CREATE OR REPLACE FUNCTION <trigger_function>() RETURNS trigger AS
            $BODY$
            BEGIN
                NEW.<fieldname> = array_to_string(ARRAY[NEW.<fieldname1>,...,NEW.<fieldnameN>],', ');
                RETURN NEW;
            END;
            $BODY$
            LANGUAGE plpgsql
        """
        r = False
        for field in columns:
            trigger_name = "%s_%s_trigger" % (tblname, field.fldname)
            trigger_function_name = trigger_name + "_function"
            # Удалим триггер с этим именем
            self.delete_trigger(tblname, trigger_name)
            # создадим или заменим функцию
            self.execute("""
                CREATE OR REPLACE FUNCTION %s() RETURNS trigger AS
                $BODY$
                BEGIN
                    NEW.%s = array_to_string(ARRAY[%s],', ');
                    RETURN NEW;
                END;
                $BODY$
                LANGUAGE plpgsql""" %
                (trigger_function_name, field.fldname, ', '.join('NEW.' + concatfield for concatfield in field.ftsconcatfields)), None, True)
            # а теперь создадим триггер
            self.execute("CREATE TRIGGER %s BEFORE INSERT OR UPDATE ON %s FOR EACH ROW EXECUTE PROCEDURE %s()" %
                (trigger_name, tblname, trigger_function_name), None, True)
            r = True
        if r:
            # заставим сработать все добавленные триггеры (если они были) для всех записей, выполнив фиктивный UPDATE.
            self.execute("UPDATE %(tblname)s SET %(fldname)s = %(fldname)s" %
                         {'tblname': tblname, 'fldname': columns[0].ftsconcatfields[0]}, None, True)

        return r

    def delete_ftstriggers(self, tblname, triggers):
        """ удаление fts-индексов. indexes - список триггеров (<field_name>, <trigger_name>, <trigger_function_name>), подлежащих удалению """
        r = False
        for (fldname, trigger_name, trigger_function_name) in triggers:
            self.delete_trigger(tblname, trigger_name)
            self.execute('DROP FUNCTION IF EXISTS %s()' % (trigger_function_name,), None, True)
            r = True
        return r

    def delete_trigger(self, tblname, trigger_name):
        self.execute("DROP TRIGGER IF EXISTS %s ON %s" % (trigger_name, tblname), None, True)

    def drop_triggers_all(self, tblname):
        triggers = self.get_triggers(tblname)
        for trigger in triggers:
            self.delete_trigger(tblname, trigger)
        return True

    def _pdox2sqlFieldType(self, fieldspec):
        """ Преобразовать тип поля из Pdox в SQL
        """
        r = None
        if fieldspec.pdoxtype == ftString:
            r = domains.varchar(fieldspec.size)
        elif fieldspec.pdoxtype == ftMemo:
            r = domains.T_TEXT
        elif fieldspec.pdoxtype == ftAutoInc:
            r = 'SERIAL'
        elif fieldspec.pdoxtype == ftSmallint:
            r = domains.T_SMALLINT
        elif fieldspec.pdoxtype == ftInteger:
            r = domains.T_INT
        elif fieldspec.pdoxtype == ftDate:
            r = domains.T_DATE
        elif fieldspec.pdoxtype == ftDateTime:
            r = domains.T_DATETIME
        elif fieldspec.pdoxtype == ftFloat:
            r = domains.T_DOUBLE
        elif fieldspec.pdoxtype == ftBoolean:
            r = domains.T_BOOLEAN
        elif fieldspec.pdoxtype in (ftBlob, ftGraphic):
            r = domains.T_BINARY
        elif fieldspec.pdoxtype == ftGUID:
            r = domains.varchar(fieldspec.size)
        return r

    def get_triggers(self, tblname):
        """ получаем список триггеров """
        r = []
        cur = self.execute("""
            select pg_class.relname, pg_trigger.tgname
            from pg_class, pg_trigger
            where pg_class.oid = pg_trigger.tgrelid and pg_class.relname = %(tblname)s
        """, {'tblname': tblname.lower()}, without_check=True)
        try:
            for rec in cur:
                r.append(rec[1])
        finally:
            cur.close()
        return r

    def get_guidfunctionname(self):
        return 'guid_update_function'

    def get_guidtriggername(self, tblname, ftsindexname, suffix):
        return "{0}_{1}{2}".format(tblname, ftsindexname, suffix)

    def function_exists(self, funcname):
        cur = self.execute("""
            select proname from pg_proc where proname = %(funcname)s
        """, {'funcname': funcname.lower()}, without_check=True)
        try:
            for rec in cur:
                return True
        finally:
            cur.close()
        return False

    def add_guidfunction(self):
        """
           Добавляем функцию, которая будет генерировать guid для указанного поля
        """
        if self.function_exists(self.get_guidfunctionname()):
            return True
        # создадим или заменим функцию
        self.execute("""
            CREATE OR REPLACE FUNCTION %s() RETURNS TRIGGER AS $$
              DECLARE
                tblname TEXT := TG_ARGV[0];
                col TEXT := TG_ARGV[1];
              BEGIN
                EXECUTE format('update %%I set %%I = (select upper(cast(uuid_generate_v4() as VARCHAR(36)))) where CTID=($1)'::text, tblname, col) USING NEW.CTID;
                RETURN NEW;
              END;
              $$ LANGUAGE plpgsql;
            """ % self.get_guidfunctionname(), None, True)
        return True

    def create_extension(self, extname):
        r = self._extension_is_installed(extname)
        if not r:
            if self._extension_is_available(extname):
                return self._extension_install(extname)
            else:
                error = u'Расширение %s не поддерживается.' % (extname)
                self.errors.append(error)
                self.log(error)
                return False
        return r

    def create_guidobjects(self, tblname, tinfo):
        """ Создание триггеров для генерации GUID в соответствующих полях """
        r = self.create_extension(PG_EXTENSION_HSTORE) \
            and self.create_extension(PG_EXTENSION_UUID) \
            and self.add_guidfunction()
        if not r:
            return False
        for ind, field in enumerate(tinfo.fields):
            if field.pdoxtype != ftGUID:
                continue
            r = False
            l_fieldname = field.fldname.lower()
            trigger_name = self.get_guidtriggername(tblname, l_fieldname, self.TRIGGER_AI)
            triggers = self.get_triggers(tblname)
            if trigger_name not in triggers:
                ddl = """
                        CREATE TRIGGER {trigger_name} AFTER INSERT ON {table_name}
                        FOR EACH ROW WHEN (NEW.{guid_fieldname} is null)
                        EXECUTE PROCEDURE {guid_expr}('{table_name}', '{guid_fieldname}')
                      """.format(trigger_name=trigger_name,
                                 table_name=tblname,
                                 guid_fieldname=l_fieldname,
                                 guid_expr=self.get_guidfunctionname()
                                 )
                self.execute(ddl, None, True)
                r = True
            # Поле только одно
            break
        return r

    def check_guidobjects(self, tblname, tinfo, just_check=False):
        """ Проверка триггеров для генерации GUID в соответствующих полях """
        for ind, field in enumerate(tinfo.fields):
            if field.pdoxtype != ftGUID:
                continue

            for extname in (PG_EXTENSION_UUID, PG_EXTENSION_HSTORE):
                if not self._extension_is_installed(extname):
                    if just_check:
                        if not self._extension_is_available(extname):
                            error = u'Таблица %s. Расширение %s не поддерживается.' % (tblname, extname)
                            self.errors.append(error)
                            self.log(error)
                            return False
                        else:
                            error = u'Таблица %s. Расширение %s не установлено.' % (tblname, extname)
                            self.errors.append(error)
                            self.log(error)
                            return False
                    else:
                        return False

            l_fieldname = field.fldname.lower()
            trigger_name = self.get_guidtriggername(tblname, l_fieldname, self.TRIGGER_AI)
            triggers = self.get_triggers(tblname)
            if trigger_name not in triggers:
                if just_check:
                    # Проверка не пройдена
                    self.log(u'Таблица %s. Не найден триггер %s. Требуется обновление.' % (tblname, trigger_name))
                return False

        return True

    def create_tables(self, dm, tblname='', si=None, just_check=False, reindex=True, allow_triggers_on_reindex=False, *args, **kwargs):
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
                        for field in tbl_info.fields:
                            if field.seqname:
                                self.create_sequence(field.seqname)
                        create_ddl = dm.get_create_ddl(tbl_info, typeconvert=self._pdox2sqlFieldType, keywords=self.KEYWORD_LIST)
                        self.execute(create_ddl, None, close_cursor=True)
                        dispname = psycopg2.extensions.adapt(tbl_info.dispname)
                        dispname.prepare(self.conn)
                        comment_list = ['COMMENT ON TABLE %s IS %s' % (str(tbl_info.tblname), dispname.getquoted())]
                        for field in tbl_info.fields:
                            dispname = psycopg2.extensions.adapt(field.dispname)
                            dispname.prepare(self.conn)
                            comment_list.append('COMMENT ON COLUMN %s.%s IS %s' % (str(tbl_info.tblname), str(field.get_field_name(keywords=self.KEYWORD_LIST)), dispname.getquoted()))
                        self.execute(';'.join(comment_list), None, close_cursor=True)
                        # нам нужны guid триггеры в любом случае
                        if not self.create_guidobjects(tname, tbl_info):
                            return False
                        if reindex:
                            dm.index_table(tbl_info)
                        if not self.update_ftsobjects(tname, si, just_check):
                            return False
                        self.conn.commit()
                    else:
                        # таблица существует
                        if not self.update_columns(dm, tname, si, just_check):
                            return False
                        if reindex or just_check:
                            if not dm.check_indexes(tbl_info, False, just_check):
                                return False
                        # check_indexes может удалить лишние индексы, поэтому обновляем FTS объекты после переиндексации
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
        except ETableRecreatePending:
            raise
        except Exception, e:
            self.log(create_ddl)
            self.log(str(e))
            self.errors.append(str(e))
            raise
        return True

    def backup_tables(self, si = None):
        si = si or get_struct_info()

    def update_tables(self, dm, tblname='', si=None, reindex=True, *args, **kwargs):
        self.clear_errors()
        si = si or get_struct_info()
        return self.create_tables(dm, tblname, si, reindex=reindex, *args, **kwargs)

    def check_table_structure(self, dm, tblname = '', si=None):
        self.clear_errors()
        si = si or get_struct_info()
        return self.create_tables(dm, tblname, si, just_check=True, reindex=False)

    def connection_ok(self):
        """ Определяет, что подключение к базе данных присутствует """
        return self.conn is not None

    def exclusive_error(self):
        r = []
        params = {}
        params['datname'] = self.dbname.lower()
        sql = 'SELECT application_name, datname, usename, textin(inet_out(client_addr)) AS client '
        sql += 'FROM pg_stat_activity '
        sql += 'WHERE lower(datname) = %(datname)s'
        sql += 'ORDER BY 4 ASC '
        d = self.execute(sql, params)
        for rec in d:
            try:
                r.append('%s (%s) - %s' % (rec[2], rec[3], rec[0]))
            except:
                pass
        return '\n'.join(r)


class PgManager(sql_datamanager):
    # символы, запрещенные в строке для FTS поиска
    FTS_NOT_ALLOWED_CHARS = {ord(c): u' ' for c in u':()&|!"'}

    op_sign_override = {sql_datamanager.OS_LIKE_CI: 'ILIKE'}  # перекрытие операторов в конкретных БД

    def beforeInit(self, *args, **kwargs):
        self.log_init()
        super(PgManager, self).beforeInit(*args, **kwargs)
        self.conn = None
        self.allow_fill_defaults = True
        self.adapt_unicode = True
        # Преобразование типов в момент вставки данных (например, int -> bool)
        self.cast_values = False
        self.table_infos = {}

    def afterInit(self, *args, **kwargs):
        super(PgManager, self).afterInit(*args, **kwargs)
        self.db_type = DB_PG
        if self.conn is None:
            self.conn = PgConnectionFactory().get_connection(self.cfg, self.KEYWORD_LIST, encoding=self.encoding)
            if self.auto_connect:
                self.connect()
            if self.conn.conn and self.serverside:
                self.conn.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def __del__(self):
        PgConnectionFactory().put_connection(self.conn)
        del self.conn
        self.conn = None

    def log(self, message, otype = 'postgre', *args, **kwargs):
        return super(PgManager, self).log(message, otype)

    def adapt_where(self, value):
        return psycopg2.extensions.adapt(value)

    def do_format_param_key(self, key):
        return '%({:s})s'.format(self.str_encode(key))

    def get_databasename(self, tblname = '', *args, **kwargs):
        return self.conn.dbname

    def create_query(self, tblname, serverside=False):
        if self.conn:
            if serverside:
                cur = self.conn.cursor(without_check=self.is_transaction_enabled(), name=create_guid())
            else:
                cur = self.conn.cursor(without_check=self.is_transaction_enabled())

            if cur:
                return pq_query(cur)
            else:
                self.log_error('не могу создать cursor. возможно проблема с соединением')
                return None
        else:
            return None

    def get_binary_param_value(self, key, value):
        """ Если поле бинарное, что возможны варианты
            Внимание! Проверить.
            Since version 9.0 PostgreSQL uses by default a new “hex” format to emit bytea fields.
            Starting from Psycopg 2.4.1 the format is correctly supported.
            If you use a previous version you will need some extra care when receiving bytea from PostgreSQL:
            you must have at least the libpq 9.0 installed on the client
            or alternatively you can set the bytea_output configutation parameter to escape,
            either in the server configuration file or in the client session
            (using a query such as SET bytea_output TO escape;) before receiving binary data.
        """
        # ToDo Проверить то что написано в __doc__
        return psycopg2.Binary(key.set_value(value))

    def xmlcompressedfield(self, *args, **kwargs):
        """ Принято решение о том, что в pg xml поля будут хранится в незапакованном виде
            но т.к. поле BYTEA - поле бинарное
        """
        return self.binaryfield(*args, **kwargs)

    def binaryfield(self, *args, **kwargs):
        return PGBinaryField(*args, **kwargs)

    def dosql(self, tblname, sql, values=None, fields=None, ti=None, *args, **kwargs):
        r = 0
        q = self.create_query(tblname)
        try:
            try:
                q.SQL = [sql, ]
                q.params = self.get_params(values, fields, ti)
                q.ExecSQL()
                if q.cursor.rowcount <= 0:
                    return 0
                else:
                    r = q.cursor.rowcount
                    #self.conn.commit()
                    return r
            except EXMLCompressException, e:
                self.log_whereami(e, tblname)
            except psycopg2.Error, e:
                if e.pgcode == PGCODE_UNIQUE_VIOLATION:
                    self.log_whereami(e.pgerror, tblname)
                    raise EKeyViolation(e.pgerror, tblname)
                else:
                    if not self.raise_error:
                        show_error(None, 'Connection status: %d, Transaction status: %d' %
                                   (self.conn.conn.status, self.conn.conn.get_transaction_status()))
                    #self.conn.rollback()
                    self.log_whereami(e, tblname, sql)
                    self.show_error(e, sql)
                    if self.raise_error:
                        raise
            except Exception, e:
                #self.conn.rollback()
                self.log_whereami(e, tblname, sql)
                self.show_error(e, sql)
                if self.raise_error:
                    raise
        finally:
            del q

    def get_records(self, tblname, sql, where = None, start = 0, limit = 0, count_sql=None, serverside=False, *args, **kwargs):
        q = self.create_query(tblname, serverside=serverside)
        try:
            q.SQL = [sql, ]
            if limit:
                q.SQL.append(' LIMIT %d' % limit)
            if start > 0:
                q.SQL.append(' OFFSET %d' % start)
            q.params = self.get_params(where)
            q.Open()
        except Exception, e:
            #self.conn.rollback()
            self.show_error(e, sql)
            if self.raise_error:
                raise
            return None
        if start:
            start = 0
        if limit:
            limit = 0
        return PGRecords(self, q, 0, 0, count_sql=count_sql, *args, **kwargs)

    def check_decl_tblname(self, tblname):
        """ имена таблиц генерируется декларантом.
        поэтому сюда приходят имена таблиц типа AkcMrk.DB """
        return tblname and tblname.split('.')[0].lower() or tblname

    def update_tables(self, tblname='', si=None, reindex=True, *args, **kwargs):
        """ update_tables """
        super(PgManager, self).update_tables(tblname, si, reindex)
        try:
            r = self.conn and self.conn.update_tables(self, self.check_decl_tblname(tblname), si, *args, **kwargs) or False
            if not r:
                self.errors.extend(self.conn.errors)
            return r
        except ETableRecreatePending:
            r = self.recreate_table(tblname, si)
            if not r:
                self.errors.extend(self.conn.errors)
            return r

    def check_table_structure(self, tblname = '', si = None):
        super(PgManager, self).check_table_structure(tblname, si)
        r = self.conn and self.conn.check_table_structure(self, self.check_decl_tblname(tblname), si) or False
        if not r:
            self.errors.extend(self.conn.errors)
        return r

    def connection_ok(self):
        """ Определяет, что подключение к базе данных присутствует """
        return self.conn and self.conn.connection_ok()

    def check_server(self):
        """ Проверяет есть ли соединение с сервером БД (база данных по умолчанию).
        Если проблемы - exception.
        """
        self.disconnect()
        r = self.connect(just_test=True, setdbname=False, reraise=True)
        self.disconnect()
        return r

    def check_database(self):
        """ Проверяет есть ли нужная нам БД.
        Если нет - вернет False.
        """
        return self.conn.check_database()

    def check_schema(self):
        """ Проверяет есть ли нужная нам схема БД.
        Если нет - вернет False.
        """
        return self.conn.check_schema()

    def check_all(self):
        """Возвращает True|False. Ошибки self.errors
        """
        err = self.conn.check_all()
        if err:
            self.errors.append(err)
            return False
        return True

    def create_database(self):
        """ Создает базу. """
        return self.conn.create_database()

    def create_tables(self, *args, **kwargs):
        r = self.conn.create_tables(self, *args, **kwargs)
        if not r:
            self.errors.extend(self.conn.errors)
        return r

    def create_schema(self):
        """ Создает базу. """
        return self.conn.create_schema()

    def connect(self, *args, **kwargs):
        """ Соединяется с БД """
        return self.conn.connect(*args, **kwargs)

    def disconnect(self, *args, **kwargs):
        """ Отсоединяется от БД """
        return self.conn.disconnect(*args, **kwargs)

    def is_transaction_enabled(self):
        """ Мы используем транзакции или просто автокоммит?
        """
        return self.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

    def commit(self):
        if self.is_transaction_enabled():
            self.conn.commit()

    def rollback(self):
        if self.is_transaction_enabled():
            self.conn.rollback()

    def get_tables(self, tblname=''):
        if self.conn:
            return self.conn.get_table_list(tblname)
        return super(PgManager, self).get_tables(tblname)

    def get_index_sql(self, tblname='', indexname='', primary=False):
        sql = []
        if not indexname:
            sql.append('select distinct table_name,')
            sql.append('    index_name')
        else:
            sql.append('select table_name,')
            sql.append('    index_name,')
            sql.append('    column_name')
        sql.append('from (')
        sql.append('    select')
        sql.append('        t.relname as table_name,')
        sql.append('        i.relname as index_name,')
        sql.append('        a.attname as column_name,')
        sql.append('        unnest(ix.indkey) as unn,')
        sql.append('        a.attnum')
        sql.append('    from')
        sql.append('        pg_class t,')
        sql.append('        pg_class i,')
        sql.append('        pg_index ix,')
        sql.append('        pg_attribute a')
        sql.append('    where')
        sql.append('        t.oid = ix.indrelid')
        sql.append('        and i.oid = ix.indexrelid')
        sql.append('        and a.attrelid = t.oid')
        sql.append('        and a.attnum = ANY(ix.indkey)')
        sql.append("        and t.relkind = 'r'")
        if not primary:
            sql.append('        and not ix.indisprimary')
        if tblname:
            sql.append("        and t.relname='%s'" % tblname)
        if indexname:
            sql.append("        and i.relname='%s'" % indexname)
        sql.append('    order by')
        sql.append('        t.relname,')
        sql.append('        i.relname,')
        sql.append('        generate_subscripts(ix.indkey,1)) sb')
        sql.append('where unn = attnum')
        return '\n'.join(sql)

    def get_indexes(self, tblname='', primary=False):
        d = self.select_sql('X', self.get_index_sql(tblname, '', primary))
        if d:
            return [rec['INDEX_NAME'] for rec in d]
        return super(PgManager, self).get_indexes(tblname, primary)

    def get_indexfieldnames(self, tblname, indexname):
        """Получение списка полей для индекса"""
        d = self.select_sql('X', self.get_index_sql(tblname, indexname, True))
        if d:
            return [rec['COLUMN_NAME'] for rec in d]
        return super(PgManager, self).get_indexfieldnames(tblname, indexname)

    def get_column_names(self, tblname):
        if self.conn:
            r = self.conn.get_table_columns(tblname)
            if r:
                return r.keys()
        return super(PgManager, self).get_column_names(tblname)

    def format_where_match(self, key, sign, value, emptystr_is_null=None, params=None,
                           tblexpr=None, fieldexpr=None, rankexpr=None, osign=sql_datamanager.OS_MATCH_START,
                           ftsconcatfieldsdict=None, highlightfieldnamesuffix='',
                           highlight=False, startsel='', stopsel='', tblname=None, **kwargs):
        """
        MATCH в PG - свой синтаксис:
        to_tsvector(<config_name>, <field_name>) @@ [plain]to_tsquery(<config_name>, <query_string>)
        явное указание имени конфигурации FTS нужно для того, чтобы использовался индекс при поиске, а не полный перебор.
        При использовании to_tsquery, query_string должна быть разбита на слова и они должны быть соединены & (=and) или | (=or)
        каждое слово может завершаться :*, тогда будет поиск по началу слова. Если query_string состоит из нескольких слов, то
        они должны быть заключены в одинарные кавычки. Примеры:
            ''пиво водка''= пиво & водка
            пиво:* & водка:*
        Вместо to_tsquery можно использовать plainto_tsquery, тогда query_string может содержать произвольный текст и
        он будет разбит на слова, а слова будут соединены по AND. Опция поиска по началу слова в этом случае недоступна.

        Поскольку, tquery используется для выделения результата функцией ts_headline и для подсчета рейтинга (ts_rank),
        перенесем tsquery в список таблиц. Для этого добавляем новые параметры:
            tblexpr - словарь определений для части FROM <table_name>-><expression>
            fieldexpr - словарь <field name>-><expression> для преобразования в части SELECT в <expression> AS <field name>
            rankexpr - список выражений для подсчета общего рейтинга суммированием ts_rank по задействованным полям FTS.

        Если поле, по которому ищем, составное FTS поле, то можем добавить подсветку результатов для составляющих его полей.
        Для этого надо передать словарь ftsconcatfieldsdict, <имя составного FTS поля>-><список имен полей, требующих подсветки>.
        Тогда в словарь fieldexpr будут добавлены выражения для полей из соответствующего списка, а к имени поля будет добавлен
        суффикс highlightfieldnamesuffix (чтобы можно было получать оригинальное и подсвеченное значение поля). При использовании
        суффикса имена полей с суффиксами должны присутствовать в запрашиваемом списке полей.
        """
        # С фрагментами не задалось
        # highlightoptions = ", MaxWords=10, MinWords=2, ShortWord=0, HighlightAll=True, MaxFragments=2"
        HIGHLIGHTOPTIONS = ", HighlightAll=True, MaxFragments=0"
        TABLE_KEY_PREFIX = 'q'
        ftsconcatfieldsdict = {} if ftsconcatfieldsdict is None else ftsconcatfieldsdict
        fieldname = DataManager.unqualify_field_name(key)
        words_match, words_like = self.parse_value_for_format_where_match(value)
        if osign == self.OS_MATCH_PHRASE:
            # поиск полной фразы - если в words_match присутствуют фразы,
            # то надо разбить их на отдельные слова для match, а всю фразу добавить в words_like.
            new_words_match = []
            for onevalue in words_match:
                words = onevalue.split()
                if len(words) > 1:
                    words_like.append(onevalue)
                new_words_match.extend(words)
            words_match = new_words_match
        sql_list = []
        if words_match:
            # в запросе есть слова для FTS
            sql_list_match = []
            # Сгенерим имя для псевдо-таблицы
            table_key = self.generate_keyname(TABLE_KEY_PREFIX, tblexpr)
            for onevalue in words_match:
                param_key = self.format_param_key(fieldname,
                                                  onevalue + (':*' if osign == self.OS_MATCH_START else ''),
                                                  params=params, from_where=True)
                sql_list_match.append("to_tsquery({0}, {1})".format(PGFTS_REGCONFIG, param_key))
            if sql_list_match:
                tblexpr[table_key] = "cast(({0}) as tsquery)".format(' && '.join([k for k in sql_list_match]))
                rankexpr.append("ts_rank(to_tsvector({0}, {1}), {2})".format(PGFTS_REGCONFIG, key, table_key))
                if highlight:
                    # Составное FTS поле, используется только для поиска, в результирующей таблице не показывается,
                    # поэтому надо добавить подсветку только для полей, составляющих FTS поле.
                    # А если поле не составное, то добавляем подстветку только для него.
                    concatfields = ftsconcatfieldsdict.get(fieldname, [fieldname])
                    fieldexpr.update({cf + highlightfieldnamesuffix:
                        "ts_headline({0}, {1}, {2}, 'StartSel=''{3}'', StopSel=''{4}''{5}')".format(
                            PGFTS_REGCONFIG, cf, table_key, startsel, stopsel, HIGHLIGHTOPTIONS) for cf in concatfields})
                sql_list.append("(to_tsvector({0}, {1}) @@ {2})".format(PGFTS_REGCONFIG, key, table_key))
        if words_like:
            # в запросе есть текст для ILIKE (~~*).
            # Мы используем оператор ~* (Matches regular expression, case insensitive) он не требует заключения слов в %..%
            sql_list_like = []
            # Сгенерим имя для псевдо-таблицы
            table_key = self.generate_keyname(TABLE_KEY_PREFIX, tblexpr)
            for onevalue in words_like:
                param_key = self.format_param_key(fieldname, onevalue, params=params, from_where=True)
                sql_list_like.append(param_key)
            if sql_list_like:
                # искомая строка может содержать все что угодно, поэтому надо экранировать символы regex
                tblexpr[table_key] = "cast(array[{0}] as text[])".format(
                    ','.join([r"regexp_replace(%s, E'([[\\](){}.+*^$|\\\\?-])', E'\\\\\\1', 'g')" % (k,)
                              for k in sql_list_like]))
                if highlight:
                    concatfields = ftsconcatfieldsdict.get(fieldname, [])
                    REGEX_REPLACE_FMT = r"regexp_replace(%s, '(' || array_to_string(%s, '|') || ')', E'%s\\1%s', 'gi')"
                    if concatfields:
                        # Составное FTS поле, используется только для поиска, в результирующей таблице не показывается,
                        # поэтому надо добавить подсветку только для полей, составляющих FTS поле
                        for cf in concatfields:
                            concatfieldname = cf + highlightfieldnamesuffix
                            inner_value = fieldexpr.get(concatfieldname, cf)
                            fieldexpr[concatfieldname] = REGEX_REPLACE_FMT % (inner_value, table_key, startsel, stopsel)
                    else:
                        # поле не составное, добавляем подстветку только для него
                        inner_value = fieldexpr.get(fieldname + highlightfieldnamesuffix, key)
                        fieldexpr[fieldname + highlightfieldnamesuffix] = REGEX_REPLACE_FMT % \
                            (inner_value, table_key, startsel, stopsel)
            for i in range(1, len(words_like) + 1):
                sql_list.append("(%s ~* %s[%d])" % (key, table_key, i))
        res = ' AND '.join(sql_list)
        return res

    def get_ddl_default_value(self, field_info):
        r = super(PgManager, self).get_ddl_default_value(field_info)
        if r is None:
            if field_info.pdoxtype in (ftDateTime, ftDate):
                return "'-infinity'"
        return r

    def get_ddl_field_default(self, field_info):
        if field_info.seqname != '':
            return " DEFAULT nextval(" + self.QUOTE_STR + field_info.seqname + self.QUOTE_STR + ")"
        return super(PgManager, self).get_ddl_field_default(field_info)

    def exclusive_error(self):
        return ''
        if self.conn:
            return self.conn.exclusive_error()
        return ''

    def get_dbname(self):
        if self.conn:
            return self.conn.dbname
        return ''

    def drop_ftsobjects_all(self, tblname):
        """
        Удалить все FTS объекты таблицы.
        Это могут быть индексы, триггера, функции и т.д.
        """
        if self.conn:
            return self.conn.drop_ftsobjects_all(tblname)
        return True

    def create_ftsobjects_all(self, tblname):
        """ Создать все FTS объекты таблицы """
        if self.conn:
            return self.conn.create_ftsobjects_all(tblname)
        return True

    def drop_triggers_all(self, tblname):
        if self.conn:
            return self.conn.drop_triggers_all(tblname)
        return super(PgManager, self).drop_triggers_all(tblname)


class PGRecords(QueryRecords):

    def close_query(self):
        if self.query is not None:
            try:
                try:
                    self.query.Close()
                except Exception, e:
                    self.dm.conn.rollback()
                    show_error(e, 'PGRecords close_query error')
            finally:
                self.query = None

    def __len__(self):
        # cursor.rowcount для серверных курсоров кол-во полученных (fetched) записей
        return self.query.cursor.rowcount

    def __iter__(self):
        self.rec_n = 0
        self.qty = 0
        if self.start >= self.fixed_offset():
            pos = self.start - self.fixed_offset()
            if pos < self.query.cursor.rowcount:
                self.query.cursor.scroll(pos, mode='absolute')
                self.rec_n = pos
        return self

    def next(self):
        if self.limit > 0 and self.qty == self.limit:
            raise StopIteration
        else:
            if self.qty < self.fixed_offset():
                self.qty += 1
                return self.get_fixed_record(self.fixed_recs[self.qty])
            if not self.qty:
                record = self.query.cursor.fetchone()
            else:
                record = self.query.cursor.next()
            if not record:
                raise StopIteration
            self.qty += 1
            return self.get_record(record)

    def get_fixed_record(self, record):
        record['FIXED'] = True
        self.do_calc_record(record)
        return record

    def get_record(self, record):
        try:
            r = {}
            for key in record.iterkeys():
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


def main1():
    from gtd.db import get_struct_info
    si = get_struct_info()

    pg = PgManager(log_enabled = True)
    pg.update_tables()


def main():
    import sys
    import pdb
    pdb.set_trace()
    from gtd.db.data import get_express_manager
    m = get_express_manager()
    print sys.getrefcount(m)
    m = None


def test():
    pm = PgManager(conn = None)
    print pm.conn.get_table_columns('xmlbase').keys()


def test_binary():
    import zlib
    print psycopg2.__version__
    dm = PgManager(dbname = 'decl', host = 'localhost', user = 'postgres')
    key = {'ID' : 1}
    data = 'Фигак фигак тру ля ля'
    tbl = 'test'
    dm.delete(tbl, key)
    ikey = key.copy()
    ikey['DATA'] = psycopg2.Binary(zlib.compress(data))
    dm.insert(tbl, ikey)
    d = dm.select(tbl, ('DATA', ), key)
    if d:
        if data != zlib.decompress(d[0]['DATA']):
            print 'error'
        else:
            print 'ok'


def test_iterator():
    dm = PgManager(dbname = 'decl', host = 'localhost', user = 'postgres')
    tbl = 'test1'
    d = dm.select(tbl, ('*', ))
    if d:
        print d


def test_compressedfield():
    import zlib
    dm = PgManager(dbname = 'decl', host = 'localhost', user = 'postgres')
    key = {'ID' : 1}
    data = 'Фигак фигак тру ля ля'
    tbl = 'test'
    dm.delete(tbl, key)
    ikey = key.copy()
    field = dm.xmlcompressedfield('DATA')
    ikey[field] = data
    dm.insert(tbl, ikey)
    d = dm.select(tbl, ('DATA', ), key)
    if d:
        if data != zlib.decompress(d[0]['DATA']):
            print 'error'
        else:
            print 'ok'


def test_valname():
    from data import db_dict_config
    dm = PgManager(db_dict_config({PARAM_PG_SERVERDBNAME:'decl', PARAM_PG_SERVERNAME:'localhost', PARAM_PG_USERNAME: 'postgres'}))
    d = dm.select('valname', ('*', ), {'KOD': '978'})
    f = open('big.bmp', 'w')
    f.write(str(d[0]['BIG']))
    f.close()
    print d


if __name__ == "__main__":

    # test_iterator()
    # test_compressedfield()
    test_valname()

