# -*- coding: cp1251 -*-

"""
    Менеджер для доступа к mysql базам
"""

from manager import *
from dbconsts import *
import pymysql


class mysql_manager(sql_datamanager):

    def beforeInit(self, cfg=None, *args, **kwargs):
        super(mysql_manager, self).beforeInit(cfg, *args, **kwargs)
        self.conn = None
        self.db_type = DB_MYSQL
        self.params_list = []
        self.lower_tablename = True

    def afterInit(self, *args, **kwargs):
        super(mysql_manager, self).afterInit(*args, **kwargs)
        if self.conn is None and self.auto_connect:
            self.connect()

    def __del__(self):
        self.disconnect()

    def get_table_name(self, tblname, select_expr=False, required_quotes=False):
        r = super(mysql_manager, self).get_table_name(tblname, select_expr, required_quotes)
        if self.lower_tablename:
            r = r.lower()
        return r

    def connect(self, just_test=False, *args, **kwargs):
        try:
            self.conn = pymysql.connect(
                user=self.cfg[PARAM_PG_USERNAME],
                password=self.cfg[PARAM_PG_USERPASS],
                host=self.cfg[PARAM_PG_SERVERNAME],
                port=self.cfg[PARAM_PG_SERVERPORT],
                database=self.cfg[PARAM_PG_SERVERDBNAME],
                cursorclass = pymysql.cursors.DictCursor
            )
        except Exception, e:
            self.log('connection failed')
            if just_test:
                return self.format_error(e)
            self.show_error(e, 'msql connect')

    def disconnect(self, *args, **kwargs):
        super(mysql_manager, self).disconnect(*args, **kwargs)
        if self.conn is not None:
            try:
                self.conn.close()
            except pymysql.err.Error:
                # already closed
                pass
            self.conn = None

    def cursor(self, *args, **kwargs):
        return self.conn.cursor(*args, **kwargs)

    def create_query(self, tblname, enable_cache=True):
        if self.conn:
            return mysql_query(self.conn.cursor(), enable_cache)
        raise EConnectionError('no connection object')

    def roolback(self):
        pass

    def format_param_key(self, key, value, fields=None, params=None, from_where=False, allow_adapt=True):
        self.params_list.append(value)
        #return '?'
        return '%s'

    def init_params(self):
        self.params_list = []
        return super(mysql_manager, self).init_params()

    def dosql(self, tblname, sql, values=None, fields=None, ti=None, *args, **kwargs):
        r = 0
        q = self.create_query(tblname)
        try:
            try:
                q.SQL = [sql, ]
                q.params = [p for p in self.params_list]
                q.ExecSQL()
                if q.cursor.rowcount <= 0:
                    return 0
                else:
                    r = q.cursor.rowcount
                    self.conn.commit()
                    return r
            except Exception, e:
                self.log_whereami(e, tblname, sql)
                self.show_error(e, sql)
                if self.raise_error:
                    raise
                return 0
        finally:
            del q

    def get_records(self, tblname, sql, where=None, start=0, limit=0, count_sql=None, serverside=False, *args, **kwargs):
        q = self.create_query(tblname, not serverside)
        try:
            q.SQL = [sql, ]
            if limit:
                q.SQL.append(' LIMIT %d' % limit)
            if start > 0:
                q.SQL.append(' OFFSET %d' % start)
            q.params = [p for p in self.params_list]
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
        return sqlite_records(self, q, 0, 0, *args, **kwargs)



class mysql_query(object):
    """ используется для queryrecords """
    def __init__(self, cursor, *args, **kwargs):
        self.cursor = cursor
        self.SQL = []
        self.params = None
        self.active = False
        self.rcount = -1

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

    def fetch(self, idx):
        return self.cursor.fetchone()


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
        if 0 < self.limit == self.qty:
            raise StopIteration
        else:
            if not self.query:
                raise StopIteration
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




