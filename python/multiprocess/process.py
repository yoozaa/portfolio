# -*- coding: cp1251 -*-

from Queue import Empty
from eventtypes import *
from gtd.eventtypes import EVENT_STOPSERVER
from multiprocessing import forking, active_children
from mutex import *
from tks import objects
from tks.strutils import get_str
import events
import logger
import os
import paths
import sys
import time
try:
    import tkssync
except ImportError:
    class tkssync:

        @classmethod
        def isWindow(cls, hwindow):
            return False

        @classmethod
        def sync_message(cls, hWindow, param, command):
            return 0

        @classmethod
        def RunningProcessesList(cls):
            return []


import traceback
import weakref

SIGNAL_STOP = 'STOP'
SIGNAL_NOTHING = "NOTHING"
SIGNAL_NOOP = "NOOP"
SIGNAL_PYCHARM_DEBUG = 'PYCHARM_DEBUG'
SIGNAL_PYCHARM_DEBUG_STOP = 'PYCHARM_DEBUG_STOP'

I_CLOSE_DEFAULT = 0
I_CLOSE_NOT = 1
I_CLOSE_NO_MESSAGE = 2


def format_log_entry(procname, message):
    return '\t'.join((procname, message))


def get_private_dir(appname='wingtd'):
    return '%s\\%s\\private' % (os.environ['APPDATA'], os.environ.get('TKSAPPINFO_NAME') or appname)


def format_background(bkname, pid):
    return '__import__("gtd.process", globals(), locals(), "process")' + \
           '.ProcessManager().remove_background("{}", {})'.format(bkname, pid)


def format_background_error(bkname, pid, error_message):
    return '__import__("gtd.process", globals(), locals(), "process")' + \
           '.ProcessManager().remove_background("{}", {}, {})'.format(bkname, pid, repr(error_message))


def run_job(job, cfg_cached, **kwargs):
    from gtd.config import configdata
    cfgdata = configdata()
    cfgdata.data_cache = cfg_cached
    cfgdata.cached_read = True
    map(lambda key: setattr(job, key, kwargs[key]), kwargs.iterkeys())
    working_dir = '%s\\%s' % (get_private_dir(), os.getpid())
    paths.create_directory(working_dir)
    os.chdir(working_dir)
    try:
        if job.background:
            job.serve_once()
        else:
            job.serve_forever()
    finally:
        exit(0)


class Job(objects.baseobject):
    verbose = False

    def beforeInit(self, *args, **kwargs):
        self.name = 'unnamed process'
        self.caption = ''
        self.console_output = sys.executable.find('console') != -1
        self.interval = 3.0
        self.queue = None
        self.state = SIGNAL_NOTHING
        # имена блокировок для текущего типа (self.name) процессов
        self.locking_resources = []
        self.hWindow = 0
        self.logger = logger.Log()
        # Словарик настроек c ключами из get_config_keys
        self.cfg = {}
        self.pid = 0
        self.test_mode = False
        self.background = False
        self.resultqueue = None
        self.init_properties()

    def init_properties(self):
        pass

    @classmethod
    def get_config_keys(cls):
        return ()

    def write_file(self, filename, data, cfg_data=None, locking_resource=LOCK_FILE):
        with LockBlock(locking_resource):
            with open(filename, 'w') as f:
                f.write(data)
            if cfg_data:
                with open(os.path.splitext(filename)[0] + '.cfg', 'w') as f:
                    f.write(cfg_data)

    def console_info(self, s):
        if isinstance(s, unicode):
            print s
        else:
            print unicode(s, 'cp1251').encode('cp866')

    def info(self, s, message_type=logger.LOG_INFO):
        self.logger.write(s, message_type)
        return s

    def warning(self, s):
        self.info(s, logger.LOG_WARNING)

    def error(self, s):
        if s:
            self.info(s, logger.LOG_ERROR)

    def exception(self, e, point='', with_trace=True):
        if with_trace and isinstance(e, Exception):
            self.error('\n' + traceback.format_exc())
        else:
            self.error('%s %s' % (point, e))

    def debug(self):
        from gtd.modules.debug import pycharm_debug
        pycharm_debug.start()

    def debug_stop(self):
        from gtd.modules.debug import pycharm_debug
        pycharm_debug.stop()

    def serve_once(self):
        try:
            self.logger.process_name = self.name
            self.pid = os.getpid()
            r = self.process()
            if self.resultqueue:
                self.resultqueue.put(r, True, 0.1)
                # sleep нужен, потому что если сразу прочитать данные, то там может оказаться пусто.
                time.sleep(0.1)
            self.synchronize(0, format_background(self.name, self.pid))
        except Exception, e:
            self.synchronize(0, format_background_error(self.name, self.pid, repr(e)))
            self.exception(e, 'process')

    def serve_forever(self):
        if not self.check_config():
            return
        self.start()
        while not self.terminate():
            try:
                if self.state != SIGNAL_NOOP:
                    if self.state == SIGNAL_PYCHARM_DEBUG:
                        self.debug()
                    elif self.state == SIGNAL_PYCHARM_DEBUG_STOP:
                        self.debug_stop()
                    else:
                        self.process()
            except Exception, e:
                self.exception(e, 'process')

            try:
                self.state = self.queue.get(True, self.interval)
            except Empty:
                self.state = SIGNAL_NOTHING
                continue
            except Exception, e:
                self.state = SIGNAL_NOTHING
                self.exception(e, 'queue state', True)
        self.stop()

    def terminate(self):
        return (self.state == SIGNAL_STOP) or not self.isAlive()

    def process(self):
        pass

    def check_config(self):
        return True

    def start(self):
        try:
            self.logger.process_name = self.name
            self.logger._pid = self.pid = os.getpid()
            self.init_start()
            self.info('Запущена служба {i.name}'.format(i=self))
        except Exception, e:
            self.exception(e, 'start')
            self.state = SIGNAL_STOP

    def stop(self):
        try:
            self.init_stop()
        except Exception, e:
            self.exception(e, 'end')
        self.info('Остановлена служба %s' % (self.name))

    def release_locks(self):
        for resource in self.locking_resources:
            lock = LocksDic().get(resource)
            if lock:
                lock.unlock()

    def init_start(self):
        pass

    def init_stop(self):
        pass

    def isAlive(self):
        return not self.hWindow or tkssync.isWindow(self.hWindow)

    @locking(LOCK_SYNC)
    def synchronize(self, param, command):
        try:
            r = tkssync.sync_message(self.hWindow, param, command)
            if r and isinstance(r, basestring):
                self.error(r)
        except Exception, e:
            self.exception(e, 'synchronize')

    def run(self):
        pm = ProcessManager()
        pi = pm.processlist.get_info(self.name)
        if pi:
            from gtd import system
            system.warning('Внимание! Процесс "{}" уже запущен. Для повторного запуска дождитесь его завершения.'.format(self.name))
            return False
        else:
            return pm.run_job(self, self.name, {}, {})

    def get_result(self, on_done, result, error_result):
        try:
            try:
                pm = ProcessManager()
                pm.processlist.remove_process_name(self.name)
                pm.run_job(self, self.name, {}, {}, result=processing.Queue(), on_done=on_done, error_result=error_result)
            except:
                if on_done and callable(on_done):
                    on_done(result)
        finally:
            return result

    def popup_message(self, text, title='', caption=''):
        from gtd.msg import sync_notify_message
        sync_notify_message(self.hWindow, content=text, title=title, caption='Уведомление')



class BackgroundJob(Job):
    """Процесс, который может выполняться в фоне"""
    def beforeInit(self, *args, **kwargs):
        super(BackgroundJob, self).beforeInit(*args, **kwargs)
        self.background = True
        self.name = self.__class__.__name__


# windows errors
# file not found
FILENOTFOUND = 2


class ProcessInfo(object):
    def __init__(self, job, process, result=None, on_done=None, error_result=None):
        self.job = job
        self.process = process
        self.result = result
        self.on_done = on_done
        self.error_result = error_result
        self.done = False


class ProcessList(object):
    def __init__(self):
        self.processes = []

    def append_process(self, job, process, result=None, on_done=None, error_result=None):
        self.processes.append(ProcessInfo(job, process, result, on_done, error_result))
        return process

    def remove_process(self, job):
        for index, pi in enumerate(self.processes):
            if pi.job.name == job.name:
                del self.processes[index]
                break

    def remove_process_name(self, jobname, pid=None):
        """
        Удаляет процесс по
        1. jobname - при создании нового задания
        2. jobname+pid - при получении результата от BackgroundJob,
                         чтобы удалять только при получении результата от последнего
                         запущенного задания с именем jobname
        """
        for index, pi in enumerate(self.processes):
            if (pi.job.name == jobname) and ((pid is None) or (pid == pi.process.pid)):
                del self.processes[index]
                return True
        return False

    def get_info(self, jobname):
        r = None
        for pi in self.processes:
            if pi.job.name == jobname:
                r = pi
                break
        return r

    def background_exists(self):
        for pi in self.processes:
            if pi.job.background and pi.process.is_alive():
                return True
        return False

    def background_terminate(self):
        to_remove = []
        for idx, pi in enumerate(self.processes):
            if pi.job.background and (pi.process.is_alive() or pi.done):
                pi.job.release_locks()
                pi.process.terminate()
                to_remove.append(idx)
        # удаления после принудительной остановки при заходе в настройки
        for idx in to_remove:
            del self.processes[idx]

        return len(to_remove)


class ProcessManager(object):
    obj = None
    PROCESS_RUNNER = 'tksrunner.exe'

    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = object.__new__(cls)
            cls.obj.init_properties(*args, **kwargs)
        return cls.obj

    def init_properties(self, *args, **kwargs):
        base_path = __file__
        for i in range(3):
            base_path = os.path.split(base_path)[0]
        # self.set_executable(base_path)
        self.in_program = False
        self._force_terminate = False
        self.queues = {}
        # глобальный словарь блокировок
        self.locks = LocksDic()
        # имена блокирумых ресурсов
        self.locking_resources = [LOCK_DB_PDOX, LOCK_DB_SQLITE, LOCK_DB_SQLITE_DATA, LOCK_DB_SQLITE_EXPRESS,
                                  LOCK_LOG, LOCK_SYNC, LOCK_RELAY_FILES, LOCK_FILE]
        self.init_locks(self.locking_resources)
        self.mutex = processing.Lock()
        self.jobs = {}
        self.running = False
        self.hWindow = 0
        self.logger = logger.Log()
        self.globals = {}
        self.processlist = ProcessList()
        events.subscribe_event(EVENT_STOPSERVER, self.stopserver)
        events.subscribe_event(EVENT_STOPPROCESSING, self.stopprocessing)
        events.subscribe_event(EVENT_STARTPROCESSING, self.startprocessing)
        events.subscribe_event('start_jobs', self.startprocessing)
        events.subscribe_event('stop_jobs', self.stopprocessing)
        pths = list()
        pths.append(os.path.join(base_path, 'python27.zip'))
        pths.append(os.path.join(base_path, 'lib27'))
        pths.append(os.path.join(base_path, 'DLLs'))
        pths.append(os.path.join(base_path, 'plib'))
        pths.append(os.path.join(base_path, 'pydebug'))
        os.environ['PYTHONPATH'] = ';'.join(pths)
        map(lambda key: setattr(self, key, kwargs[key]), kwargs.keys())

    def init_locks(self, resources):
        for resource in resources:
            self.locks[resource] = LazyLock(resource)

    def set_executable(self, base_path):
        forking.set_executable(os.path.join(base_path, self.PROCESS_RUNNER))

    def set_global(self, key, obj):
        self.globals[key] = weakref.ref(obj)

    def get_global(self, key):
        obj_ref = self.globals.get(key)
        if obj_ref:
            return obj_ref()
        return None

    def remove_directory(self, d):
        for name in os.listdir(d):
            f = os.path.join(d, name)
            if os.path.isdir(f):
                self.remove_directory(f)
            else:
                os.remove(f)
        os.rmdir(d)
        return

    def clear_private_dir(self):
        p_dir = get_private_dir()
        if not os.path.exists(p_dir):
            return
        d_list = os.listdir(p_dir)
        p_list = tkssync.RunningProcessesList()
        for d in d_list:
            remove = True
            try:
                remove = int(d) not in p_list
            except ValueError:
                pass
            if remove:
                self.remove_directory(os.path.join(p_dir, d))

    def create_queue(self, job_name):
        q = processing.Queue()
        self.queues[job_name] = q
        return q

    def run_job(self, job, name, cfg_data, cfg_cached, result=None, on_done=None, error_result=None):

        if name in [
            # "relay",
            # "smtp",
            # "pop3",
            # "http",
            "ford",
            # "rss",
            # "lserver"
        ]:
            return
        remove = False
        try:
            try:
                new_resources = filter(lambda r: r not in self.locks, job.locking_resources)
                self.init_locks(new_resources)
                self.processlist.append_process(job, processing.Process(
                    target=run_job,
                    args=(job, cfg_cached),
                    kwargs=dict(name=name,
                                queue=self.create_queue(name),
                                locks=self.locks,
                                hWindow=self.hWindow,
                                cfg=cfg_data,
                                resultqueue=result)
                ), result=result, on_done=on_done, error_result=error_result).start()
                if job.background:
                    self.update_background_gui()
            except WindowsError, e:
                remove = True
                if e.errno == FILENOTFOUND:
                    self.error('Сервис %s не запущен. Не найден файл: %s' % (name, e.filename))
                else:
                    self.exception(e)
            except Exception, e:
                remove = True
                raise e
        finally:
            if remove:
                self.processlist.remove_process(job)

    def stop_job(self, job_name):
        self.signal(SIGNAL_STOP, job_name)
        if job_name in self.queues:
            del self.queues[job_name]

    def stopserver(self, e_name, e_data, *args, **kwargs):
        self.stop()
        return True

    def register_job(self, job_name, cls):
        if job_name not in self.jobs:
            self.jobs[job_name] = cls

    def start_job(self, job_name, cfg=None):
        if job_name not in self.jobs:
            self.error('Служба %s не зарегистрирована' % job_name)
            return
        if cfg is None:
            from gtd.config import configdata
            cfg = configdata()
        try:
            cfg_data = {}
            current_profile = cfg.get_current_profile()
            for key in self.jobs[job_name].get_config_keys():
                cfg_data[key] = cfg.get(key, current_profile)
            self.run_job(self.jobs[job_name](), job_name, cfg_data, cfg.data_cache)
        except Exception, e:
            self.exception(e, 'Ошибка запуска %s.' % (job_name))

    def signal(self, signal, job_name=None):
        if job_name is None:
            for jn in self.queues:
                self.queues[jn].put(signal, signal==SIGNAL_STOP)
        elif job_name in self.queues:
            self.queues[job_name].put(signal, False)
        time.sleep(0.5)
        return True

    def children_running(self, param=None):
        return len(active_children()) != 0

    def force_terminate(self, param=None):
        self._force_terminate = True

    def release_locks(self):
        for lock in self.locks.itervalues():
            lock.unlock()

    def wait_child(self):
        from subprocess import call
        from gtd.html.waiting import waiting_html_document
        try:
            waiting_html_document().waitfor(self.children_running, self.force_terminate, None)
        except Exception as e:
            self.exception(e)
            self._force_terminate = True

        if self._force_terminate:
            for p in active_children():
                p.terminate()
            # если terminate не помог
            for p in active_children():
                self.info('taskkill /pid {}'.format(p.pid))
                call(['taskkill', '/pid', str(p.pid)], shell=True)

        # разблокировка ресурсов
        self.release_locks()

    def stop(self):
        if self.running:
            if not self.signal(SIGNAL_STOP):
                return False
            self.queues = {}
            self.processlist.background_terminate()
            self.update_background_gui()
            self.running = self.children_running()
            if self.running:
                self.wait_child()
                self.running = False
        return not self.running

    def start(self):
        from gtd.config import configdata
        self.clear_private_dir()
        cfg = configdata()
        if not self.running:
            for job_name in self.jobs.keys():
                self.start_job(job_name, cfg)
            self.running = True
        return self.running

    def stopprocessing(self, e_name, e_data, *args, **kwargs):
        return self.stop()

    def startprocessing(self, e_name, e_data, *args, **kwargs):
        return self.start()

    def info(self, s, message_type=logger.LOG_INFO):
        self.logger.write(s, message_type)
        return s

    def emptyline(self, count=1):
        self.logger.emptyline(count)

    def error(self, s):
        self.info(s, logger.LOG_ERROR)

    def exception(self, e, point='', with_trace=True):
        if with_trace and isinstance(e, Exception):
            self.error('\n' + traceback.format_exc())
        else:
            self.error('%s %s' % (point, e))

    def write(self, filename, data, messagetype='', locking_resource=LOCK_FILE):
        with LockBlock(locking_resource):
            with open(filename, 'w') as f:
                f.write(data)
        s = ''
        if messagetype:
            s = '(%s) ' % (messagetype, )
        # Для того, чтобы можно было разобраться в порядке создания файлов
        # time.sleep(1)
        self.info('main_process - %s%s записан в очередь' % (s, os.path.basename(filename)))

    def background_jobs_running(self):
        return self.processlist.background_exists()

    def update_background_gui(self):
        if self.in_program:
            from gtd.html.statusbar import statusbar_manager
            sb = statusbar_manager().get_bar()
            if sb:
                if self.background_jobs_running():
                    sb.query('#background').set_style_attr('visibility', 'visible')
                else:
                    sb.query('#background').set_style_attr('visibility', 'collapse')

    def remove_background(self, bkname, pid, error_message=None):
        try:
            pi = self.processlist.get_info(bkname)
            if pi:
                if pi.process.pid == pid:
                    pi.done = True
                    if pi.on_done and callable(pi.on_done):
                        if not error_message:
                            try:
                                data = pi.result.get(True, 0.11)
                            except Empty:
                                data = pi.error_result
                        else:
                            self.error('remove_background. {} error - {}'.format(bkname, get_str(error_message)))
                            data = pi.error_result
                        pi.on_done(data)
                else:
                    # Имя задания совпало, а pid нет, значит завершилось задание, которое нам уже не интересно
                    pass
        finally:
            # удалим только то задание, результатов которого мы ждем (по jobname+pid)
            if self.processlist.remove_process_name(bkname, pid=pid):
                self.update_background_gui()

    def can_close(self):
        """ Проверка возможности закрыть программу
        """
        if self.background_jobs_running():
            from gtd import system
            if system.confirm('Внимание! Запущены фоновые процессы.\n' +
                    'В случае закрытия программы, возможна потеря данных.\n' +
                    'Вы уверены, что хотите закрыть программу'):
                self.processlist.background_terminate()
                return I_CLOSE_NO_MESSAGE
            else:
                return I_CLOSE_NOT
        return I_CLOSE_DEFAULT


def test():
    pass


if __name__ == "__main__":
    test()
