# -*- coding: cp1251 -*-

"""

    модуль базового класса для доступа к данным

"""

import datetime
import time
import zlib
from os import path
import re
from dbconsts import *
from tks.strutils import format_error, uformat, to_ustr

from cdecimal import Decimal
from gtd import show_error
from tks import objects
from gtd.db import get_struct_info
from gtd import system

# список ключевых слов SQL, которые нельзя использовать как имена полей и таблиц
SQL_KEYWORD_LIST = []

class ETableProblem(Exception): pass
class EKeyViolation(Exception): pass
class ETypeMismatch(Exception): pass
class EAutoCreateError(Exception): pass
class EAutoCreateCancel(EAutoCreateError): pass
class ETableRecreatePending(Exception): pass
class EConnectionError(Exception): pass

# Максимальное количество параметров
# Ограничение для SQLite 999, для PG 32767
MAX_PARAM_COUNT = 700
SQL_INDEX_PATTERN = '^(.*)\((.*)\);?$'


class datevalue(object):

    def __init__(self, value):
        self.value = tuple(value)

    def __repr__(self):
        return 'time.struct_time(%s)' % (str(self.value))


class PureSQL(dict):
    """
    Словарь с вариантами чистого SQL для разных типов БД.
    Ключи: DB_COMMON, DB_PDOX, DB_PG, DB_SQLITE, DB_SQLITE2, DB_ODBC
    Значение: строка SQL для соответствующего типа БД.
    """

    def SQL(self, dbtype, notfoundsql='(NULL)'):
        return self.get(dbtype, self.get(DB_COMMON, notfoundsql))


class DataField(objects.baseobject):
    """ Обработка данных полей (чтение / запись) """

    def beforeInit(self, fieldname, *args, **kwargs):
        super(DataField, self).beforeInit(*args, **kwargs)
        self.fieldname = fieldname
        self.is_binary = False

    def set_value(self, value):
        return value

    def set_record_value(self, rec, value):
        rec[self.fieldname] = self.set_value(value)
        return value

    def get_value(self, value):
        return value

    def get_record_value(self, rec, defvalue = None):
        return self.get_value(rec.get(self.fieldname, defvalue))

    def __str__(self):
        return self.fieldname


class BinaryField(DataField):
    """ Бинарное поле (поле с возможным наличием #0) """
    def beforeInit(self, *args, **kwargs):
        super(BinaryField, self).beforeInit(*args, **kwargs)
        self.is_binary = True


class CompressedField(BinaryField):
    """
        Обработка сжатых полей
        Такие поля не могут участвовать в where
    """

    def set_value(self, value):
        if value:
            return self.compress(value)
        return value

    def get_value(self, value):
        if value:
            return self.decompress(value)
        return value

    def compress(self, data):
        return zlib.compress(data)

    def decompress(self, data):
        return zlib.decompress(data)


class EXMLCompressException(Exception): pass


class XMLCompressedField(CompressedField):
    """
        Обработка сжатых полей
        Такие поля не могут участвовать в where
    """

    raise_exceptions = False

    def beforeInit(self, *args, **kwargs):
        super(XMLCompressedField, self).beforeInit(*args, **kwargs)
        self.log_init()

    def check_xml(self, value):
        sval = str(value)
        return value and (sval.startswith('<?xml') or sval.startswith('\xEF\xBB\xBF<?xml') or sval.startswith('<env'))

    def set_value(self, value):
        if self.check_xml(value):
            return self.compress(value)
        if value and self.raise_exceptions:
            raise EXMLCompressException('set_value: value is not xml string. may be already compressed')
        # в pdox insert для поля xml "" вызывает ошибку
        # type mismatch in expression
        if value == "":
            return None
        return value

    def get_value(self, value):
        if self.check_xml(value):
            if value and self.raise_exceptions:
                raise EXMLCompressException('get_value: value is not compressed')
            return value
        if value:
            try:
                return self.decompress(value)
            except zlib.error, e:
                # TODO Здесь нужен идентификатор записи
                self.log_error(e, self.fieldname)
                return None
        return value


class substring_info(object):
    def __init__(self):
        self.string = ''
        self.from_index = 0
        self.for_index = 0


class DataManager(objects.baseobject):

    # коды Op_Sign OS_ - префиксы имен полей, используемые при формировании where части запроса или в условии join.
    OS_EQ = '='
    OS_NE_AND = '!'  # не равно, элементы list или tuple соединяется по И
    OS_NE_OR = '-'  # не равно, элементы list или tuple соединяется по ИЛИ
    OS_GT = '>'  # больше
    OS_LT = '<'  # меньше
    OS_GE = '}'  # больше или равно
    OS_LE = '{'  # меньше или равно
    OS_MATCH_EXACT = '~'  # полное совпадение слова
    OS_MATCH_START = '*'  # совпадает начало слова
    OS_MATCH_PHRASE = '@'  # совпадает фраза
    # Про match в SQLite: если передается список, то проверяется match для трех вариантов каждого слова из списка
    # слово*, СЛОВО*, Слово*. * - совпадение по началу слова.
    # Если передается просто строка, то проверяется match для этой строки (без *).
    # match для SQLite используется только в модуле tnved (htmldoc.py).
    # В PG OS_MATCH_EXACT и OS_MATCH_START работают, как положено и от регистра не зависят.
    OS_LIKE = '#'  # стандартный LIKE
    OS_ILIKE = '$'  # Только в PG! FTS оператор для регистро-независимого LIKE (в PG ищет по произвольному фрагменту текста без обрамления %)
    OS_LIKE_CI = '%'  # Регистро-независимый LIKE. В SQLite это обычный LIKE по-умолчанию. В PG - ILIKE
    OS_FIELD = '^'  # имя поля таблицы
    OS_FIELD_AND = '`'  # имя поля таблицы, используется в выражениях вида {'`field' : {'>':value, '<' : value}}
                        # для того чтобы условия соединялись через AND
    OS_IN = '?'  # IN
    OS_UPPER_EQ = '+'

    # Sql_Op_Sign SOS_ - операторы SQL, соотвествующие префиксам, если производится простая подстановка.
    SOS_EQ = '='
    SOS_NE = '<>'

    op_sign = {
        OS_EQ: SOS_EQ,
        OS_UPPER_EQ: SOS_EQ,
        OS_NE_AND: SOS_NE,
        OS_GT: '>',
        OS_GE: '>=',
        OS_LT: '<',
        OS_LE: '<=',
        OS_NE_OR: SOS_NE,
        OS_MATCH_EXACT: 'MATCH',
        OS_LIKE: 'LIKE',
        OS_MATCH_START: 'MATCH', # FTS match по началу слова
        OS_MATCH_PHRASE: 'MATCH',
        # FTS оператор для регистро-независимого LIKE (в PG ищет по произвольному фрагменту текста без обрамления %)
        OS_ILIKE: 'ILIKE',
        OS_LIKE_CI: 'LIKE',
        OS_IN: 'IN',
        # имя поля таблицы
        OS_FIELD: SOS_EQ,
        # используется в выражениях вида {'`field' : {'>':value, '<' : value}}
        # для того чтобы условия соединялись через AND
        OS_FIELD_AND: SOS_EQ,
    }

    op_sign_override = {}  # перекрытие операторов в конкретных БД

    # список зарезервированных слов, которые нельзя использовать в качестве имен таблиц и полей
    # http://www.postgresql.org/docs/current/static/sql-keywords-appendix.html
    # select * from pg_get_keywords()
    KEYWORD_LIST = ['WINDOW', 'ORDER', 'IN', 'OUT', 'DEFAULT', 'VALUES', 'MIN', 'MAX', 'YEAR', 'DOUBLE', 'LENGTH', 'WORK', 'DESC']

    # кавычка для формирования имен полей из списка зарезирвированных
    QUOTE_STR = "'"

    # атрибуты словаря (JoinDict_...) для генерации SQL вида:
    # <table1> <join_type> JOIN <table2> AS <table2_alias> ON <join_condition>
    JD_TABLE = 'table'
    JD_JOIN_TYPE = 'join'
    JD_JOIN_TYPE_LEFT = 'LEFT'
    JD_JOIN_TYPE_INNER = 'INNER'
    JD_JOIN_CONDITION = 'on'
    JD_TABLE_ALIAS = 'as'

    QFN_SEPARATOR = '.'  # Qualified Field Name separator - разделитель квалифицированного имени поля

    FLD_WITH_OS_FMT = '{0}{1}'  # строка форматирования для поля с префиксом OS_...

    MATCH_OP_AND = u' AND '
    MATCH_OP_OR = u' OR '

    def beforeInit(self, cfg=None, *args, **kwargs):
        super(DataManager, self).beforeInit(*args, **kwargs)
        self.on_error = None
        self.cfg = cfg
        if self.cfg:
            self.db_type = self.cfg.db_type
            self.encoding = self.cfg.encoding
        else:
            self.db_type = 0
            self.encoding = 'cp1251'
        self.field_encodings = {
            'XML': 'utf-8',
            'CFG': 'utf-8',
        }
        # Если параметр выборки p = '' то условие преобразуется в p in ('', Null)
        self.emptystr_is_null = False
        self.select_name_in_quotes = False # заключать в "" имя таблицы для sql-выражений
        # self.sql_table_ext расширение таблицы (с точкой). Если не пусто:
        # 1. в sql-выражении к имени таблицы оно добавляется
        # 2. в select по нескольким таблицам имя таблицы заключается в "" (self.select_name_in_quotes = True)
        self.sql_table_ext = ''
        self.errors = []
        # создавать исключения, вместо показа ошибок
        self.raise_error = False
        # PRAGMA journal_mode для sqlite
        self.journal_mode = True
        # атоматический commmit - для isolation_level
        self.autocommit = True
        # Возможность удалять колонки - не поддерживается в sqlite
        self.can_delete_columns = False
        # подсчитывать количество записей с помощью count(*)
        self.count_records = False
        # поддерживает ли query_records - для sqlite пока не имеет смысла из-за отсутсвия backward scrolling
        self.supports_query_records = True
        # Использовать имя таблицы в команде insert для зарезервированных слов
        self.tablename_in_insert = False
        # Есть ли реализация autoinc полей
        self.autoinc_enabled = True
        # Возможность конвертации параметров в строки
        self.allow_adapt = True
        # нужно ли заполнять пустые поля в ключе значениями по умолчанию
        self.allow_fill_defaults = False
        # Имена полей в результатах выборки - unicode
        self.unicode_fieldnames = False
        # преобразовывать значения полей unicode в str
        self.adapt_unicode = False
        # Использовать text_factory=str
        self._force_str = False
        # Автоматическое соединение с базой данных при создании
        self.auto_connect = True
        # Возможность использования serverside cursor (пока только для pg)
        self.serverside = False
        # Ограничивать "подозрительные" операции над пользовательскими данными
        # Например, update без параметров.
        self.restrict_suspicious_operations = True
        self.suspicious_where = False
        # Класс для обработки decimal
        self.decimal_cls = Decimal
        # Класс для записей
        self.rec_factory = dict
        # Последний сгенерированный sql запрос
        self.sql = ''
        # Значения параметров для последнего запроса
        self.params = {}
        # Время выполнения последнего запроса
        self.time_to_process = 0
        self.log_init()
        # делать upper для like
        self.upper_like = True
        # использовать тип данных для определения способа сложения условий (как было ранее)
        # False для того, чтобы работало как написано.
        self.use_and_types = False

    def get_field_encoding(self, fieldname):
        return self.field_encodings.get(fieldname, self.encoding)

    def get_force_str(self):
        return self._force_str

    def set_force_str(self, value):
        self._force_str = value
        self.do_set_force_str(value)

    def do_set_force_str(self, value):
        pass

    force_str = property(get_force_str, set_force_str)

    def finalizeInit(self, *args, **kwargs):
        super(DataManager, self).finalizeInit(*args, **kwargs)
        self.set_journal_mode(self.journal_mode)
        self.set_autocommit(self.autocommit)

    def format_error(self, error):
        return format_error(error)

    def clear_errors(self):
        self.errors = []

    def get_error_string(self, sep=u'\n'):
        return sep.join(self.errors)

    def is_datafield(self, key):
        """
            проблема проверки isinstance(key, DataField)
            иногда выдает False для XMLCompressedField
        """
        return not isinstance(key, basestring)

    def xmlcompressedfield(self, *args, **kwargs):
        return XMLCompressedField(*args, **kwargs)

    def binaryfield(self, *args, **kwargs):
        return BinaryField(*args, **kwargs)

    def is_time_tuple(self, value):
        return isinstance(value, tuple) and len(value) == 9 and isinstance(value[0], int)

    def adapt_fieldname(self, key):
        if self.unicode_fieldnames:
            if isinstance(key, unicode):
                return key
            return unicode(key, self.encoding)
        else:
            if isinstance(key, unicode):
                return key.encode(self.encoding)
            return key

    def get_decimal(self, value):
        return self.decimal_cls(value)

    def adapt(self, key, value, valuetype=ftUnknown):
        if self.is_datafield(key):
            return key.get_value(value)
        elif isinstance(value, datetime.datetime):
            if valuetype == ftDate:
                return value
            else:
                return value.timetuple()
        elif self.is_time_tuple(value):
            if valuetype == ftDate:
                return datetime.date(*value[:3])
            elif value[0] < 1971 or value[0] > 2037: # в mktime() 0 - 00:00:00 01.01.1970 по UTC
                return time.localtime(0)
            else:
                return time.struct_time(value)
        elif isinstance(value, float):
            if value > 10000000000.0:
                # после этого числа str() округляет в большую сторону до 1 знака после запятой
                return self.get_decimal(repr(value))
            else:
                return self.get_decimal(str(value))
        elif self.adapt_unicode and isinstance(value, unicode):
            return value.encode(self.get_field_encoding(key), errors='replace')
        elif not self.adapt_unicode and isinstance(value, str):
            return unicode(value, self.get_field_encoding(key))
        else:
            return value

    def show_error(self, error, sql = ''):
        if self.raise_error:
            return
        if self.on_error:
            self.on_error(error, sql)
        else:
            show_error(error, sql)

    def dosql(self, tblname, sql, values=None, where=None, fields=None, ti=None, *args, **kwargs):
        """ Возвращает количество записей, которые обработал запрос """
        return 0

    def get_sign(self, sign):
        return self.op_sign_override.get(sign, self.op_sign.get(sign, self.SOS_EQ))

    def split_sign(self, key):
        if key[0] in self.op_sign:
            return key[0], self.get_sign(key[0]), self.str_encode(key[1:])
        else:
            # оператор по умолчанию: =
            return self.OS_EQ, self.SOS_EQ, self.str_encode(key)

    def str_encode(self, s):
        if isinstance(s, unicode):
            return s.encode(self.encoding)
        return s

    def str_decode(self, s):
        if isinstance(s, basestring):
            return unicode(s, self.encoding)
        return s

    def format_where_key_none(self, sign, key):
        return '(%s is %s Null)' % (key, 'not' if sign != self.SOS_EQ else '')

    def adapt_where(self, value):
        return "'%s'" % (value)

    def format_where_param(self, sign, key, value):
        """ Форматирует строку параметра, когда ее надо вставить в where в виде строки """
        return "(%s %s %s)" % (key, sign, self.adapt_where(value))

    def format_where_bool(self, key, sign, value, params=None):
        return "(%s %s %s)" % (key, sign, self.format_param_key(key, value, params=params, from_where=True))

    def is_substring(self, key, ssi):
        p = 'SUBSTRING.?\((.+) FROM (\d+) FOR (\d+)\)'
        m = re.match(p, key, re.IGNORECASE)
        if m:
            g = m.groups()
            ssi.string = g[0]
            ssi.from_index = int(g[1])
            ssi.for_index = int(g[2])
            return True
        return False

    def format_substring(self, s, from_index, for_index):
        return "SUBSTR(%s, %d, %d)" % (s, from_index, for_index)

    def format_where_key(self, akey, value, emptystr_is_null=None, params=None, **kwargs):
        """
           Форматирует условие для поля.
           Если value - массив - то формируется выражение in
        """
        if emptystr_is_null is None:
            emptystr_is_null = True
        if not akey:
            self.suspicious_where = True
            return '(0 = 0)'
        else:
            if value == '' and emptystr_is_null and self.emptystr_is_null:
                value = (value, None)
                emptystr_is_null = False
            osign, sign, key = self.split_sign(akey)
            if value is None:
                return self.format_where_key_none(sign, key)
            elif isinstance(value, bool):
                return self.format_where_bool(key, sign, value, params)
            elif isinstance(value, int) or isinstance(value, self.decimal_cls):
                return '(%s %s %s)' % (key, sign, value)
            elif isinstance(value, basestring):
                # значение параметра - строка
                ssi = substring_info()
                if self.is_substring(key, ssi):
                    return "(%s %s %s)" % (
                        self.format_substring(ssi.string, ssi.from_index, ssi.for_index),
                        sign,
                        self.format_param_key('PARAM', value, params=params)
                    )
                elif osign == self.OS_FIELD: # поле таблицы
                    return "(%s %s %s)" % (key, sign, value)
                elif osign in [self.OS_MATCH_EXACT, self.OS_MATCH_START, self.OS_MATCH_PHRASE, self.OS_ILIKE]: # Full Text Search
                    return self.format_where_match(key, sign, value, emptystr_is_null=emptystr_is_null,
                                                   params=params, osign=osign, **kwargs)
                else:
                    param_key = self.format_param_key(key, value, params=params, from_where=True)
                    if osign in [self.OS_LIKE, self.OS_UPPER_EQ]:
                        if self.upper_like:
                            return "(UPPER(%s) %s UPPER(%s))" % (key, sign, param_key)
                    return "(%s %s %s)" % (key, sign, param_key)
            elif self.is_date(value):
                return self.format_where_date(key, sign, value) or \
                       "(%s %s %s)" % (key, sign, self.format_param_key(key, value, params=params))
            elif isinstance(value, PureSQL):
                if osign in [self.OS_EQ, self.OS_IN]:
                    # подзапрос
                    return "({0} {1} ({2}))".format(key, sign, value.SQL(self.db_type))
                else:
                    raise NotImplementedError()
            elif isinstance(value, dict):
                # значение параметра - словарь. как объединять элементы зависит от кода операции
                # попадаем сюда, когда osign == self.OS_FIELD_AND
                s = ' OR ' if osign in [self.OS_EQ, self.OS_NE_OR] else ' AND '
                return '(%s)' % (s.join([self.format_where_key(k + key, value[k], emptystr_is_null, params=params)
                                         for k in value]))
            elif value:
                # value - tuple или list
                if osign in [self.OS_MATCH_EXACT, self.OS_MATCH_START, self.OS_MATCH_PHRASE, self.OS_ILIKE]: # Full Text Search
                    return self.format_where_match(key, sign, value, emptystr_is_null=emptystr_is_null,
                                                   params=params, osign=osign, **kwargs)
                else:
                    # как объединять элементы зависит от кода операции
                    if not self.use_and_types:
                        s = ' OR ' if osign in [self.OS_EQ, self.OS_NE_OR, self.OS_LIKE] else ' AND '
                    else:
                        if isinstance(value, tuple):
                            s = ' AND '
                        else:
                            s = ' OR '
                    return '(%s)' % (s.join([self.format_where_key(akey, v, emptystr_is_null, params=params)
                                             for v in value]))
            self.suspicious_where = True
            return '(0 = 0)'

    def is_date(self, value):
        return isinstance(value, datetime.datetime) or isinstance(value, datetime.date) or \
            isinstance(value, time.struct_time) or self.is_time_tuple(value)

    def format_where_date(self, key, sign, value):
        """
        Форматировать параметр типа Date для where. Для учета особенностей Pdox
        """
        return ''

    def get_select_clause(self, *args, **kwargs):
        self.sql, _ = self.get_select_clause_2(*args, **kwargs)
        return self.sql

    def get_select_clause_2(self, tblname, fieldnames, where = None, order_by = None, group_by = None, distinct = False, params=None, *args, **kwargs):
        tblexpr = {}
        fieldexpr = {}
        rankexpr = []
        wherepart = self.get_where_clause(where, params=params, tblexpr=tblexpr, fieldexpr=fieldexpr, rankexpr=rankexpr,
                                          tblname=tblname, **kwargs)
        distinct_part = distinct and 'DISTINCT' or ''
        fieldlist = self.get_field_list(fieldnames, fieldexpr)
        tablelist = self.get_table_names(tblname, tblexpr=tblexpr, params=params, **kwargs)
        group_by_part = self.get_group_clause(group_by)
        order_by_part = self.get_order_clause(order_by, rankexpr)
        sql = 'select %s %s from %s %s %s %s' % (distinct_part, fieldlist, tablelist, wherepart, group_by_part, order_by_part)
        if group_by_part:
            count_sql = 'select count(*) from (%s) as subquery' % (sql,)
        else:
            count_sql = 'select count(*) from %s %s' % (tablelist, wherepart)
        return sql, count_sql

    def format_where_match(self, key, sign, value, emptystr_is_null=None, params=None, **kwargs):
        # MATCH sqlite и Pg - свой синтаксис: format_where_match будет перекрыт.
        # Здесь реализуем через LIKE, хотя использоваться не должно.
        return self.format_where_key(self.OS_LIKE+key, value, emptystr_is_null=emptystr_is_null, params=params, **kwargs)

    def get_table_names(self, tblnames, tblexpr=None, **kwargs):
        if tblexpr:
            t = []
            if isinstance(tblnames, basestring):
                t.append(tblnames)
            elif isinstance(tblnames, list):
                t.extend(tblnames)
            else:
                raise TypeError('Неподдерживаемый тип tblnames в get_table_names: {0}'.format(type(tblnames)))
            for table_alias, table_expression in tblexpr.iteritems():
                # Словарь <table_name>-><expression> для добавления таблиц и выражений для join'a в процессе обработки
                # дерева where
                if isinstance(table_expression, basestring):
                    # выражение, с именем. используется в pg fts. фактически это cross join,
                    # но можно заменить left join с пустым условием on (что даст нам left join on 0=0)
                    t.append({self.JD_TABLE: table_expression, self.JD_TABLE_ALIAS: table_alias})
                elif isinstance(table_expression, dict):
                    # уже сформирован нужный словарь для JOIN'а, его и добавим
                    t.append(table_expression)
                else:
                    raise TypeError('Неподдерживаемый тип table_expression в get_table_names: {0}'.format(type(
                        table_expression)))
            return self.get_table_list(t)
        if isinstance(tblnames, basestring):
            return self.get_table_name(tblnames, True)
        else:
            return self.get_table_list(tblnames, **kwargs)

    def get_table_name(self, tblname, select_expr = False, required_quotes = False):
        if isinstance(tblname, unicode):
            tblname = tblname.encode(self.encoding)
        r = tblname
        name_ext = path.splitext(path.split(tblname)[1])
        if self.sql_table_ext and name_ext[1] == '':
            r = '%s%s' % (r, self.sql_table_ext)
        if self.select_name_in_quotes or required_quotes:
            r = '"%s" %s' % (r, select_expr and name_ext[0] or '')
        return r

    def get_table_list(self, tblnames, *args, **kwargs):
        """ tblnames: список таблиц - [table1, table2, ...] или
        [table1, {'table':table2, 'join':'left'|'inner'|...(не обязат.), 'on':как where}, 'as': table_alias...]
        """
        r = []
        sep = ', '
        required_quotes = bool(self.sql_table_ext) # заключать в "" имя таблицы
        for tbl in tblnames:
            if isinstance(tbl, basestring):
                r.append(self.get_table_name(tbl, True, required_quotes))
            else:
                sep = ' '
                r.append(u'{0} JOIN {1} {2} ON {3}'.format(
                    tbl.get(self.JD_JOIN_TYPE, self.JD_JOIN_TYPE_INNER),
                    self.get_table_name(tbl.get(self.JD_TABLE, ''), True, required_quotes),
                    u'AS {0}'.format(tbl.get(self.JD_TABLE_ALIAS)) if self.JD_TABLE_ALIAS in tbl else '',
                    self.format_where_clause(tbl.get(self.JD_JOIN_CONDITION, None), **kwargs)))
        return sep.join(r)

    def get_field_list(self, fieldnames, fieldexpr=None):
        if fieldexpr:
            # Словарь <field_name>-><expression> в список строк <expression> AS <field_name>
            fieldlist = map(lambda x: str(x.strip()), fieldnames.split(',')) if isinstance(fieldnames, basestring) else fieldnames
            r = u','.join([u"{0} AS {1}".format(fieldexpr[field], field)
                          if field in fieldexpr else field for field in fieldlist])
            return r
        if isinstance(fieldnames, basestring):
            return fieldnames
        else:
            return ', '.join([str(fld) for fld in fieldnames])

    @staticmethod
    def unqualify_field_name(qualified_field_name):
        return qualified_field_name.split(DataManager.QFN_SEPARATOR)[-1]

    @staticmethod
    def qualify_field_name(qualification_list, field_name):
        if qualification_list:
            if isinstance(qualification_list, list):
                # схема, база, таблица
                full_name_list = qualification_list + [field_name]
            else:
                # таблица
                full_name_list = [qualification_list, field_name]
            return DataManager.QFN_SEPARATOR.join(full_name_list)
        else:
            # нечем квалифицировать
            return field_name

    def format_where_clause(self, where=None, params=None, defvalue='0=0', matchexpr=None, matchop=None, **kwargs):
        if where:
            """
            В SQLite нужно учесть, что FTS match имеет ограничения - для одного индекса (FTS таблицы)
            в запросе может быть только один вызов match. Поэтому, нужно собрать и объединить все
            условия, относящиеся к одной FTS таблице, если это возможно.
            """
            childmatchexpr = {}  # словарь для группировки выражений match (используется только SQLite)
            childmatchop = self.MATCH_OP_AND
            if isinstance(where, list):
                orlist = []
                childmatchop = self.MATCH_OP_OR
                for w in where:
                    ornode = self.format_where_clause(w, params,
                                                      matchexpr=childmatchexpr, matchop=childmatchop, **kwargs)
                    if ornode:
                        orlist.append(u'({0})'.format(ornode))
                ornode = self.process_match_expr(parentmatchexpr=matchexpr, parentmatchop=matchop,
                                                 childmatchexpr=childmatchexpr, childmatchop=childmatchop,
                                                 otherexpr=orlist, params=params, **kwargs)
                if ornode:
                    orlist.append(u'({0})'.format(ornode))
                return u' OR '.join(orlist)
            elif isinstance(where, tuple):
                andlist = []
                for w in where:
                    andnode = self.format_where_clause(w, params,
                                                       matchexpr=childmatchexpr, matchop=childmatchop, **kwargs)
                    if andnode:
                        andlist.append(u'({0})'.format(andnode))
                andnode = self.process_match_expr(parentmatchexpr=matchexpr, parentmatchop=matchop,
                                                  childmatchexpr=childmatchexpr, childmatchop=childmatchop,
                                                  otherexpr=andlist, params=params, **kwargs)
                if andnode:
                    andlist.append(u'({0})'.format(andnode))
                return u' AND '.join(andlist)
            elif isinstance(where, PureSQL):
                return where.SQL(self.db_type)
            elif isinstance(where, dict):
                andlist = []
                for key in where.keys():
                    andnode = self.format_where_key(key, where[key], params=params,
                                                    matchexpr=childmatchexpr, matchop=childmatchop, **kwargs)
                    if andnode:
                        andlist.append(u'({0})'.format(andnode))
                andnode = self.process_match_expr(parentmatchexpr=matchexpr, parentmatchop=matchop,
                                                  childmatchexpr=childmatchexpr, childmatchop=childmatchop,
                                                  otherexpr=andlist, params=params, **kwargs)
                if andnode:
                    andlist.append(u'({0})'.format(andnode))
                return u' AND '.join(andlist)
            else:
                raise TypeError('Неподдерживаемый тип where в format_where_clause: {0}'.format(type(where)))
        return defvalue

    def get_where_clause(self, where=None, add_condition='', params=None, **kwargs):
        if where:
            s = self.format_where_clause(where, params, defvalue='', **kwargs)
            if s or add_condition:
                if isinstance(add_condition, dict):
                    if self.db_type in add_condition:
                        cond = add_condition[self.db_type]
                    else:
                        cond = add_condition.get(DB_COMMON, ' and (1=0)')
                else:
                    cond = add_condition
                s = 'where %s%s' % (s, cond)
            return s
        return ''

    def process_match_expr(self, **kwargs):
        return None

    def get_order_clause(self, order_by, rankexpr=None):
        if order_by:
            for ob_item in order_by:
                if ob_item.startswith(RANK_FIELD_NAME):
                    if rankexpr:
                        return 'order by ' + '+'.join(rankexpr) + ob_item[len(RANK_FIELD_NAME):]
                    else:
                        # несортированный результат
                        return ''
        if order_by:
            return 'order by ' + ', '.join(order_by)
        return ''

    def get_group_clause(self, group_by = None):
        if group_by:
            return 'group by ' + ', '.join(group_by)
        return ''

    def execsql(self, tblname, sql, values=None, fields=None, ti=None, *args, **kwargs):
        """
         ti: dbstruct.table_info
        """
        if ti is not None:
            if fields is None:
                fields = {}
                for fieldspec in ti.fields:
                    if fieldspec.is_binary() and (fieldspec not in fields):
                        fields[fieldspec.fldname] = BinaryField(fieldspec.fldname)
        return self.dosql(tblname, sql, values, fields=fields, ti=ti, *args, **kwargs)

    def process_fields(self, fieldnames, fields):
        a = [(fld.fieldname, fld) for fld in fieldnames if self.is_datafield(fld)]
        if a:
            r = fields or {}
            r.update(dict(a))
            return r
        else:
            return fields

    def init_params(self):
        return {}

    def select(self, tblname, fieldnames, where=None,
               order_by=None, group_by=None, distinct=False, fields=None,
               params=None, out=None, *args, **kwargs):
        if params is None:
            params = self.init_params()
        sql, count_sql = self.get_select_clause_2(tblname, fieldnames, where, order_by, group_by, distinct, params, *args, **kwargs)
        if out is not None:
            out['count_sql'] = count_sql
            out['params'] = params
            out['sql'] = sql
        self.params = params
        return self.select_sql(tblname, sql, params, fields = self.process_fields(fieldnames, fields), *args, **kwargs)

    def select_records(self, tblname, fieldnames, where=None,
                       order_by=None, group_by=None, distinct=False, fields=None,
                       serverside=False, params=None, *args, **kwargs):
        if not self.supports_query_records:
            return self.select(tblname, fieldnames, where, order_by, group_by, distinct, fields, *args, **kwargs)
        if params is None:
            params = self.init_params()
        sql, count_sql = self.get_select_clause_2(tblname, fieldnames, where, order_by, group_by, distinct, params, *args, **kwargs)
        if not self.count_records:
            count_sql=None
        return self.get_records(tblname, sql, params, fields=self.process_fields(fieldnames, fields), count_sql=count_sql, serverside=serverside, *args, **kwargs)

    def select_sql(self, tblname, sql, where=None, alone=False, *args, **kwargs):
        if alone:
            self.init_params()
        return self.fetch(tblname, sql, where, *args, **kwargs)

    def fetch(self, tblname, sql, where = None, limit = 0, start = 0, *args, **kwargs):
        starttime = datetime.datetime.now()
        recs = self.get_records(tblname, sql, where, start, limit, *args, **kwargs)
        try:
            r = []
            if recs is not None:
                for rec in recs:
                    r.append(rec)
                recs.close_query()
            return r
        finally:
            del recs
            self.time_to_process = datetime.datetime.now() - starttime

    def get_records(self, tblname, sql, where = None, start = 0, limit = 0, count_sql=None, serverside=False, *args, **kwargs):
        return []

    def locate(self, tblname, where=None, *args, **kwargs):
        self.count_records = True
        d = self.select_records(tblname, ('count(*) as C', ), where, *args, **kwargs)
        self.count_records = False
        return d and int(d[0]['C']) or 0

    def recordcount(self, tblname, where=None, *args, **kwargs):
        return self.locate(tblname, where, *args, **kwargs)

    def generate_keyname(self, basename, params):
        """
            Генерирование имен параметров, которые появляются в процессе разбора условий поиска
        """
        i = 1
        # Разбираем имена типа XMLBASE.IDLIST
        basename = basename.split('.')[-1]
        while i < MAX_PARAM_COUNT:
            keyname = '{:s}_{:d}'.format(basename, i)
            if keyname not in params:
                return keyname
            i += 1
        return basename

    def do_format_param_key(self, key):
        return ':{:s}'.format(self.str_encode(key))

    def format_param_key(self, key, value, fields=None, params=None, from_where=False, allow_adapt=True):
        keyname = self.str_encode(key)
        if params is not None:
            keyname = self.generate_keyname(keyname, params)
            params[keyname] = value
        return self.do_format_param_key(keyname)

    def get_param_name(self, key):
        if key:
            if not isinstance(key, basestring):
                return str(key)
            elif key[0] not in self.op_sign:
                return key
            else:
                return key[1:]
        return key

    def is_keyword(self, name):
        """ Проверяет, является ли идентификатор (имя поля или таблицы) ключевым словом.
        """
        return name.upper() in self.KEYWORD_LIST

    def format_name(self, name, fieldname=True):
        return name and name.lower() or name

    def qw(self, word):
        return '{}{}{}'.format(self.QUOTE_STR, word, self.QUOTE_STR)

    def format_field_name(self, name, tblname, from_insert=True):
        """ Форматировать имя поля.
        name -> tblname."name", если name:
        1. начинается с _.
        2. является ключевым словом.
        """
        if self.is_keyword(name):
            # возможна ошибка, если использовать расширение. например, pdox
            if from_insert and (self.sql_table_ext or not self.tablename_in_insert):
                return self.qw(self.format_name(name))
            else:
                return '{}.{}{}{}'.format(self.format_name(tblname, False), self.QUOTE_STR, self.format_name(name), self.QUOTE_STR)
        return name

    def get_binary_param_value(self, key, value):
        """ Если поле бинарное, что возможны варианты """
        return key.set_value(value)

    def get_fieldobj_value(self, fieldobj, value):
        if fieldobj.is_binary:
            return self.get_binary_param_value(fieldobj, value)
        return fieldobj.set_value(value)

    def get_param_value(self, key, value, fieldobj = None):
        if value is None:
            return value
        elif fieldobj:
            return self.get_fieldobj_value(fieldobj, value)
        elif self.is_datafield(key):
            return self.get_fieldobj_value(key, value)
        else:
            return value

    def filter_params_value(self, value, fieldobj=None, allow_adapt=True):
        return True

    def adapt_param_value(self, param_name, param_value, ti=None):
        """
         Преобразование значение параметра перед непосредственной передачей их в запрос
        """
        if ti is not None:
            if param_name in ti.fieldnames:
                if ti.fieldnames[param_name].pdoxtype in (ftBoolean, ):
                    return not not param_value
        return param_value

    def get_params_dict(self, values, fields=None, ti=None):
        r = {}
        for key, value in values.items():
            param_name = self.get_param_name(key)
            fieldobj = None
            if fields:
                fieldobj = fields.get(param_name)
            elif self.is_datafield(key):
                fieldobj = key
            try:
                param_value = self.get_param_value(key, value, fieldobj)
            except Exception, e:
                show_error(e, key)
            if fieldobj or self.filter_params_value(param_value, fieldobj, allow_adapt=(ti is None) and self.allow_adapt):
                r[param_name] = self.adapt_param_value(param_name, param_value, ti)
        return r

    def get_params(self, values, fields=None, ti=None):
        vv = None
        if isinstance(values, dict):
            vv = values
        elif values:
            vv = values[0]
        if isinstance(vv, dict) and vv:
            return self.get_params_dict(vv, fields, ti)
        return vv

    def get_update_clause(self, tblname, values, where=None, fields=None, params=None, **kwargs):
        if ('inc' in kwargs) and kwargs['inc']:
            temp = []
            for key in values.keys():
                if key in kwargs['inc']:
                    temp.append('{0} = CASE WHEN {0} IS NULL THEN 0 ELSE {0} END + {1}'.format(self.str_encode(key),
                                self.format_param_key(key, values[key], fields)))
                else:
                    temp.append('%s = %s' % (self.str_encode(key), self.format_param_key(key, values[key], fields)))
            fldlist = ', '.join(temp)
        else:
            fldlist = ', '.join(['%s = %s' % (self.str_encode(key),
                                          self.format_param_key(key, values[key], fields))
                                          for key in values.keys()])
        where_str = self.get_where_clause(where, params=params, **kwargs)
        updtablename = self.get_table_name(tblname)
        r = 'update %s set %s %s' % (updtablename, fldlist, where_str)
        return r

    def get_insert_clause(self, tblname, values, fields=None, allow_adapt=True, on_filter_values=None, **kwargs):
        if on_filter_values:
            fieldnames = [fieldname for fieldname in values.keys()
                          if on_filter_values and on_filter_values(fieldname)]
        else:
            fieldnames = values.keys()
        return 'insert into %s (%s) values (%s)' % (
            self.get_table_name(tblname),
            ', '.join([self.format_field_name(self.get_param_name(key), self.get_table_name(tblname, True))
                       for key in fieldnames]),
            ', '.join(['%s' % (self.format_param_key(key, values[key], fields, allow_adapt=allow_adapt)) for key in fieldnames]))

    def get_delete_clause(self, tblname, where = None, **kwargs):
        return 'delete from %s %s' % (
            self.get_table_name(tblname),
            self.get_where_clause(where, **kwargs)
            )

    def combine_values(self, values, where = None):
        if where:
            return dict(values.items() + where.items())
        else:
            return values

    def update(self, tblname, values, where=None, force=False, *args, **kwargs):
        self.suspicious_where = False
        params = self.init_params()
        update_str = self.get_update_clause(tblname, values, where, params=params, **kwargs)

        if self.restrict_suspicious_operations and (not where or self.suspicious_where) and not force:
            self.log('suspicious where in sql update')
            self.log_stack()
            return 0

        if values:
            params.update(values)
        return self.execsql(tblname, update_str, params, *args, **kwargs)

    def insert(self, tblname, values, *args, **kwargs):
        insert_str = self.get_insert_clause(tblname, values, **kwargs)
        return self.execsql(tblname, insert_str, values, *args, **kwargs)

    def insert_many(self, tblname, values, fieldnames=None, on_record=None, on_after_record=None, on_error=None, ti=None, *args, **kwargs):
        try:
            fieldnames = fieldnames or values[0]
        except:
            return 0
        r = 0
        insert_str = self.get_insert_clause(tblname, fieldnames, allow_adapt=(ti is None) and self.allow_adapt, **kwargs)
        for rec in values:
            try:
                if on_record is not None:
                    if not on_record(rec):
                        r += 1
                        continue
                r += self.execsql(tblname, insert_str, rec, ti=ti, *args, **kwargs)
                if on_after_record is not None:
                    if not on_after_record(rec, r):
                        return r
            except Exception, e:
                if on_error is not None:
                    if on_error(e, rec):
                        continue
                    else:
                        break
                else:
                    raise
        return r

    def update_or_insert(self, tblname, values, where=None, *args, **kwargs):
        r = self.update(tblname, values, where, *args, **kwargs)
        if not r:
            values.update(where)
            r = self.insert(tblname, values, *args, **kwargs)
        return r

    def delete(self, tblname, where=None, force=False, *args, **kwargs):
        self.suspicious_where = False
        params = self.init_params()
        delete_str = self.get_delete_clause(tblname, where, params=params, **kwargs)

        if self.restrict_suspicious_operations and (not where or self.suspicious_where) and not force:
            self.log('suspicious where in sql delete')
            self.log_stack()
            return 0

        return self.execsql(tblname, delete_str, params, *args, **kwargs)

    def get_databasename(self, tblname, *args, **kwargs):
        return ''

    def update_tables(self, tblname=None, si=None, reindex=True, *args, **kwargs):
        if not self.check_exclusive():
            return False
        # все нормально - работаем дальше
        self.clear_errors()
        return True

    def check_table_structure(self, tblname = '', si = None):
        # Проверка структур таблиц прошла нормально
        self.clear_errors()
        return True

    def connection_ok(self):
        """ Определяет, что подключение к базе данных присутствует """
        return True

    def check_server(self):
        """ Проверяет есть ли соединение с сервером БД (база данных по умолчанию).
        Если проблемы - exception.
        """
        return True

    def check_database(self):
        """ Проверяет есть ли нужная нам БД.
        Если нет - вернет False.
        """
        return True

    def check_schema(self):
        """ Проверяет есть ли нужная нам схема БД.
        Если нет - вернет False.
        """
        return True

    def check_all(self):
        """
            проверяет соединение, наличие базы данных и схемы данных
        """
        return True

    def get_tables(self, tblname=''):
        """
         Получение списка таблиц
         get_table_list уже занято
        """
        return []

    def get_triggers(self, tblname):
        """Получение списка триггеров"""
        return []

    def get_indexes(self, tblname = '', primary=False):
        """ Получение списка индексов """
        return ()

    def get_index_set(self, tblname='', primary=False):
        r = set()
        for indexname in self.get_indexes(tblname, primary):
            r.add(tuple(self.get_indexfieldnames(tblname, indexname)))
        return r

    def get_indexfieldnames(self, tblname, indexname):
        """Получение списка полей для индекса"""
        return ()

    def table_exists(self, tblname):
        return bool(self.get_tables(tblname))

    def trigger_exists(self, tblname, trigger):
        return trigger in self.get_triggers(tblname)

    def drop_table(self, tblname, check_exist=True):
        """
         удаление таблицы
        """
        if not check_exist or self.table_exists(tblname):
            return self.dosql(tblname, self.get_drop_ddl(tblname))
        return 0

    def borrow_struct(self, si, tbllist=None, structdesc='', *args, **kwargs):
        """
            Заполнение информации о структуре по существующим данным
        """
        if not tbllist:
            tbllist = self.get_tables()
        elif isinstance(tbllist, basestring):
            tbllist = (tbllist, )
        for tblname in tbllist:
            if tblname in si.tables.keys():
                continue
            tbl = si.addtable(tblname)
            if structdesc:
                self.borrow_table_desc(tblname, tbl, structdesc)
            else:
                self.borrow_table_struct(tblname, tbl)

    def borrow_table_desc(self, tblname, tbl, structdesc):
        # ToDo: сделать загрузку структуры таблицы из файла
        pass

    def borrow_table_struct(self, tblname, tbl):
        """
        :param tblname: str
        :param tbl: dbstruct.table_info
        :return: dbstruct.table_info
        Заполнение структуры table_info данными об отдельно взятой таблицы с имененем tblname
        """
        pass

    def set_journal_mode(self, journal_mode):
        pass

    def set_autocommit(self, autocommit):
        pass

    def connect(self, *args, **kwargs):
        """ Соединяется с БД """
        return ''

    def disconnect(self, *args, **kwargs):
        """ Отсоединяется от БД """
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def select_max(self, tblname, fieldname):
        d = self.select(tblname, ('max(%s) as m' % fieldname, ))
        if d:
            return d[0]['M'] or 0
        return 0

    def fill_defaults(self, rec, pk_defaults):
        if self.allow_fill_defaults:
            for fieldname in pk_defaults:
                if fieldname in rec and rec[fieldname] is None:
                    rec[fieldname] = pk_defaults[fieldname]

    def get_column_names(self, tblname):
        return []

    def get_ddl_field_default(self, field_info):
        if field_info.pk or field_info.required:
            if field_info.default is not None:
                return " DEFAULT %s" % (field_info.default)
            elif field_info.pdoxtype == ftString:
                return " DEFAULT ''"
            else:
                defvalue = self.get_ddl_default_value(field_info)
                if defvalue is not None:
                    return " DEFAULT %s" % (defvalue, )
        return ''

    def get_ddl_field_spec(self, table_info, field_info, typeconvert=None, keywords=()):
        """
         typeconvert - функция с одним аргументом. возвращает тип поля
        """
        r = '%s %s' % (field_info.get_field_name(keywords), typeconvert and typeconvert(field_info) or field_info.fldtype)
        if (field_info.pk and not table_info.is_null_pk_allowed()) or field_info.required:
            r += ' NOT NULL'
            r += self.get_ddl_field_default(field_info)
        return r

    def get_ddl_default_value(self, field_info):
        if field_info.pdoxtype == ftString:
            return ''
        elif field_info.pdoxtype in (ftInteger, ftSmallint, ftFloat):
            return 0
        return None

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
        return 'CREATE TABLE %s (%s%s)%s' % (
            table_info.tblname,
            self.get_ddl_field_list(table_info, typeconvert, keywords),
            pkey, ld)

    def get_drop_ddl(self, tblname, last_delim = True):
        ld = last_delim and ';' or ''
        return 'DROP TABLE %s%s' % (tblname, ld)

    def get_ddl_field_list(self, table_info, typeconvert=None, keywords=()):
        r = []
        for field in table_info.fields:
            r.append(self.get_ddl_field_spec(table_info, field, typeconvert, keywords))
        return ', '.join(r)

    def get_primary_key(self, table_info):
        pk_fields = self.get_pk_fields(table_info)
        if pk_fields:
            return 'PRIMARY KEY (%s)' % (', '.join(pk_fields))
        return ''

    def get_pk_fields(self, table_info):
        return [field.fldname for field in table_info.fields if field.pk]

    def get_pk_defaults(self, table_info, force=False):
        if table_info.is_null_pk_allowed() and not force:
            return {}
        return dict([(field.fldname, self.get_ddl_default_value(field)) for field in table_info.fields if field.pk])

    def check_indexes(self, table_info, primary=False, just_check=False):
        r = True
        exist_indexes = self.get_index_set(table_info.tblname, primary)
        for index in table_info.indexes:
            if tuple(index) not in exist_indexes:
                r = False
                error = u'Таблица %s. Не найден индекс по полям %s. Требуется обновление.' % \
                         (table_info.tblname, ', '.join(index))
                self.errors.append(error)
                self.log(error)
                break
        if not r:
            if not just_check:
                return self.reindex_table(table_info, primary)
        return r

    def reindex_tablename(self, tblname, primary=False, si=None):
        si = si or get_struct_info()
        if tblname in si.tables:
            return self.reindex_table(si.tables[tblname], primary)
        return False

    def create_index(self, tblname, indexname, indexfields):
        return False

    def drop_index(self, tblname, indexname):
        return False

    def drop_index_all(self, tblname, primary=False):
        indexes = self.get_indexes(tblname, primary)
        for index in indexes:
            if not self.drop_index(tblname, index):
                return False
        return True

    def gen_index_name(self, tblname, ind):
        return 'FI_%s_%d' % (tblname, ind)

    def reindex_table(self, table_info, primary=False):
        if not self.check_exclusive():
            return False
        if not self.drop_index_all(table_info.tblname, primary):
            return False
        self.index_table(table_info)
        return True

    def index_table(self, table_info):
        self.log(u'Индексация таблицы %s' % (table_info.tblname))
        for ind, index in enumerate(table_info.indexes):
            if index:
                self.create_index(table_info.tblname,
                                  self.gen_index_name(table_info.tblname, ind),
                                  index
                                  )

    def exclusive_error(self):
        return ''

    def check_exclusive(self):
        while True:
            err = self.exclusive_error()
            if not err:
                break
            # здесь имеется ввиду self.cfg = aliasconfig
            errmsg = uformat(u'Внимание! База данных %s занята другими пользователями.\n%s', self.get_dbname(), err)
            if not system.confirm(errmsg + u'\nПовторить попытку', False):
                self.errors.append(errmsg)
                return False
        return True

    def get_dbname(self):
        return ''

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_rec_factory(self):
        return self.rec_factory


class sql_datamanager(DataManager):
    # кавычка для формирования имен полей из списка зарезирвированных
    QUOTE_STR = '"'
    # символы, запрещенные в строке для FTS поиска, для translate
    FTS_NOT_ALLOWED_CHARS = {}

    def recreate_table(self, tblname, si=None):
        # ToDo: неправильно пересоздает таблицы с автоинкрементов на основе последовательностей.
        # Надо сохранять последовательности и не создавать новые.
        from gtd.db import get_struct_info
        from gtd.db.dbstruct import struct_info
        si = si if si else get_struct_info()
        tbl = si.tables[tblname]
        new_si = struct_info()
        tmptblname = tblname + '_tmp'
        tmptbl = new_si.addtable(tmptblname)
        tmptbl.fields = tbl.fields
        for field in tmptbl.fields:
            field.required = False
        # Описание индексов не копируем в новую таблицу!
        # При переименовании таблицы имена индексов не меняются.
        #tmptbl.indexes = tbl.indexes
        old_rcount = self.locate(tblname)
        self.drop_table(tmptblname)
        if self.update_tables(tmptblname, new_si, reindex=False):
            columns = []
            columnnames = [column.lower() for column in self.get_column_names(tblname)]
            fieldnames = [column.lower() for column in tbl.fieldnames.keys()]
            for column in columnnames:
                if column in fieldnames:
                    columns.append(column)
            # Некоторые таблицы позволяют иметь Null значения в первичном ключе - например ТН ВЭД
            if not tbl.is_null_pk_allowed():
                # найти поля первичного ключа и с атрибутом required
                notnullfieldnames = [field.fldname.lower() for field in new_si.tables[tblname].fields if
                                 (field.fldname.lower() in columns) and (field.pk or field.required)]
                if notnullfieldnames:
                    cfn = 'C'
                    delnullwhere = ' OR '.join(['({0} IS NULL)'.format(notnullfieldname)
                                                for notnullfieldname in notnullfieldnames])
                    countnullsql = 'SELECT COUNT(*) AS {0} FROM {1} WHERE {2}'.format(cfn, tblname, delnullwhere)
                    delnullsql = 'DELETE FROM {0} WHERE {1}'.format(tblname, delnullwhere)
                    countrec = self.get_records(tblname, countnullsql)
                    delcount = int(countrec[0][cfn]) if countrec is not None else 0
                    if delcount > 0:
                        old_rcount -= delcount
                        self.dosql(tblname, delnullsql)
                        self.log(delnullsql)
                        self.log('В процессе пересоздания таблицы {0} удалено неправильных записей: {1}'.format(
                            tblname, delcount))
            new_field_names = columns[:]
            new_field_values = columns[:]
            # значения по умолчанию для первичного ключа
            pk_defaults = self.get_pk_defaults(tbl, force=True)
            if 'VERSION' in pk_defaults:
                pk_defaults['VERSION'] = 1
            params = self.init_params()
            for pk_field_name in pk_defaults:
                if pk_field_name.lower() not in new_field_names:
                    new_field_names.append(pk_field_name)
                    new_field_values.append(self.format_param_key(pk_field_name, pk_defaults[pk_field_name], params=params))
            sql = 'INSERT INTO %s (%s) SELECT %s FROM %s' % (
                tmptblname,
                self.get_field_list(new_field_names),
                self.get_field_list(new_field_values),
                tblname
            )
            try:
                new_rcount = self.dosql(tmptblname, sql, values=params, ti=tbl)
                if new_rcount == old_rcount:
                    self.drop_table(tblname)
                    # rename все равно не меняет ddl триггеров
                    self.drop_triggers_all(tmptblname)
                    self.dosql(tmptblname, 'ALTER TABLE %s RENAME TO %s' % (tmptblname, tblname))
                    # а вот теперь надо создать индексы в новой таблице
                    if self.update_tables(tblname, si, reindex=True, allow_triggers_on_reindex=True):
                        return True
                    else:
                        self.rollback()
                else:
                    self.rollback()
            except Exception, e:
                self.errors.append(e.message)
                self.rollback()
        return False

    def create_index(self, tblname, indexname, indexfields):
        sql = 'CREATE INDEX %s ON %s (%s)' % (indexname, tblname, ', '.join(
            [self.format_field_name(fieldname, tblname, True) for fieldname in indexfields]
        ))
        return self.dosql(tblname, sql)

    def drop_index(self, tblname, indexname):
        sql = 'DROP INDEX %s' % self.qw(indexname)
        # drop index возвращает всегда 0 ...
        self.dosql(tblname, sql)
        return True

    def drop_table(self, tblname, check_exist=True):
        """
         удаление таблицы и связанных с ней объектов
        """
        r = super(sql_datamanager, self).drop_table(tblname, check_exist)
        self.drop_ftsobjects_all(tblname)
        return r

    def parse_index_sql(self, sql):
        m = re.match(SQL_INDEX_PATTERN, sql)
        if m:
            fieldnames = m.groups()[1]
            r = []
            for fieldname in fieldnames.split(', '):
                if fieldname.startswith('"') or fieldname.startswith("'"):
                    r.append(fieldname[1:-1].lower())
                else:
                    r.append(fieldname.lower())
            return r
        return None

    def drop_ftsobjects_all(self, tblname):
        """
        Удалить все FTS объекты таблицы.
        Это могут быть индексы, триггера, функции и т.д.
        """
        return True

    def drop_triggers_all(self, tblname):
        return True

    def create_ftsobjects_all(self, tblname):
        """ Создать все FTS объекты таблицы """
        return True

    def reindex_table(self, table_info, primary=False):
        res = super(sql_datamanager, self).reindex_table(table_info, primary)
        if res:
            if not self.drop_ftsobjects_all(table_info.tblname):
                return False
            res = self.create_ftsobjects_all(table_info.tblname)
        return res

    @classmethod
    def parse_value_for_format_where_match(cls, value):
        """ Разобрать параметр со строками для FTS поиска """
        words_match = []
        words_like = []
        if isinstance(value, tuple):
            # words_match, words_like
            if len(value) > 1:
                words_match, words_like = value[:2]
            elif len(value) == 1:
                words_match = value[0]
        else:
            # если только один набор слов - то это слова для match.
            words_match = value

        words_like = words_like if isinstance(words_like, list) else \
            [words_like] if isinstance(words_like, basestring) else []
        if words_like:
            words_like = [to_ustr(onevalue).strip() for onevalue in words_like]

        words_match = words_match if isinstance(words_match, list) else \
            [words_match] if isinstance(words_match, basestring) else []
        # сразу уберем лишние символы и выкинем получившиеся пустые слова
        words_match = [to_ustr(onevalue).strip().lower() for onevalue in words_match]
        new_words_match = []
        for onevalue in words_match:
            newonevalue = onevalue.translate(cls.FTS_NOT_ALLOWED_CHARS).strip()
            if newonevalue != onevalue:
                # значение изменилось, добавим старое значение в список для like
                words_like.append(onevalue)
            if newonevalue:
                new_words_match.extend(newonevalue.split())
        return new_words_match, words_like


class QueryRecords(objects.baseobject):

    def beforeInit(self, data_manager, query, start = 0, limit = 0, fields = None, *args, **kwargs):
        """ fields = словарик с именем поля в качестве ключа и DataField в качестве значения """
        self.dm = data_manager
        self.query = query
        self.rec_n = 0
        self.qty = 0
        self.start = start
        self.limit = limit
        self.fields = fields
        self.locate_where = None
        # вызывается, когда данные получаются из базы данных
        self.on_calc_record = None
        # Фиксированные данные, добавляются в начало каждой выборки
        self.fixed_recs = []
        # модифицированные данные
        self.modified = {}
        self.verbose = True

    def fixed_offset(self):
        return len(self.fixed_recs)

    def __del__(self):
        self.close_query()

    def close_query(self):
        pass

    def __len__(self):
        pass

    def __iter__(self):
        pass

    def next(self):
        pass

    def __getitem__(self, key):
        if isinstance(key, int):
            self.start = key
            self.limit = 1
            for r in self:
                self.start = 0
                self.limit = 0
                return r
        elif isinstance(key, slice):
            self.start = key.start or 0
            if key.stop:
                self.limit = key.stop - self.start
            else:
                self.limit = 0
            rs = []
            for r in self:
                rs.append(r)
            self.start = 0
            self.limit = 0
            return rs
        else:
            return None

    def get_rec_number(self, rec_where):
        r = 0
        self.start = 0
        self.limit = 0
        rec_found = False
        for rec in self:
            rec_found = True
            for key in rec_where:
                if key in rec and rec[key] != rec_where[key]:
                    rec_found = False
                    break
            if rec_found:
                break
            r += 1
        if rec_found:
            return r
        else:
            return -1

    def do_calc_record(self, rec):
        if self.on_calc_record:
            self.on_calc_record(rec)

    def update_modified(self, idx, values):
        modified = self.modified.setdefault(idx, {})
        modified.update(values)

    def merge_modified(self, rec):
        modified = self.modified.get(self.rec_n)
        if modified:
            rec.update(modified)
            return True
        return False


def test_where_clause(where):
    return DataManager().get_where_clause(where)


def test_where():
    from gtd.soap.messagetime import minus_month_time
    where = ({'APP_ID' : 1, '!STATUS' : ('1', '2', '3'), '>DMODIFY' : minus_month_time()}, )
    print test_where_clause(where)


def test_where_2():
    """ тестирование выражений вида {'^DOCCODE' : {'}' : gr_doc, '<' : '%-2.2d' % (int(gr_doc) + 1)}}"""
    gr_doc = '01'
    print test_where_clause(
        {'`DOCCODE' :
            {'}' : gr_doc,
            '<' : '%-2.2d' % (int(gr_doc) + 1)
            }})


def test_where_not_with_or():
    """ надо сформировать что-то типа ((CS <> 7) or (CS is Null)) and (app_id = 1) and (nd = '???') """
    dm = DataManager()
    #(({'!CS' : 7}), ({'CS' : None}), ({'APP_ID' : 1, 'ND' : '???'})) \
    print dm.get_where_clause(
        {'APP_ID' : 1, 'ND' : '???', 'CS' : {'!' : 7, '' : None}}
    )


def test_unicode_params():
    """ Ошибка происходит из-за того,
    что в строку форматирования попадают unicode имена полей
    она сама становится unicode и тут сверху еще русская строчка в ascii
    """
    key = {'ND' : u'12345678/121314/ББ12345'}
    values = {u'STATUS' : 'Б'}
    print DataManager().get_update_clause('eds_ids', values, key)


def test(n):
    if n in (0, 99):
        return test_where()
    elif n in (1, 99):
        return test_where_not_with_or()


def test_table_names():
    dm = DataManager()
    dm.select_name_in_quotes = True
    dm.sql_table_ext = '.db'
    print dm.get_table_names(['DECL.DBF', 'DECL_REG'])
    print dm.get_table_names('DDDDDD')
    print dm.get_table_names('tttt.dbf')


def test_error():
    # если передать в качестве условия пустой tuple - возникает ошибка, т.к. в join(a) передается None вместо строки
    print DataManager().get_select_clause('docs', ('field1', ), {'DOCTYPE': (), 'ND': '???'})


def test_where_and():
    print DataManager().get_where_clause({'ARCHDECLID': (None, 'XXX')})


def test_match():
    print DataManager().get_where_clause({'~TEXT': ['xxx*', 'yyy*', 'zzz*']})
    print DataManager().get_where_clause({'~TEXT': u'фывxxx* yyy* zzz*'})


def test_bool():
    print DataManager().get_where_clause({'ISKTS': True})


def test_null():
    print DataManager().get_where_clause(
        {'ND': 'XXXX',
         'G44INDMARK': {'!': 0, '': None}})


def test_g32():
    print DataManager().get_where_clause(
        [{'`G32': {'}': 1, '{': 5},}, {'G32': 1}]
    )


def test_g32_complex():
    print DataManager().get_where_clause(
        (
            {'ND':'XXX',
             'G441': '99999',
            },
            [{'`G32': {'}': 1, '{': 5},}, {'G32': 1}]
        )
    )


if __name__ == "__main__":
    # test_where_2()
    # test_table_names()
    # test_error()
    # test_match()
    # test_bool()
    # test_null()
    # test_g32()
    test_g32_complex()
