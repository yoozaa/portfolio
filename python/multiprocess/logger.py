# -*- coding: cp1251 -*-

import sys, os, time
from gtd.paths import *
from gtd.mutex import *
from tks.objects import singleton


LOG_INFO = 'INFO'
LOG_WARNING = 'WARN'
LOG_ERROR = 'ERROR'
LOG_CRITICAL = 'CRITICAL'
LOG_DEBUG = 'DEBUG'
LOG_DEBUG1 = 'DEBUG1'
LOG_DEBUG2 = 'DEBUG2'
LOG_DEBUG3 = 'DEBUG3'

LOG_NAME = 'logger'
LOG_PATH = 'log'
LOG_FILENAME = '%s_%s.log'

MAIN_PROCESS_NAME = 'main'


def write_log(message, message_type=LOG_INFO):
    return Log().write(message, message_type)


class Log(singleton):

    def init_properties(self):
        self.encoding = 'cp1251'
        self.path_manager = path_manager()
        self.path_manager[LOG_NAME] = self.path_manager.join(LOG_PATH, True)
        create_directory(self.path_manager[LOG_NAME])
        self.filename = os.path.join(self.path_manager[LOG_NAME], self.get_filename())
        self.LogObject = None
        self.LogTimeStamp = True
        self.initialized = True
        self._pid = 0
        self.process_name = MAIN_PROCESS_NAME

    @locking(LOCK_LOG)
    def emptyline(self, count = 1):
        try:
            self.LogObject = open(self.filename, 'a+')
            for i in range(count):
                self.LogObject.write('\n')
            self.LogObject.close()
        except (AttributeError, IOError):
            pass
        return True

    @staticmethod
    def get_filename():
        return LOG_FILENAME % (
            os.environ.get('TKSAPPINFO_NAME', '').lower() or 'wingtd',
            time.strftime('%Y%m%d')
        )

    @property
    def pid(self):
        if not self._pid:
            self._pid = os.getpid()
        return self._pid

    def timestamp(self):
        r = ''
        if self.LogTimeStamp:
            r = '%s.%s' % (time.strftime('%Y-%m-%d %H:%M:%S'), str(time.clock() % 1)[2:7])
        return r

    @locking(LOCK_LOG)
    def write(self, message, message_type=LOG_INFO):
        try:
            self.LogObject = open(self.filename, 'a+')
            if isinstance(message, unicode):
                message = message.encode(self.encoding, errors='replace')

            s = "%s\t%s\t%s\t%s\t%s\n" % (message_type, self.timestamp(), self.process_name, self.pid, message)
            self.LogObject.write(s)
            self.LogObject.close()
        except (AttributeError, IOError):
            pass

        return True

    @locking(LOCK_LOG)
    def touch(self):
        with open(self.filename, 'a+'):
            os.utime(self.filename, None)


if __name__ == "__main__":

    import gtd
    log1 = Log()
    log1.write('message 1')
    log2 = Log()
    log2.write('message 2')
