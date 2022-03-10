# -*- coding: cp1251 -*-

"""
    менеджер для подключения к MySQL через ODBC
"""

from odbc import ODBCManager
from dbconsts import *


DSN_ANSI = "DRIVER=MySQL ODBC 5.3 Ansi Driver;SERVER=%s;DATABASE=%s;UID=%s;PWD=%s"
DSN_UNICODE = "DRIVER=MySQL ODBC 5.3 Unicode Driver;SERVER=%s;DATABASE=%s;UID=%s;PWD=%s"
DSN_OLD = "DRIVER=MySQL ODBC 3.51 Driver;SERVER=%s;DATABASE=%s;UID=%s;PWD=%s"


class myodbc_manager(ODBCManager):

    def get_connection_string(self, dbpath):
        return DSN_UNICODE % (
            self.cfg[PARAM_PG_SERVERNAME],
            self.cfg[PARAM_PG_SERVERDBNAME],
            self.cfg[PARAM_PG_USERNAME],
            self.cfg[PARAM_PG_USERPASS]
        )

    def get_databasename(self, tblname, dbname='', *args, **kwargs):
        return ''

