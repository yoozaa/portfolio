# -*- coding: cp1251 -*-

"""
Блокировки ресурсов


LocksDic - глобальный словарик ресурсов, имена разделяемых ресурсов берутся
из списков ProcessManager.locking_resources или Job.locking_resources (для процессов одного типа)



Использование

from gtd.mutex import *


@locking(LOCK_DB)
def exec_sql(self, *args):
    pass

def dummy_function(self, *args):
    ...
    with LockBlock(LOCK_FILES):
        self.write_to_files(data)
    ...

"""

import multiprocessing as processing

from tks.objects import singledict

LOCK_DB_PDOX = 'global.db.pdox'
LOCK_DB_SQLITE = 'global.db.sqlite'
LOCK_DB_SQLITE_DATA = 'global.db.sqlite.data'
LOCK_DB_SQLITE_EXPRESS = 'global.db.sqlite.express'


LOCK_LOG = 'global.log'
LOCK_SYNC = 'global.sync'
LOCK_FILE = 'global.file'

LOCK_SOAP_OUTGOING = 'smtp.files'
LOCK_SOAP_OUTGOING_CFG = 'smtp.cfg'
LOCK_SOAP_OUTGOING_DELAYED = 'smtp.delayed'
LOCK_SOAP_INCOMING = 'pop3.files'
LOCK_SOAP_COPY = 'ford.files'
LOCK_MPS_OUTGOING = 'mps.files'
LOCK_RELAY_FILES = 'relay.files'
LOCK_RSS_FILES = 'rss.files'


class LazyLock(object):
    """
    Объект, позволяющий избегать deadlock в рамках одного процесса
    name - имя блокируемого ресурса для удобства отладки
    """
    def __init__(self, name):
        self.name = name
        self.locked = False
        self._lock = processing.Lock()

    def acquire(self):
        if not self.locked:
            self._lock.acquire()
            self.locked = True
            return True
        return False

    def release(self, acquired=True):
        if acquired and self.locked:
            self._lock.release()
            self.locked = False

    def unlock(self):
        try:
            self.locked = False
            self._lock.release()
        except Exception as e:
            pass


class LocksDic(singledict):
    """
    Глобальный словарик блокировок
    'Имя ресурса': LazyLock('Имя ресурса')
    """
    pass


def locking(resource):
    """
    Декоратор для блокировки функции или метода
    """
    def decorator(func):
        def func_proxy(*args, **kwargs):
            lock = LocksDic().get(resource)
            acquired = False
            if lock:
                acquired = lock.acquire()
            try:
                return func(*args, **kwargs)
            finally:
                if lock:
                    lock.release(acquired)
        return func_proxy
    return decorator


class LockBlock(object):
    def __init__(self, resource):
        self.lock = LocksDic().get(resource)
        self.acquired = False

    def __enter__(self):
        if self.lock:
            self.acquired = self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock:
            self.lock.release(self.acquired)

