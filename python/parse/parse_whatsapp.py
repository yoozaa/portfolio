# -*- coding: utf-8 -*-

"""
    кликер для контейнера whatsapp
"""

import pyautogui, time, pyperclip, requests, os, urllib, ssl
from sync import get_window_pos, set_window_size, mouse_click, get_window_text, paste, tofront
import datetime
import time
import re
import io
import json
import ruamel.yaml as yaml
from whatsapp.outbox import outbox_manager
from wappcommon import logger
from wappcommon import objects
from wappcommon import paths
from whatsapp.consts import FILESTORAGE
from wappcommon.strutils import utuple, filename_replace
from db.data import sqlt_get_data
import random
import inspect
import sys

from requests.packages.urllib3.util.retry import Retry
from requests.packages.urllib3 import PoolManager

retry = Retry(backoff_factor=0.5, total=3)
req = PoolManager(retries=retry)

pyautogui.FAILSAFE = False
ssl._create_default_https_context = ssl._create_unverified_context

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
# Теги комментариев                                          #
# #A - обрати внимание, может быть нарушение работы кликера  #
# #R - требуется рефакторинг                                 #
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #

# test

__version__ = 300

PARAM1_PYTHONCOMMAND = 1
# Асинхронный вызов JS
PARAM1_JSCOMMAND_ASYNC = 2
# Синхронный вызов JS, т.е. Python ожидает возврата значения из JS-модуля
PARAM1_JSCOMMAND_SYNC = 3
PARAM1_SETFILENAME = 4
PARAM1_JSPROC_SYNC = 5
# Установка имени файла в document_info
PARAM1_SETFILENAME2 = 6

PASTE_SELECTAFTER = 1

# Obychnoe polojenie polya vvoda
y = 155

# Click na dialoge chtoby sbit fokus
POINT_9 = [50, 640]

# расширения видеофайлов - для отправки как видео, а не как документ
VIDEO_EXT = ['.mp4']

class EDeadContainer(Exception):
    pass


def dict_to_str(d=None):
    ''''''
    if not d:
        return ''
    s = '{'
    for k, v in d.items():
        if not isinstance(v, unicode):
            tmp_v = str(v)
        else:
            tmp_v = unicode(v)
        s += unicode(k) + ': ' + tmp_v + ', '
    s = s[:-2] + '}'
    return s.encode('utf-8')


def to_str(string):
    if not isinstance(string, unicode):
        return str(string)
    return unicode(string).encode('utf-8')


def raw_log_print(*args):
    try:
        called_from = 'from func: {} / {} /line {}/ '.format(
            inspect.stack()[2][3],
            inspect.stack()[1][3],
            inspect.stack()[2][2]
        )
        for i in args:
            if isinstance(i, dict):
                called_from += ' ' + dict_to_str(i)
            else:
                called_from += ' ' + str(i)
        logger.Log().write(called_from, encoding='utf-8')
    except Exception as err:
        logger.Log().write('Logger exception {}'.format(str(err)))


def log_print(*args):
    """ отладочные сообщения в лог """
    stack = []
    try:
        for i in inspect.stack()[1:-1]:
            if i[1].split('\\')[-1] == 'sender2.py':
                stack.append({'line': i[2], 'f_name': i[3]})
        n = len(stack)
        template = 'from func: ' + '{}/' * n
        print n
        called_from = template
        called_from = called_from.format(
            *list(map(lambda x: ' - '.join(
                list(map(lambda y: str(y), x.values()[::-1]))), stack[::-1])))
        logger.Log().write(called_from + u' -> ' + u' '.join(utuple(*args)))
    except Exception as err:
        logger.Log().write('Logger exception {}'.format(str(err)))


# Рекурсивное чтение yaml с последующим присваиванием полей оттуда объекту
def set_params(obj, data):
    try:
        for key, value in data.items():
            if isinstance(value, dict):
                set_params(obj, value)
            else:
                setattr(obj, str(key), value)
                log_print('| {} | {} '.format(key.ljust(31), obj.__dict__.get(key)))
    except Exception, e:
        log_print(str(e))


# Проверка валидности телефона
def is_phone_valid(phone):
    try:
        return len(str(int(phone))) >= 9
    except ValueError:
        return False


# Парсинг телефона
def parse_phone(phone):
    separators = ' +-()'
    previous_char = ''
    parsed_chars = ''
    result = ''
    for phone_char in phone:
        try:
            if phone_char.isdigit():
                if previous_char in separators or parsed_chars.isdigit() or not previous_char:
                    if previous_char == '-' and not result:
                        continue
                    result += phone_char
                else:
                    result = ''
            elif phone_char not in separators:
                if is_phone_valid(result):
                    break
                result = ''
            else:
                parsed_chars = ''
        finally:
            if phone_char not in separators:
                parsed_chars += phone_char
            previous_char = phone_char
    if len(result) < 9:
        result = ''
    return result


def parse_brazil(raw_phone):
    '''некоторые бразильские номера имеют добавленную 9,
    ее надо убрать,
    иначе кликер не сможет определить найденный чат'''
    if isinstance(raw_phone, (int, long)):
        phone = str(raw_phone)
    else:
        phone = raw_phone
    if isinstance(phone, (str, unicode)) \
            and phone.isdigit() \
            and phone.startswith('55') \
            and len(phone) == 13:
        return phone[:4] + phone[-8:]
    return raw_phone


# Типы статусов кликера
class first_time_status:
    NO_TASK = 0
    WAIT_FOR_LOAD = 1
    NO_SUCH_PHONE = 2
    TEXT_SENT = 3
    DESC = {NO_TASK: 'not a first time task',
            WAIT_FOR_LOAD: 'load first time url. waiting',
            NO_SUCH_PHONE: 'first time url loaded, but phone is not found. canceling',
            TEXT_SENT: 'First time message was sent',
            }


# Главный синглтон
class message_processor(objects.baseobject):
    """ Обработка сообщений """

    # Действия перед инициализацией
    def beforeInit(self, device_number, *args, **kwargs):
        # Назначение параметров по умолчанию
        # Все параметры по умолчанию могут быть переписаны настройками конфигурационных файлов whatsapp.ini/settings.yaml
        super(message_processor, self).beforeInit(*args, **kwargs)
        # Время запуска
        self.start_time = int(time.time())
        self.paths = paths.path_manager()
        self.RESOURCE_PATH = os.path.split(__file__)[0]
        self.settings = {}
        self.status_since = datetime.datetime.now()
        self.first_time_status = first_time_status.NO_TASK
        # Время последнего скана непрочитанных сообщений
        self.unread_scan_last = datetime.datetime.now()
        self.cmdid = 0
        self._status = '???'
        # Номер девайса
        self.device_number = device_number
        root_dir = os.path.join(*os.path.split(sys.argv[0])[:-1])
        # Путь конфигурационного yaml-файла в папке установки
        self.yaml_path = os.path.join(root_dir, 'users', self.device_number, 'settings.yaml')
        self.css_yaml_path = os.path.join(root_dir, 'users', self.device_number, 'css_settings.yaml')
        # Путь конфигурационного yaml-файла по умолчанию
        if not os.path.exists(self.yaml_path):
            log_print('No settings.yaml in root dir', self.yaml_path)
            self.yaml_path = 'C:/whatsapp/proto/users/%s/settings.yaml' % self.device_number
        # if not os.path.exists(self.css_yaml_path):
        #     log_print('No settings.yaml in root dir', self.css_yaml_path)
        #     self.css_yaml_path = 'C:/whatsapp/proto/users/%s/css_settings.yaml' % self.device_number
        # Путь локальной базы данных, в которой хранятся хеши сообщений(защита от дублирования)
        self.storage_filename = 'C:/whatsapp/proto/users/%s/whatsapp.db3' % self.device_number
        # Путь к файлу автоответа
        self.autoanswer_filename = 'C:/whatsapp/proto/users/%s/whatsapp.autoanswer' % self.device_number
        # Автоответ
        self.autoanswer = ''
        # Запущен кликер или нет
        self.is_started = False
        # Доступен ли гейт
        self.is_gateway_available = True
        # Период попытки подключения к гейту (5 минут)
        self.gateway_retry_delay = 5 * 60
        # Время последней проверки доступности гейтвея если он был не доступен
        self.gateway_failed_time = None
        # возраст сообщений в db3 для удаления, дней
        self.clear_hashes = 14

        # Селекторы
        # Список диалогов
        self.pane_side = '#pane-side'
        # Высота списка диалогов
        self.viewport_height = '$("#pane-side>div>div>div").height()'
        # Поле ввода текста, при отправке картинки
        self.image_editable = '._3ogpF, ._3FRCZ.copyable-text.selectable-text, ._2_1wd.copyable-text.selectable-text, ._3yEml._2359L ._13NKt.copyable-text.selectable-text'
        # Поле ввода текста в диалоге
        self.text_editable = 'footer [contenteditable]'
        # Поле поиска контактов
        self.search_editable = '._1JAUF, ._3yWey'
        # Кнопка подтверждения во всплывающем окне
        self.popup_button = '.S7_rT.FV2Qy, ._30EVj.gMRg5, ._1dwBj._3xWLK, ._20C5O._2Zdgs'
        # Метка загрузки картинки, по факту селектор отмены загрузки картинки
        self.image_load_css = '[data-icon="media-cancel"]'
        # Селектор непрочитанного диалога
        self.unread_dialog_css = '._2Z4DV ._38M1B, ._2nY6U ._23LrM'
        # Селектор найденного контакта в списке диалогов, при отправке
        self.css_client_chat = '._2Z4DV:not(._2GVnY), ._2nY6U:not(._7qwtH)' # TODO: находит чат + группу в которой состоит контакт - пофиксить
        # Селектор скрепки в диалоге, т.е. кнопка отправки вложений
        self.clip_css = '[data-icon=clip]'
        # Селектор отправки вложения документом
        self.clip_doc_css = '[data-icon=document], [data-icon=attach-document], [data-icon=attach-document-old]'
        # Селектор отправки вложения изображением
        self.clip_image_css = '[data-icon=image], [data-icon=attach-image], [data-icon=attach-image-old]'
        # Селектор чата
        self.css_chat = '._2UaNq, ._2EXPL, .eJ0yJ, ._3Pwfx, ._2Z4DV, ._2nY6U'
        # Поле для тестируемого селектора
        self.test_css = 'test value'
        # Селектор отправки сообщения
        self.send_btn_css = '[data-icon=send]'
        # хэдер с аватаром и меню (для сбивания фокуса при вставке телефона)
        self.header_menu = '._1KBFI, ._1G3Wr'
        # div с текстом вставки телефона not usd
        self.phone_input_div = '._2S1VP'

        # Тогглы, т.е. переключатели
        # 1 настраиваемые тп (будут переопределены текущие, от сюда можно убрать, но не стоит)
        # Режим кликера только на отправку
        self.send_only = False
        # Очистка включена
        self.clear_enabled = False
        # Удалять группы
        self.group_deletable = False
        # Удалять рассылки
        self.broadcast_deletable = False
        # Допустить невалидные телефоны
        self.allow_empty_phone = False
        # Открытие диалога по ссылке вотсаппа
        self.link_send_enabled = False
        # 2 остальные
        # Отправка сообщений включена
        self.outbox_enabled = True
        # Прокликивание списка диалогов включено
        self.click_enabled = True
        # Прием сообщений включен
        self.click_inbox = False
        # Увеличивать задержку времени ожидания загрузки изображения
        self.image_load_sleep_increase = True
        # Ожидать прогрузки сообщений со стороны вотсаппа
        self.process_waiting_enabled = False
        # Очищать рассылки
        self.clear_broadcasts = True
        # Очищать временные данные
        self.autoclean = False

        # Таймауты (задержки)
        # 1 настраиваемые тп (будут переопределены текущие, от сюда можно убрать)
        # задержка после скролла при прокликивании чатов, сек
        self.scroll_sleep = 0.5
        # задержка перед отправкой сообщения при рассылке, сек
        self.broadcast_click_sleep = 0.1
        # Время задержки после раскрытия попапа (при удалении), сек
        self.after_chat_context_sleep = 2
        # задержка после клика по прикреплению картинки, сек
        self.image_sleep = 2
        # задержка после клика по скрепке, сек
        self.clip_sleep = 3
        # задержка после клика по прикреплению документа, сек
        self.doc_sleep = 2
        # задержка поиска, для ожидания отрисовки контакта, сек
        self.search_sleep = 0.5
        # еще одна задержка поска, для ожидания отрисовки контакта, сек
        self.after_search_sleep = 2
        # задержка подгрузки картинки, сек
        self.image_load_sleep = 3
        # 2 остальные
        # таймаут обращения к JS, сек?
        self.sync_timeout = 120
        # максимальное время в LOST REGISTRATION, после будет перезагрузка браузера, сек
        self.lost_registration_period = 300
        # Задержка после вставки текста
        self.after_paste_text_sleep = 1
        # Задержка после открытия диалога по ссылке
        self.sleep_after_open_by_link = 2
        # задержка после отправки сообщения клиенту
        self.sleep_after_send_outbox = 1
        # задержка после перезагрузки браузера
        self.sleep_after_reload = 10

        # Другие настройки
        # 1 настраиваемые тп (будут переопределены текущие, от сюда можно убрать)
        # отступ клика от центра элемента в %, чем меньше, тем ближе к центру
        self.offset_click = 10  # set default
        # максимальное количество пустых страниц, просматриваемых при приеме сообщений
        self.max_empty_pages = 20
        # ограничитель на кол-во исходящих сообщений за одну отправку
        self.outbox_limit = 40
        # кол-во попыток задержки перед проверкой диалога, открытого по ссылке, одна попытка - 1 сек
        self.check_dialog_attempts = 3
        # ??? количество пропускаемых циклов работы кликера. (приводит к замедлению работы кликера)
        # - как часто слать запрос на предмет новых сообщений
        self.outbox_skip_cycles = 5
        # минимальное количество оставленных чатов после удаления, при достижении чаты не будут удаляться
        self.non_deletable_chat_count = 10
        # лимит удаленных чатов за цикл
        self.clear_limit = 5
        # не отправлять сообщения после истечения указанного периода в режиме LOST_CONNECT, сек
        self.lost_connect_send_period = 5
        # ничего не делать после получения ONLINE, сек
        self.online_calm_period = 5
        # прокликивание первых N номеров (диалогов)
        self.unread_scan_number = 0
        # период прокликивания
        self.unread_scan_period = 0
        # начало очистки
        self.clear_start_time = '01:00'
        # конец очистки
        self.clear_end_time = '23:00'
        # 2 остальные
        # ???
        self.r = 0
        # Количество пропущенных циклов
        self.skiped_cycles = 0
        # Количество пропущенных при удалении чатов
        self.skipped_on_delete = 0
        # кол-во прокликиваний по диалогу
        self.clicks = 20
        # максимальное кол-во попыток запуска
        self.times = 30
        # отступ хрома по оси у, лучше не трогать
        self.chrome_offset_y = 44
        # корректирующая переменная, лучше не трогать
        self.pane_offset_top = 1
        # количество страниц, которое просматривается после окончания лимита на отправку outbox_limit
        self.first_pages = 1
        # счетчик ошибок
        self.ioerror_count = 0
        # максимальное количество ошибок
        self.max_ioerror_count = 5
        # максимальное кол-во попыток получения статуса ONLINE/LOST_CONNECT, после достижения перезагрузит страницу браузера
        self.times_to_start = 100
        # количество диалогов на данный момент, лучше не менять
        self.total_qty = 0
        # количество задержек для отображения превью ссылки (not used?)
        self.link_preview_steps = 1
        # количество попыток скачать файл (с задержкой в 1 сек)
        self.download_file_tries = 2
        # минимальная длина телефона для генерации ссылки для открытия 
        self.valid_link_phone_length = 1

        self.sending_from_chat = False  # идет отправка сообщений из чата (пока не используется)
        self.enable_send_from_chat = True  # можно ли отправить сообщения из чата (пока не используется)
        self.transform_brazil = False  # убирать лишнюю 9 из бразильских номеров

    # Возвращает префикс для доступа к функциям в whatsapp-web.user.js
    def ep(self):
        return 'w("vlad")'

    def get_status_prop(self):
        return self._status

    def set_status_prop(self, value):
        if value != self._status:
            self.prior_status = self._status
            self._status = value
            self.status_last_update = datetime.datetime.now()

    status = property(get_status_prop, set_status_prop)

    # Возвращает дельту по времени
    def get_delta(self, param):
        return datetime.datetime.now() - param

    def set_status(self, status, remaining=''):
        try:
            self.job.synchronize(PARAM1_JSCOMMAND_ASYNC, u'%s.vlad.set_status(%d, %d, "%s", "%s");' %
                                 (self.ep(), self.total_qty, self.unread_dialogs_count(), status, remaining))
        except Exception:
            pass

    # Проверяет потеряно ли соединение 
    def is_connect_lost(self):
        return self.status == 'LOST_CONNECT'

    # Назначение параметров из yaml файла в JS
    def js_set_params(self, data):
        # if self.send_only:
        #     self.sync("{}.clearLocalStorage();".format(self.ep()), PARAM1_JSCOMMAND_ASYNC)
        #     self.sync("{}.{}={};".format(self.ep(), 'settings.send_only', 'true'), PARAM1_JSCOMMAND_ASYNC)
        #     log_print('| JS | {} | {} '.format('settings.send_only'.ljust(31), 'true'))
        # else:
        #     self.sync("{}.showVersion();".format(self.ep()), PARAM1_JSCOMMAND_ASYNC)
        #     self.sync("{}.addStyles();".format(self.ep()), PARAM1_JSCOMMAND_ASYNC)

        try:
            self.sync("{}.settings.timeline={};".format(self.ep(), self.timeline), PARAM1_JSCOMMAND_ASYNC)
            for key, value in data.items():
                if isinstance(value, dict):
                    self.js_set_params(value)
                else:
                    if not value.isdigit() and value not in ("true", "false"):
                        value = '`%s`' % value
                    self.sync("{}.{}={};".format(self.ep(), key, value), PARAM1_JSCOMMAND_ASYNC)
                    log_print('| JS | {} | {} '.format(key.ljust(31), value))
        except Exception, e:
            log_print(str(e))

    # После инициализации
    def afterInit(self, *args, **kwargs):
        super(message_processor, self).afterInit(*args, **kwargs)
        self.yaml_path = self.settings.get('yaml_path', self.yaml_path)
        self.css_yaml_path = self.settings.get('css_yaml_path', self.css_yaml_path)
        self.storage_filename = self.settings.get('storage_filename', self.storage_filename)
        self.autoanswer_filename = self.settings.get('autoanswer_filename', self.autoanswer_filename)
        self.settings['gateway'] = self.settings.get('gateway', 'https://gateway.chat2desk.com')
        self.settings['api'] = self.settings.get('api', 'https://api.chat2desk.com')
        self.timeline = self.settings.get('timeline', None)
        # Чтение ямла
        with open(self.yaml_path, 'r') as f:
            try:
                data = yaml.safe_load(f)
                set_params(self, data['Python'])
                time.sleep(1)
                self.js_set_params(data['JS'])
            except Exception, e:
                log_print(str(e))
        # with open(self.css_yaml_path, 'r') as f:
        #     try:
        #         data = yaml.safe_load(f)
        #         set_params(self, data['Python'])
        #         self.js_set_params(data['JS'])
        #     except Exception, e:
        #         log_print(str(e))
        if os.path.exists(self.autoanswer_filename):
            with io.open(self.autoanswer_filename, 'r', encoding='utf-8') as f:
                self.autoanswer = f.read()

    # Модификация координаты 
    def modify_point(self, point):
        r = list(point)
        try:
            if self.hwindow > 0:
                x, y = get_window_pos(self.hwindow)
                log_print('get window pos x: %s, y: %s' % (x, y))
                r[0] += x
                r[1] += y
        except Exception, e:
            log_print(repr(e))
        finally:
            return r

    # Подсчет непрочитанных диалогов 
    def unread_dialogs_count(self):
        return self.eval(self.sync("document.querySelectorAll('%s').length" % self.unread_dialog_css))

    # Проверка на наличие нового сообщения, парсится заголовок вкладки, в котором указано количество новых сообщений
    def new_messages_exist(self):
        r = 0
        text = get_window_text(self.hwindow)
        # log_print('='*10, 'text: ', text)
        if text:
            # match (number).*
            rr = re.match('\((\d+)\).*', text)
            if rr:
                try:
                    r = int(rr.groups()[0])
                except ValueError:
                    log_print('=' * 10, 'got error, text to parse: ', text)
                    pass
        if not r:
            r = self.unread_dialogs_count()
            if r:
                log_print('NEW_MESSAGES_EXIST: counting unread dialogs by css')
        return r

    # Проверяет зависла ли вкладка вотсаппа
    def not_responding(self):
        text = get_window_text(self.hwindow)
        if text:
            return text.find('responding') > -1
        return False

    # Функция клика, эти две функции избыточны, т.к. всего лишь делегируют параметры, ранее тут была логика
    def click(self, *args, **kwargs):
        return self.doclick(*args, **kwargs)

    # Функция правого клика
    def rightClick(self, *args, **kwargs):
        return self.dorightClick(*args, **kwargs)

    def doclick(self, point_x, point_y):
        point_x, point_y = self.modify_point([point_x, point_y])
        try:
            log_print('click %d %d' % (point_x, point_y))
            self.tofront()
            self.moveTo(point_x, point_y, False)
            time.sleep(0.1)
            return pyautogui.click(point_x, point_y)
        except WindowsError:
            pass
        return True

    def dorightClick(self, point_x, point_y):
        point_x, point_y = self.modify_point([point_x, point_y])
        try:
            log_print('rightClick %d %d' % (point_x, point_y))
            self.tofront()
            self.moveTo(point_x, point_y, False)
            return pyautogui.rightClick(point_x, point_y)
        except WindowsError:
            pass
        return True

    # Перемещение курсора по координате, с опциональной модификацией координат
    def moveTo(self, point_x, point_y, modify=True, *args, **kwargs):
        if modify:
            point_x, point_y = self.modify_point([point_x, point_y])
        try:
            return pyautogui.moveTo(point_x, point_y, *args, **kwargs)
        except WindowsError:
            pass

    # Скролл 
    def scroll(self, *args):
        self.tofront()
        try:
            return pyautogui.scroll(*args)
        except WindowsError:
            pass

    # Вставка телефона в поле поиска диалогов
    def paste_phone_in_search_field(self, phone):
        # вставляем телефон только если нет активной отправки из чата
        # if not self.sending_from_chat:
        # Предварительно закрываем все диалоговые окна, если не закрыть, поле ввода не будет активно и номер не вставится
        self.press_button('esc', times=3, sleep_after=0.1)
        self.enable_send_from_chat = False  # в настоящий момент не используется
        # сбиваем фокус - кликаем вне поля вставки телефона
        self.click_element(self.header_menu)
        time.sleep(1)
        log_print('>>>> search phone input', phone)
        # физический клик на поле ввода телефона - при клике из жс может не прочитать текст в поле
        self.click_element(self.search_editable)
        # self.sync('%s.pasteInputVal("%s", "%s", "%s")' % (self.ep(), self.search_editable, phone, 1), PARAM1_JSCOMMAND_SYNC)
        # self.sync('%s.searchPhoneFunc("%s", "%s", "%s")' % (self.ep(), phone, self.search_editable, self.phone_input_div), PARAM1_JSCOMMAND_SYNC)
        log_print('>>>> sleep after search input 1 sec')
        time.sleep(1)
        # Выделяем весь текст на случай, если тут уже было что-то написано
        pyautogui.hotkey('ctrlleft', 'a')
        time.sleep(0.5)
        # Копируем телефон в буфер обмена
        log_print('>>> now paste phone', phone)
        pyperclip.copy(phone)
        # Заменяем выделенный текст, необходимо чтобы гарантированно найти клиента
        pyautogui.hotkey('ctrlleft', 'v')
        time.sleep(0.5)

    # Обработка исключения при поиске клиента
    def after_find(self):
        log_print('after_find')
        self.press_button('enter', times=4, sleep_after=0.3)
        self.press_button('return', sleep_after=0.3)

    def get_client_chat_css(self, *args, **kwargs):
        sep = kwargs.get('sep', ' ')
        try:
            result = ''
            for char in args:
                if not isinstance(char, unicode):
                    temp_char = str(char)
                else:
                    temp_char = unicode(char)
                result += temp_char + sep
            return result.encode('utf-8')
        except Exception as err:
            logger.Log().write('get_client_chat_css {}'.format(str(err)))
            return self.css_client_chat

    # Поиск клиента
    def find_client(self, phone):
        # Проверяем, находимся ли в нужном диалоге, если да, клиента найден
        if self.check_current_dialog(phone, True):
            return True
        # Вставка телефона в строку поиска диалогов
        self.paste_phone_in_search_field(phone)
        # В случае если чат с клиентом не отрендерился ждем
        if not self.element_exists(self.css_client_chat):
            log_print('Client dialog not found, sleep {} sec'.format(self.search_sleep))
            time.sleep(self.search_sleep)
        # log_print('contact ', self.element_exists(self.css_client_chat))
        try:
            # Ждем
            log_print('Sleep one more {} sec'.format(self.after_search_sleep))
            time.sleep(self.after_search_sleep)
            # has_unread = self.sync('%s.hasDialogUnreadMessages(%s);' % (self.ep(), '%d'), PARAM1_JSPROC_SYNC)
            # log_print('>'*5, 'has unread', has_unread)
            # archive = self.sync('%s.isArchiveChat(%s);' % (self.ep(), '%d'), PARAM1_JSPROC_SYNC)
            # log_print('archive>', bool(archive))
            # Открываем чат с клиентом

            # проверка по названию чата начало
            title = self.get_client_chat_css('[title="', phone, '"]', sep='')
            log_print('css title', title)
            css = self.get_client_chat_css(self.css_client_chat, title)
            log_print('css full', css)
            self.click_element(css)
            # проверка по названию чата конец

            time.sleep(0.5)
            # Проверка чата, тот ли клиент
            if not self.check_current_dialog(phone):
                # В случае если клиент не тот, пытаемся открыть диалог по ссылке
                log_print('Try to open dialog by link...')
                start_time = time.time()
                open_by_link = self.open_dialog_by_link(phone)
                if open_by_link == 0:
                    self.close_popup()
                log_print('open by link result', str(open_by_link), ' in ', time.time() - start_time, ' sec')
                time.sleep(self.sleep_after_open_by_link)
            # Проверка в интервале
            for i in range(self.check_dialog_attempts):
                if not self.check_current_dialog(phone):
                    time.sleep(1)
                else:
                    # TODO: в send_message() есть вызов sendNewMessages()
                    # if has_unread:
                    # self.sendNewMessages(archive=archive)
                    self.sendNewMessages()
                    log_print('searching %s. found' % phone)
                    return True
            log_print('Failed to check current dialog after {} attempts'.format(
                str(self.check_dialog_attempts).encode('utf-8')))
            # self.sendNewMessages()
        except Exception, e:
            self.job.exception(e, 'found')
            self.after_find()
        # Проверим еще раз, если при проверке в интервале не вернулось True
        r = self.check_current_dialog(phone)
        if r:
            log_print('searching %s. found' % phone)
        else:
            log_print('searching %s. not found' % phone)
        return r

    # Еще один поиск клиента, надстройка над ним
    # R Выпилить, избыточно
    def find_client_to_send(self, phone, is_check_client=True):
        if is_check_client:
            if not self.find_client(phone):
                log_print('find_client_to_send. not found ' + phone)
                self.press_button('esc', times=3, sleep_after=0.1)
                return False
        return True
        # return self.check_current_dialog(phone)

    # Перезагрузка браузера
    def reload_browser(self):
        log_print('RELOAD_BROWSER: reloading')
        self.job.synchronize(PARAM1_JSCOMMAND_ASYNC, u'location.reload();')
        time.sleep(self.sleep_after_reload)
        # После перезагрузки необходимо снова назначить параметры в JS поскольку они слетают
        with open(self.yaml_path, 'r') as f:
            try:
                data = yaml.safe_load(f)
                self.js_set_params(data['JS'])
            except Exception, e:
                log_print(str(e))

    def element_clicked(self, css):
        '''

        :param css:
        :return:
        '''
        return True

    def send_image(self, filename, filedesc, addkeys=True):
        log_print('send image', filename)
        ### Отправка картинки. Выбираем файл, вбиваем описание и отправляем его
        # Надо уточнить, что данная строка вставляет путь к файлу в попап выбора файла
        self.job.synchronize(PARAM1_SETFILENAME, filename)
        image_clicked = None
        # Нажимаем по кнопке вложений
        for i in range(self.clip_sleep):
            clip_clicked = self.click_element(self.clip_css)
            if not clip_clicked:
                log_print('Could not find clip in send image after {} tries ({} sec)'.format(self.clip_sleep,
                                                                                             self.clip_sleep),
                          self.clip_css)
            else:
                # Ищем иконку для прикрепления изображения
                time.sleep(1)
                # Нажимаем по кнопке отправки изображения
                image_clicked = self.click_element(self.clip_image_css)
                if image_clicked:
                    log_print('Find image clip after {} tries ({} sec)'.format(i + 1, i + 1))
                    break
        # если иконка не нашлась - логгируем и ничего не делаем
        if not image_clicked:
            log_print('Could not find image clip after {} tries ({} sec)'.format(self.clip_sleep, self.clip_sleep))
        # иконка нашлась - отправляем картинку
        else:
            time.sleep(self.image_sleep)
            # Если есть описание то вбиваем
            if filedesc:
                log_print('select_image_file desc %s' % filedesc[:50])
                # self.type_write_click(filedesc, self.image_editable, False)
                self.click_element(self.image_editable)
                pyperclip.copy(filedesc)
                pyautogui.hotkey('ctrlleft', 'a')
                pyautogui.hotkey('ctrlleft', 'v')
                time.sleep(0.2)
            # Отправляем
            self.press_button('enter')
            time.sleep(0.1)
        # На случай если не отправилось, закрываем все окна, возвращаясь к исходному положению
        self.press_button('esc', times=3, sleep_after=0.25)

    # Аналогично send_image
    def send_doc(self, filename, filedesc=''):
        # Отправка DOC файла. Выбираем файл, вбиваем описание и отправляем его
        # Надо уточнить, что данная строка вставляет путь к файлу в попап выбора файла
        self.job.synchronize(PARAM1_SETFILENAME, filename)
        doc_clicked = None
        clip_clicked = self.click_element(self.clip_css)
        file_clip_type = self.clip_doc_css if os.path.splitext(filename)[-1] not in VIDEO_EXT else self.clip_image_css
        log_print('file ext: ', os.path.splitext(filename)[-1], 'clip type: ', file_clip_type)
        if not clip_clicked:
            log_print('Could not find clip in send document', self.clip_css)
        else:
            for i in range(self.clip_sleep):
                time.sleep(1)
                doc_clicked = self.click_element(file_clip_type)
                if doc_clicked:
                    log_print('Find document clip after {} tries ({} sec)'.format(i + 1, i + 1))
                    break
            if not doc_clicked:
                log_print(
                    'Could not find document clip after {} tries ({} sec)'.format(self.clip_sleep, self.clip_sleep))
            else:
                time.sleep(self.doc_sleep)
                # Если есть описание то вбиваем
                if filedesc:
                    log_print('select_video_file desc %s' % filedesc[:50])
                    # self.type_write_click(filedesc, self.image_editable, False)
                    self.click_element(self.image_editable)
                    pyperclip.copy(filedesc)
                    pyautogui.hotkey('ctrlleft', 'a')
                    pyautogui.hotkey('ctrlleft', 'v')
                    time.sleep(0.2)
                # self.press_button('enter', sleep_after=0.1)
                for _ in range(self.clip_sleep):
                    if self.click_element('[data-icon="send"]'):
                        break
                    time.sleep(1)
                time.sleep(0.1)
                self.press_button('esc', times=3, sleep_after=0.25)

    # Генерация имени файла
    def gen_filename(self, ext):
        return self.paths.filename(FILESTORAGE, '%s_%s%s' % (self.device_number, int(round(time.time())), ext))

    def retrieve_file(self, filename, filedesc=''):
        ext = os.path.splitext(filename)[1]
        image_path = self.gen_filename(ext)
        log_print('filename ->', filename)
        log_print('image_path ->', image_path)
        if isinstance(filename, unicode):
            filename = filename.encode('UTF-8')
        try:
            for i in range(self.download_file_tries):
                download = urllib.urlretrieve(filename, image_path)
                if os.path.exists(image_path):
                    log_print('file downloaded ->', i + 1, download[0])
                    break
                log_print('Try to download ->', i + 1, download[0])
                time.sleep(1)
            if not os.path.exists(image_path):
                log_print('Failed to download ->', download[0], download[1].__dict__)
        except Exception as err:
            log_print('ERROR!. cannot retrieve %s' % filename)
            log_print(err)
            raise Exception('ERROR!. cannot retrieve %s' % filename)
        return image_path

    def get_first(self, start, stop, css_selector):
        r = self.sync("%s.vlad.get_first(%d, %d, '%s')" % (self.ep(), start, stop, css_selector))
        if r:
            return self.eval(r)
        return None

    def get_first_status(self, start, stop, css_selector):
        r = self.sync("%s.vlad.get_first_status(%d, %d, '%s')" % (self.ep(), start, stop, css_selector))
        if r:
            return r
        return None

    def get_first_broadcast(self, start, stop, css_selector):
        r = self.sync("%s.vlad.get_first_broadcast(%d, %d, '%s')" % (self.ep(), start, stop, css_selector))
        if r:
            return self.eval(r)
        return None

    def get_last(self, start, stop, css_selector):
        r = self.sync("%s.vlad.get_last_unread(%d, %d, '%s')" % (self.ep(), start, stop, css_selector))
        if r:
            return self.eval(r)
        return None

    # Получить последнее непрочитанное
    def get_last_unread(self, start, stop):
        return self.get_last(start - self.pane_offset_top, stop, self.unread_dialog_css)

    # Удалить атрибут элемента
    def remove_attr(self, css_selector, attrname):
        return self.sync("$('%s').attr('%s', null)" % (css_selector, attrname))

    # Добавить атрибут элемента
    def add_attr(self, css_selector, attrname, attrvalue):
        return self.sync("$('%s').attr('%s', '%s')" % (css_selector, attrname, attrvalue))

    # Скролл в JS
    def set_scroll(self, css, value, scroll_sleep=0.1):
        self.job.synchronize(PARAM1_JSCOMMAND_ASYNC, u'$("%s").scrollTop(%d);' % (css, value))
        time.sleep(scroll_sleep)

    # Скролл панели диалогов
    def scroll_paneside(self, pos):
        self.sync("$('%s').scrollTop(%s)" % (self.pane_side, pos))

    # Получить позицию скролла элемента
    def get_scroll(self, css):
        r = self.sync(u'$("%s").scrollTop()' % (css,))
        if r is not None:
            try:
                return int(r)
            except ValueError:
                return 0
        return None

    # Получить высоту диалога
    # R Не помню чтоб эта высота когда-либо менялась, лучше переделать в настраиваемый параметр со значением по умолчанию
    def get_chat_height(self):
        r = self.sync('$("%s").first().height()' % self.css_chat)
        # log_print('chat h', r)
        if r is not None:
            try:
                if int(r):
                    return int(r)
            except ValueError:
                return 72
        return 72

    # Получить высоту всего списка диалогов, даже неотрендеренных
    def get_viewport_height(self):
        return self.eval(self.sync(self.viewport_height))

    # Поиск непрочитанных сообщений
    def scan_unread(self):
        log_print('=' * 10, 'scan_unread')
        self.set_status(u'Scanning for unread messages')
        count = 0
        try:
            log_print('=' * 10, 'rem attr:', self.css_chat, 'broadcast')
            self.remove_attr(self.css_chat, 'broadcast')

            self.press_button('esc', sleep_after=0.1)

            # Проверяем отрендерен ли вообще список чатов
            # R Избыточно, ситуаций когда он не отрендерен нет
            pane_side = self.get_pane_side_coord()
            if not pane_side:
                log_print('no pane side')
                return False, count

            # Идем в самый конец
            height = self.get_viewport_height()
            # Определяем количество страниц с диалогами, с поправкой
            pages = 4 + (height / pane_side[3])
            times = 0
            chat_height = self.get_chat_height()
            # Назначаем скролл в высоту диалога в списке
            scroll_height = pane_side[3]
            self.sync('%s.vlad.clear_broadcast()' % self.ep())
            while times < 1:
                times += 1
                pageno = 0
                # Проверяем отрендерена ли строка поиска контактов
                # R Избыточно
                if not self.find_magnifier():
                    return False, count
                # Скроллим список диалогов вверх
                self.set_scroll(self.pane_side, 0, self.scroll_sleep)
                scroll_pos = 0
                empty = True
                # Начинаем перебирать список диалогов
                while count <= self.unread_scan_number:
                    pcount = self.scan_unread_next(pane_side, scroll_pos)
                    count += pcount
                    if pcount:
                        empty = False
                    else:
                        break
                    # Ограничение по количеству проскроленных страниц
                    if count >= self.unread_scan_number:
                        break
                    # Скроллим по диалогу в списке диалогов вниз
                    scroll_pos += scroll_height
                    self.set_scroll(self.pane_side, scroll_pos, self.scroll_sleep)
                    pageno += 1
                if empty:
                    break

            self.find_magnifier()

            return True, count

        except Exception, e:
            self.job.exception(e, 'scan_unread')
            return False, count

    # Итерация по непрочитанным
    def scan_unread_next(self, pane_side, scroll_pos):
        r = 0
        self.set_scroll(self.pane_side, scroll_pos)
        # Ищем бейдж непрочитанного
        first_coord = self.get_first_broadcast(pane_side[1] - self.pane_offset_top, pane_side[1] + pane_side[3],
                                               self.css_chat)
        log_print('[first coord]', first_coord)
        # В случае если нашли
        while first_coord and (first_coord[0] is not None):
            # Открываем непрочитанный диалог
            x, y = self.coord_to_point(first_coord)
            self.click(x, y)
            time.sleep(self.broadcast_click_sleep)
            # Отправляем сообщения из диалога в систему
            self.sendNewMessages()
            time.sleep(0.1)

            r += 1
            # В случае если есть ограничение по приему непрочитанных - прерываемся
            if r >= self.unread_scan_number:
                break
            self.set_scroll(self.pane_side, scroll_pos)
            first_coord = self.get_first_broadcast(pane_side[1], pane_side[1] + pane_side[3], self.css_chat)
        return r

    # Нажатие кнопки отправки, опционально с нажатием enter
    def click_send_button(self, after_send_sleep=0.1, addkeys=True):
        # self.sync('%s.clickSendButton()' % self.ep())
        self.click_element(self.send_btn_css)
        time.sleep(after_send_sleep)
        if addkeys:
            self.press_button('enter')
        return True

    # Отправка сообщения из системы клиенту
    def send_message(self, outbox, is_check_client=True, check_current=True, addkeys=True, after_send_sleep=0.1):
        """ Отправка сообщения по информации из пакета """
        # Закрываем все всплывающие окна
        self.press_button('esc', 1, 1)
        # self.close_popup()
        # В случае если нужна проверка телефона - проверяем
        if check_current:
            is_phone = bool(parse_phone(outbox['phone']))
            # log_print('raw phone', outbox['phone'])
            if not self.find_client_to_send(outbox['phone'],
                                            is_check_client):
                log_print('send_message. current dialog is not ' + outbox['phone'] + ' skip message')
                return False
        self.tofront()
        # Отправка картинки/видео
        outbox_image = outbox.get('image') or outbox.get('video')
        # log_print('='*5, 'get image', outbox_image)
        if outbox_image:
            if not outbox.get('localfile'):
                outbox['localfile'] = self.retrieve_file(outbox_image)
            self.send_image(outbox['localfile'], outbox.get('body'), addkeys)
            time.sleep(self.sleep_after_send_outbox)
        else:
            pdf_file = outbox.get('pdf')
            # Отправка пдф
            if pdf_file:
                if not outbox.get('localfile'):
                    outbox['localfile'] = self.retrieve_file(pdf_file, outbox.get('body'))
                if os.path.splitext(outbox['localfile'])[-1] in {'.mp4', }:
                    self.send_doc(outbox['localfile'], outbox.get('body'))
                else:
                    self.send_doc(outbox['localfile'])
                    self.type_write_click(outbox.get('body'))
                time.sleep(self.after_paste_text_sleep)
                self.press_button('enter')
                time.sleep(self.sleep_after_send_outbox)
            # Отправка просто текста
            else:
                # ToDo: исправить кодировку load_link
                if True or self.first_time_status != first_time_status.WAIT_FOR_LOAD:
                    # Вставка текста в поле сообщения в диалоге
                    self.type_write_click(outbox['body'], self.text_editable, clear_text=True)
                    time.sleep(1)
                # Отправляем
                self.click_send_button(after_send_sleep, addkeys)
                time.sleep(self.sleep_after_send_outbox)
                # self.press_button('enter')
                # Принимаем сообщения, на случай, если сообщение пришло во время отправки, оно может быть прочитанным
                # и кликер получит его только при следующем непрочитанном сообщении, если выйдет из диалога,
                # или при отправке сообщения в этот диалог
                # A После отправки картинки нет приема сообщений, сообщения могут теряться
        self.sendNewMessages()
        if self.first_time_status == first_time_status.WAIT_FOR_LOAD:
            self.first_time_status = first_time_status.TEXT_SENT
        return True

    # Преобразование координат в точку, с поправкой на высоту рамки контейнера кликера
    def coord_to_point(self, coord):
        return int((coord[0] * 2 + coord[2]) / 2), int((coord[1] * 2 + coord[3]) / 2) + self.chrome_offset_y

    # Стандартный eval, с кастомным обработчиком, в случае null выбросит эксепшн
    def eval(self, expr):
        if expr is None:
            raise EDeadContainer()
        try:
            return eval(expr)
        except Exception as err:
            log_print('Eval failed:', err)
            log_print('Eval failed expession:', expr)

    # Основная функция связи Python & JS, где-то в проекте она лежит в качестве модуля на делфи
    def sync(self, cmd, param=PARAM1_JSCOMMAND_SYNC, sync_timeout=None):
        # log_print('>>>>>>>>>>', cmd)
        self.cmdid += 1
        if not isinstance(cmd, unicode):
            cmd = unicode(cmd)
        sync_timeout = self.sync_timeout if sync_timeout is None else sync_timeout
        return self.job.synchronize(param, cmd, self.cmdid, sync_timeout)

    # Выделение текста в области элемента по селектору
    def select_text(self, input_css):
        self.job.synchronize(PARAM1_JSCOMMAND_ASYNC, u'$("%s").select();' % input_css)
        time.sleep(0.1)

    # ?
    def check_selected_text(self, input_css):
        return self.sync("%s.check_selection('%s')" % (self.ep(), input_css)) == '1'

    # Очистка текста в области элемента по селектору
    def clear_text(self, input_css):
        self.job.synchronize(PARAM1_JSCOMMAND_ASYNC, u'$("%s").text("");' % input_css)
        time.sleep(0.1)

    # Функция вставки текста
    def type_write_click(self, message, input_css=None, check_selected=True, clear_text=False):
        if not message:
            log_print('type_write_click - empty message. ')
            return False
        if input_css is None:
            input_css = self.text_editable
        select_sleep = 0.1
        log_print('type_write_click')

        self.sync('%s.pasteInputVal("%s","%s")' % (self.ep(), input_css, ''))
        if self.first_time_status == first_time_status.WAIT_FOR_LOAD:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(select_sleep)
        if clear_text:
            self.clear_text(input_css)
        pyperclip.copy(message)
        paste(self.hwindow, PASTE_SELECTAFTER)
        time.sleep(select_sleep)
        self.select_text(input_css)
        if check_selected and not self.check_selected_text(input_css):
            log_print('new paste function failed')
            if clear_text:
                self.clear_text(input_css)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(select_sleep)
        return True

    def get_chat_status(self):
        # log_print('get chat status...')
        try:
            pane_side = self.get_pane_side_coord()
            log_print('got pane side {}'.format(pane_side))
            return self.get_first_status(pane_side[1] - self.pane_offset_top, pane_side[1] + pane_side[3],
                                         self.css_chat)
        except Exception, e:
            log_print(repr(e))
            return 'not found'

    # Отправка статуса кликера в сервис
    def check_status(self, check_msg):
        log_print('check status check_msg', check_msg)
        result = "None"
        r = 0
        self.press_button('esc', sleep_after=0.1)
        # Sbivaem fokus inache ne naydet
        log_print("Removing focus...")
        # chtoby klikat to na odnu stroku, to na druguyu
        while r < 2:
            log_print(r)
            # self.click(POINT_9[0], POINT_9[1] - (r * 70))
            self.click_element(self.header_menu)
            time.sleep(0.5)
            if self.find_magnifier():
                # Ishem nujniy kontakt
                pyautogui.hotkey('ctrlleft', 'a')
                time.sleep(0.1)
                log_print("Checking status of " + check_msg['client_phone'] + "...")
                self.paste_phone_in_search_field(check_msg['client_phone'])
                time.sleep(1)
                result = self.get_chat_status()
            else:
                result = "not found"
            log_print('check_status_result=', result)
            if result != "not found":
                self.press_button('esc', times=2, sleep_after=0.1)
                body = {"message_id": check_msg['message_id'], "status": result,
                        "client_phone": check_msg['client_phone']}
                # response = requests.post(self.settings['api'] + '/macros/statuses', body)

                # log_print('to send', body)
                response = req.request('POST', self.settings['api'] + '/macros/statuses',
                                       body=json.dumps(body).encode('utf-8'),
                                       headers={'Content-Type': 'application/json'}
                                       )

                try:
                    # log_print('[status response]', response.json())
                    log_print('[status response]', to_str(response.data))
                except:
                    # log_print('[status response]', response.text)
                    log_print('[status response]', to_str(response.data))
                return result
            self.press_button('esc', times=2, sleep_after=0.25)
            r = r + 1
        # response = requests.post(self.settings['api'] + '/macros/statuses',
        #                          {"message_id": check_msg['message_id'], "status": result,
        #                           "client_phone": check_msg['client_phone']})

        response = req.request('POST', self.settings['api'] + '/macros/statuses',
                               body=json.dumps({"message_id": check_msg['message_id'], "status": result,
                                                "client_phone": check_msg['client_phone']}),
                               headers={'Content-Type': 'application/json'})
        # log_print('[status response]', response)
        log_print('[status response]', response.data)
        return result

    def is_alive(self):
        return self.job.isAlive()

    # Поиск поля ввода номера телефона, основной маркер того, что все в порядке, при LOST_REGISTRATION поля ввода нет
    def find_magnifier(self):
        rect = self.sync('%s.getRect("%s")' % (self.ep(), self.search_editable))
        # log_print('@'*10, type(rect))
        # log_print('@'*10, rect)
        response = self.eval(rect)
        # log_print("MAGNIFIER", response)
        # response = self.eval(self.sync('%s.getRect("%s")' % (self.ep(), self.search_editable)))
        if response:
            return True
        log_print("Cannot find phone input, make sure that whatsapp window loaded")
        return False

    # Проверка наличия элемента
    def element_exists(self, css_selector):
        coord = self.eval(self.sync("%s.vlad.getcoord('%s')" % (self.ep(), css_selector)))
        return bool(coord and coord[0] is not None)

    # Получение координат списка диалогов
    def get_pane_side_coord(self):
        # log_print('[get pane side coord]')
        r = self.sync('%s.vlad.getcoord("%s")' % (self.ep(), self.pane_side))
        if r:
            return self.eval(r)
        return None

    # Клик по непрочитанному диалогу
    def click_unread_dialog(self, pane_side):
        # log_print('='*10, 'click unread dialog')
        last = self.get_last_unread(pane_side[1], pane_side[1] + pane_side[3])
        # log_print('[*1 LAST]', last)
        if not last or (last[0] is None):
            return False
        if pane_side[1] <= last[1]:
            x, y = self.coord_to_point(last)
            # log_print('[*2 COORDS]', x, y)
            self.sendNewMessages()
            self.click(x, y)
            time.sleep(0.1)
            self.sendNewMessages()
            return True
        delta = 0
        if pane_side[1] > last[1]:
            delta = pane_side[1] - last[1]
        x, y = self.coord_to_point(pane_side)
        self.moveTo(x, y, True, 0.1)
        self.scroll(delta)
        time.sleep(0.1)
        x, y = self.coord_to_point([pane_side[0], pane_side[1], last[2], last[3]])
        self.sendNewMessages()
        self.click(x, y)
        time.sleep(0.1)
        self.sendNewMessages()
        return True

    # Откат в начальное состояние
    def goto_first(self):
        self.press_button('esc', times=3, sleep_after=0.1)
        self.set_scroll(self.pane_side, 0)
        self.find_magnifier()

    # Поиск непрочитанных с пролистыванием списка диалогов
    def click_unread(self, first_page=False):

        if not self.click_enabled:
            return False

        if not self.new_messages_exist():
            # log_print('[NO NEW MESSAGES]')
            return False

        pane_side = self.get_pane_side_coord()
        # log_print('[PANE SIDE]', pane_side)
        if not pane_side:
            log_print('no pane side')
            return False

        self.set_status(u'Receiving messages')

        height = self.get_viewport_height()
        # log_print('[VIEWPORT H]', height)
        if first_page:
            pages = 1
            log_print('click_unread. first page only')
        else:
            pages = 1 + (height / pane_side[3])
        pageno = 0
        empty_page_count = 0
        qty_to_send = self.new_messages_exist()
        # log_print('[QTY TO SEND]', qty_to_send)
        while self.new_messages_exist() and (pageno < pages) and (empty_page_count < self.max_empty_pages):
            empty_page = True
            for t in range(1, self.clicks):
                if not self.click_unread_dialog(pane_side):
                    break
                else:
                    empty_page = False
                    empty_page_count = 0
                    qty_to_send -= 1
            if qty_to_send == 0:
                break
            if empty_page:
                empty_page_count += 1
            self.moveTo(pane_side[0] + 50, pane_side[1] + 30 + self.chrome_offset_y, True, 0.1)
            self.scroll_paneside(pageno * pane_side[3])
            time.sleep(self.scroll_sleep)
            pageno += 1

        self.find_magnifier()
        self.goto_first()
        return True

    # Получить заголовок открытого чата
    def get_activechattitle(self):
        return self.sync('%s.vlad.activechattitle()' % self.ep())

    # Проверка текущего диалога при отправке
    def check_current_dialog(self, phone, force_check=False):
        # для бразильскийх номеров может потребоваться убрать "лишнюю" девятку
        # phone or chat title here
        cp = self.get_current_dialog()
        # if cp.startswith('55') and len(cp) == 12:
        # для бразильскийх номеров может потребоваться убрать "лишнюю" девятку
        # если текущий диалог имеет 12 значный номер, то убираем 9
        # если нет (13 значный), то номер останется оригинальным
        if self.transform_brazil is True:
            phone = parse_brazil(phone)
        # compare phone or chat title with phone
        r = cp == phone
        if not r:
            r = cp == '00' + phone
            if not r:
                r = cp == '0' + phone
        try:
            log_print('Check current dialog for %s, chat title is %s, r is %s' % (
                unicode(phone) if isinstance(phone, unicode) else phone, unicode(cp) if isinstance(cp, unicode) else cp,
                r))
        except UnicodeEncodeError as err:
            log_print('1. UnicodeEncodeError error in logging string (not important)', err.message)
        except Exception as err:
            log_print('2. Some error in logging string (not important)', err.message)
        if self.allow_empty_phone and not r and cp and not parse_phone(cp) and not force_check:
            return True
        return r

    def get_current_dialog(self):
        """ Получение текущего номера телефона, если телефон пустой возвращается просто название диалога """
        r = self.get_activechattitle()
        if r:
            phone = parse_phone(r)
            if phone:
                return phone
        return r

    # Очистка старых хешей по таймштампу, если этого не делать whatsapp.db3 разрастется 
    def clear_old_hashes(self):
        dm = sqlt_get_data(self.storage_filename)
        try:
            r = dm.delete('INBOX3', {'TIMESTAMP': None})
            r = dm.delete('INBOX3', {'TIMESTAMP': ""})
            # 600000 ~ 1 week
            tmstmp = self.clear_hashes * 24 * 60 * 60
            r = dm.execute('DELETE FROM INBOX3 WHERE TIMESTAMP < %s' % int((time.time() - tmstmp) * 1000))
            log_print("\n DB TIMESTAMPS NEXT : \n HASHES WILL BE DELETED BELOW THIS DATE %s \n CURRENT DATE %s" % (
            time.ctime(int((time.time() - 600000))), time.ctime()))
            dm.commit()
            return r
        except Exception:
            return 0

    def add_waiting(self, clientphone):
        dm = sqlt_get_data(self.storage_filename)
        try:
            r = dm.insert('WAITING', {'CLIENTPHONE': clientphone})
            if r:
                log_print('%s append for waiting' % clientphone)
            return r
        except Exception:
            return 0

    def delete_waiting(self, clientphone):
        dm = sqlt_get_data(self.storage_filename)
        try:
            r = dm.delete('WAITING', {'CLIENTPHONE': clientphone})
            if r:
                log_print('%s delete from waiting' % clientphone)
            return r
        except Exception, e:
            self.job.exception(e)
            return 0

    # R уже не актуально, нужно удалить
    def process_waiting(self):
        dm = sqlt_get_data(self.storage_filename, adapt_unicode=False)
        try:
            d = dm.select('WAITING', ('CLIENTPHONE',))
            for ind, rec in enumerate(d):
                qty_to_send = len(d) - ind
                log_print('%s Process waiting (%d) %d remaining' % (rec['CLIENTPHONE'], len(d), qty_to_send))
                self.set_status(u'Process waiting (%d)' % len(d), u'%d remaining' % qty_to_send)
                if self.find_client_to_send(rec['CLIENTPHONE'], True):
                    self.sendNewMessages()
                    time.sleep(0.5)
                else:
                    self.delete_waiting(rec['CLIENTPHONE'])
        except Exception, e:
            self.job.exception(e)
            return 0

    # Отправка сообщений из кликера в систему, основная логика в js
    def sendNewMessages(self, archive=False):
        """Отправка сообщений в js"""
        self.sending_from_chat = True
        if self.send_only:
            self.sending_from_chat = False
            return 0

        if not archive:
            # log_print('ESC')
            self.press_button('esc', times=3, sleep_after=0.1)
        else:
            log_print('NO ESC')
        cp = self.get_current_dialog()
        # log_print('='*5, 'sendNewMessages', 'dialog>', cp)

        if not cp:
            self.sending_from_chat = False
            return 0

        d1 = datetime.datetime.now()
        r = self.sync('%s.sendNewMessages(%s);' % (self.ep(), '%d'), PARAM1_JSPROC_SYNC, sync_timeout=120)
        # pyautogui.scroll(10)
        # pyautogui.scroll(-10)
        self.press_button('esc', times=3, sleep_after=0.1)
        # log_print('after js.sendNewMessages ESC')
        if r and int(r):
            log_print('=' * 5, 'sendNewMessages', r)

        try:
            t = 0
            if not r:
                self.sending_from_chat = False
                return 0
            # Тут происходят небольшие лупы, это необходимо чтобы прогрузилась картинка/видео/документ, текст же улетает очень быстро
            while r and int(r) < 0 and t < 20:
                log_print('>>> from js sendNewMessages() ', r)
                log_print('try once more')
                if int(r) == -2:
                    log_print('waiting for message')
                    self.add_waiting(cp)
                    self.sending_from_chat = False
                    return r
                t += 1
                if self.image_load_sleep_increase:
                    time.sleep(t * self.image_load_sleep)
                else:
                    time.sleep(self.image_load_sleep)
                while self.element_exists(self.image_load_css):
                    log_print('image still loading')
                    time.sleep(1)
                # close possible popup
                self.press_button('esc')
                # self.close_popup()
                r = self.sync('%s.sendNewMessages(%s);' % (self.ep(), '%d'), PARAM1_JSPROC_SYNC)
                log_print('2>>> from js sendNewMessages() ', r)
            if t >= 20:
                log_print('ooppps > 20 times')
            if r and int(r) > 0:
                delta = datetime.datetime.now() - d1
                log_print('%s. sending inbox %s messages. %d.%d sec' % (cp, r, delta.seconds, delta.microseconds))
                self.delete_waiting(cp)
                if self.autoanswer:
                    self.send_message({'body': self.autoanswer, 'phone': cp}, False)
        except ValueError:
            self.sending_from_chat = False
            delta = datetime.datetime.now() - d1
            log_print('%s. Error in sendNewMessages. %d.%d sec' % (cp, delta.seconds, delta.microseconds))
            r = 0
        self.sending_from_chat = False
        return r

    def get_app_status(self):
        return self.sync('%s.vlad.getappstatus()' % self.ep())

    def tofront(self):
        return tofront(self.hwindow)

    def close_low_battery(self):
        log_print('in close low battery')
        self.sync('%s.lowBatteryClose()' % (self.ep()), PARAM1_JSCOMMAND_ASYNC)
        # self.sync('%s.lowBatteryClose();' % self.ep(), PARAM1_JSCOMMAND_SYNC)

    # Основной цикл синглтона, который кликер пробегает постоянно, вновь и вновь
    # Т.е. фактически, если ты видишь, что кликер отправил сообщение, потом принял, потом снова отправил, то он проживает 2-ой цикл
    #                                             |         1-ый цикл             | | начало 2-го цикла |
    #                                              _______________________________   ___________________
    def process_messages(self):
        # log_print(datetime.datetime.now() - self.start_time)
        # log_print(datetime.datetime.now().second - self.start_time.second)
        if int(time.time()) - self.start_time >= 60 * 60 * 12:
            log_print('START TO RELOAD BROWSER DAYLY')
            self.reload_browser()
            # self.close_low_battery()
            self.start_time = int(time.time())
        inbox_first_page = False
        outbox_enabled = self.outbox_enabled
        if outbox_enabled and self.outbox_skip_cycles:
            outbox_enabled = self.skiped_cycles >= self.outbox_skip_cycles
            if outbox_enabled:
                self.skiped_cycles = 0
            else:
                self.skiped_cycles += 1

        try:
            self.tofront()

            # Очистка временных данных
            if not self.autoclean:
                # Очистка хешей сообщений
                self.clear_old_hashes()
                # Очистка логов старше 7 суток
                self.clear_path("C:\\whatsapp\\proto\\users\\%s\\log\\", 7)
                # Очистка стораджа(скачанные медиа), старше суток
                self.clear_path("C:\\whatsapp\\proto\\users\\%s\\wa_storage\\", 1)
                # Ставим флаг в True, чтобы больше в этот цикл не заходить
                self.autoclean = True

            # Проверка загрузился ли JS
            if self.sync('%s.vlad && "1" || "0"' % self.ep()) == '0':
                log_print('no js script. waiting')

                return True

            # Получение статуса приложения, далее в зависимости от статуса идут разные режимы работы
            self.status = self.get_app_status()

            # В случае если это LOST_REGISTRATION, n-ое время спустя страница перезагрузится
            if self.status == 'LOST_REGISTRATION' and self.get_delta(
                    self.status_since).seconds > self.lost_registration_period:
                log_print('lost registration reload after %d' % self.lost_registration_period)
                self.reload_browser()
                # self.close_low_battery()
                return True
            # Дальше идет проверка на то, сколько времени кликер не работает и после достижения лимита происходит перезагрузка страницы
            if self.status not in ('ONLINE', 'LOST_CONNECT'):
                self.set_status(u'Idle due to status (%s)' % self.status)
                self.r += 1
                log_print('not online. skip processing.')
                if self.r == self.times_to_start:
                    log_print("Rebooting page after many tries (not online)")
                    self.reload_browser()
                    # self.close_low_battery()
                    self.r = 0
                return True
            # В случае если статус ONLINE, начинается старт кликера
            if self.status == 'ONLINE':
                delta = self.get_delta(self.status_since)
                if delta.seconds < self.online_calm_period:
                    self.set_status(u'Warming up (%d)' % (self.online_calm_period - delta.seconds,))
                    return True
            if not self.is_started:
                log_print('start to close low battery')
                self.close_low_battery()
                try:
                    self.sync('%s.changeVersionStyle()' % self.ep(), PARAM1_JSCOMMAND_ASYNC)
                except:
                    pass
                self.is_started = True
            # Проверка строки поиска, если ее нет, что-то не так
            # R Тут тоже избыточно
            if not self.find_magnifier():
                self.r += 1
                self.goto_first()
                if self.r == self.times:
                    log_print("Refreshing page after many tries (phone input not found)")
                    self.reload_browser()
                    self.r = 0
            else:

                # определение количества диалогов требует наличие лупы
                self.total_qty = self.get_dialog_qty()
                if not self.not_responding():

                    if self.is_connect_lost():
                        delta = self.get_delta(self.status_since)
                        if delta.seconds > self.lost_connect_send_period:
                            self.set_status(
                                u'Idle after %d sec of LOST_CONNECT (%d)' % (self.lost_connect_send_period,
                                                                             delta.seconds))
                            log_print('skip sending after %d sec of LOST_CONNECT' % self.lost_connect_send_period)
                            return True

                    # отправка сообщений
                    out_queue = outbox_manager(log_print)
                    if self.status in ('ONLINE', 'LOST_CONNECT'):
                        outboxes = out_queue.read_data()
                        # log_print('='*5, 'outboxes', outboxes)
                        if not outboxes:

                            if outbox_enabled:
                                url = self.settings['gateway'] + \
                                      '/?r=scheduler/get-updates&type=whatsapp&devicePhone=' + \
                                      self.device_number
                                if self.is_gateway_available or \
                                        (not self.is_gateway_available
                                         and self.gateway_failed_time
                                         and time.time() - self.gateway_failed_time > self.gateway_retry_delay):
                                    # response = requests.get(url)
                                    # log_print('reading data from outbox')
                                    try:
                                        # response = requests.get(url)
                                        # data = response.json()

                                        response = req.request('GET', url, retries=retry)
                                        data = response.data
                                        data = to_str(data)
                                        data = json.loads(data)

                                        # гейт доступен:
                                        self.is_gateway_available = True
                                        self.gateway_failed_time = None
                                        if data:
                                            out_queue.write_data(data)
                                            outboxes = out_queue.read_data()
                                    except requests.exceptions.ConnectionError as err:
                                        log_print('connection %s' % err.message)
                                        # не смогли подключиться == гейт не доступен
                                        self.is_gateway_available = False
                                        self.gateway_failed_time = time.time()
                                    except Exception, e:
                                        self.job.exception(e)
                                        log_print(url)
                                        # log_print('response=%s' % (response.text,))
                                        # log_print('no data for outbox (%s)' % response.text)

                                        log_print('response=%s' % (response.data,))
                                        log_print('no data for outbox (%s)' % response.data)
                                        # не получили json == гейт не доступен
                                        self.is_gateway_available = False
                                        self.gateway_failed_time = time.time()
                        else:
                            log_print('!!!! queue has unsent messages !!!!')
                    else:
                        log_print('appStatus = %s. skip retrieve messages' % (self.status,))
                        return True

                    if outboxes and self.is_gateway_available:
                        phone = None
                        found = False
                        outcount = 0
                        qty_to_send = len(outboxes)
                        if self.outbox_limit:
                            qty_to_send = min(qty_to_send, self.outbox_limit)
                        for filename, outbox in outboxes.items():
                            # лог сообщений из сервиса
                            raw_log_print('=' * 10, 'raw print',
                                          outbox)  # логгирование кириллицы, открывать лог файл в кодировке utf-8!
                            # log_print('='*10, outbox)
                            log_print('=' * 10, self.device_number)
                            if not self.is_alive():
                                return True

                            error = False
                            error_message = ''

                            try:
                                self.set_status(u'Sending messages', u'%d remaining' % qty_to_send)
                                qty_to_send -= 1
                                # пустой пакет - сделано для отладки
                                if filename:
                                    log_print('process %s' % os.path.split(filename)[1])
                                    if outbox is None:
                                        fname = os.path.split(filename)[1]
                                        outbox = {'phone': fname.split('_')[0]}
                                        raise Exception('error reading %s' % fname)

                                # если изменился номер телефона - перед сменой диалога надо принять сообщения
                                if phone != outbox['phone']:
                                    if phone:
                                        if self.click_inbox:
                                            self.sendNewMessages()
                                    phone = outbox['phone']
                                    found = False

                                # Zaderjka na sluchai not responding
                                for t in range(1, 30):
                                    if self.not_responding():
                                        log_print("Browser not responding, waiting 3 secs...")
                                        time.sleep(3)
                                    else:
                                        break

                                if self.status != 'LOST_CONNECT':
                                    self.status = self.get_app_status()

                                if self.is_connect_lost():
                                    return True

                                found = self.send_message(outbox)

                                self.ioerror_count = 0

                            except IOError, e:
                                self.job.exception(e)
                                if self.ioerror_count < self.max_ioerror_count:
                                    self.ioerror_count += 1
                                    log_print('try to send one more time (%d)' % self.ioerror_count)
                                    return True
                            except EDeadContainer:
                                log_print('container is not responding. breaking...')
                                return False
                            except Exception, e:
                                error_message = self.job.exception(e)
                                found = False
                                error = True

                            # Обработка файлов из очереди

                            log_print('remove %s' % os.path.split(filename)[1])
                            out_queue.remove_file(filename)

                            if not found:
                                try:
                                    error_data = {"channel_phone": self.device_number,
                                                  "client_phone": outbox['phone']}
                                    # response = requests.post(self.settings['api'] + '/wa_error', error_data)
                                    # log_print(response.status_code, response.reason, response.url, error_data)
                                    response = req.request('POST', self.settings['api'] + '/wa_error',
                                                           body=json.dumps(error_data).encode('utf-8'),
                                                           headers={'Content-Type': 'application/json'})
                                    log_print(response.status, response.reason, error_data)
                                except Exception, e:
                                    self.job.exception(e)
                            if filename:
                                try:
                                    if not found:
                                        log_print('append to not found %s' % outbox['phone'])
                                        out_queue.notfound.write_file(outbox, out_queue.get_prefix(outbox, '_F'))
                                finally:
                                    out_queue.remove_file(filename)

                            # Ограничение одновременно обрабатываемых файлов
                            outcount += 1
                            if self.outbox_limit and (outcount >= self.outbox_limit):
                                inbox_first_page = True
                                break

                    if not self.is_alive():
                        return True

                    # Прием сообщений
                    if self.status == 'ONLINE' and self.is_gateway_available:
                        # Оставить без всяких условий - будет кликать через 1 секунду.
                        # но тогда не будет пропускать сообщения, если диалог не сменился
                        if self.click_inbox:
                            self.sendNewMessages()

                        # Инициируем отправку сообщений если есть открытый диалог
                        if self.get_activechattitle():
                            self.sendNewMessages()

                        if not self.send_only:
                            self.click_unread(inbox_first_page)

                        if not self.send_only and self.unread_scan_period and (
                                self.get_delta(self.unread_scan_last).seconds > self.unread_scan_period):
                            self.scan_unread()
                            self.unread_scan_last = datetime.datetime.now()

                        # missed_calls = self.sync('%s.findMissedCalls(%s);' % (self.ep(), '%d'), PARAM1_JSPROC_SYNC)
                        # log_print('='*5, 'calls detected: ', missed_calls)

                    else:
                        log_print('appStatus = %s. skip clicking' % (self.status,))

                    if outbox_enabled and self.is_gateway_available:
                        # log_print('[ready for check status]')
                        try:
                            # response1 = requests.post(self.settings['api'] + '/macros/raw_statuses', {
                            #     "channel_phone": self.device_number, "transport": "whatsapp"
                            # })
                            response1 = req.request('POST', url=self.settings['api'] + '/macros/raw_statuses',
                                                    body=json.dumps({"channel_phone": self.device_number,
                                                                     "transport": "whatsapp"}).encode('utf-8'),
                                                    headers={'Content-Type': 'application/json'}
                                                    )
                            # log_print('[check status response]', response1.data, 'url', self.settings['api'] + '/macros/raw_statuses')
                            try:
                                # check_msgs = response1.json()

                                check_msgs = response1.data
                                check_msgs = to_str(check_msgs)
                                check_msgs = json.loads(check_msgs)

                                # log_print('[check status response json]', check_msgs)
                                for check_msg in check_msgs:
                                    self.set_status(u'Checking sent message status')
                                    log_print("---CHECKING STATUS OF: " + check_msg['client_phone'])
                                    self.check_status(check_msg)
                            except Exception as err:
                                log_print('=' * 5, 'ERROR CHECKING STATUS', err)
                                # log_print(response1.text)
                                log_print(response1.data)
                        except requests.exceptions.ConnectionError as err:
                            log_print('connection (status) %s' % err.message)
                            self.is_gateway_available = False
                            self.gateway_failed_time = time.time()
                        except Exception as err:
                            log_print(err.message)

                    if self.clear_enabled:
                        self.clearance()

                    if self.process_waiting_enabled:
                        self.process_waiting()

                    # self.press_button('esc')
                else:
                    log_print("Browser not responding, skipped 1 cycle")
                self.press_button('esc')

        except EDeadContainer:
            log_print('container is not responding. breaking...(2)')
            return False
        except Exception as e:
            self.job.exception(e, 'process_message')

        self.set_status(u'Idle')

        return True

    def get_dialog_qty(self):
        """ определение количества диалогов """
        try:
            pane_side = self.get_pane_side_coord()
            first_coord = self.get_first(pane_side[1], pane_side[1] + pane_side[3], self.css_chat)
            height = self.get_viewport_height()
            return height / first_coord[3]
        except:
            return 0

    # Закрытие всплывающих окон
    # R Избыточно, лучше заменить хоткеями с escape, хоткеи не фейлятся, в отличие от взаимодействия через прокликивание
    def close_popup(self):
        self.click_element(self.popup_button)

    # Функция дебага css, описывает периметр элемента
    def css_debug(self):
        try:
            rect = eval(self.sync("%s.getRect('%s')" % (self.ep(), self.test_css)))
            while True:
                pyautogui.moveTo(rect[0], rect[2] + self.chrome_offset_y)
                time.sleep(3)
                pyautogui.moveTo(rect[0], rect[3] + self.chrome_offset_y)
                time.sleep(3)
                pyautogui.moveTo(rect[1], rect[3] + self.chrome_offset_y)
                time.sleep(3)
                pyautogui.moveTo(rect[1], rect[2] + self.chrome_offset_y)
                time.sleep(15)
        except TypeError:
            log_print(
                'Failed to test css:| {} |, Cannot find element by css, or types of data not valid, RECT: {}'.format(
                    self.test_css, rect))
        except Exception as e:
            log_print('Failed to test css:| {} |, Exception raised: {}'.format(self.test_css, e))

    # Очередная функция клика по элементу, с рандомизацией
    # Кликает в рамках пермиетра с поправкой на отступы, т.к. на границах элементы некликабельны
    # Так же у чата в списке диалогов есть открытие контекстного меню, которое может прервать клик по диалогу
    # R Избыточно, лучше выкосить, сделано чисто из-за паранойи
    def click_element(self, css, revert_click=False, offset_click=0, default_offset_click=10):
        '''
        :param offset_click: отстутп клика от центра элемента
        :param default_offset_click: в случае если у экземпляра нет свойства offset_click
        '''
        try:

            if css == self.test_css:
                return self.css_debug()

            # log_print('Searching to click element', css)
            rect = eval(self.sync("%s.getRect('%s')" % (self.ep(), css)))
            # log_print('Searching to click element', css, 'coordinates:', rect)

            try:
                offset = offset_click or self.offset_click or 1
            except AttributeError:
                offset = default_offset_click
            # log_print('clicked on element', rect)
            # Координаты центра элемента
            x_1 = (rect[1] + rect[0]) / 2
            # y_1 = ((rect[3] + self.chrome_offset_y) + (rect[2]) + self.chrome_offset_y) / 2
            y_1 = (rect[3] + rect[2]) / 2 + self.chrome_offset_y
            offset_x = (offset / 100 * random.choice([-1, 1])) * (rect[1] - rect[0])
            offset_y = (offset / 100 * random.choice([-1, 1])) * (rect[3] - rect[2])
            x_1 = int(x_1 + offset_x / 2)
            y_1 = int(y_1 + offset_y / 2)
            # log_print('clicked on element point', x_1, y_1)
            if revert_click:
                self.rightClick(x_1, y_1)
            else:
                log_print('Searching to click element', css, 'el coords:', rect, 'coords to click:', x_1, y_1)
                self.click(x_1, y_1)
            return True
        except TypeError:
            if rect is None:
                log_print('Elemet\'s <{}> borders not found'.format(str(css)))
            else:
                log_print('Type Error!', TypeError.__doc__)
        except Exception as e:
            log_print('click element error', e)
            return False

    # Открытие диалога по ссылке
    def open_dialog_by_link(self, phone):
        if not self.link_send_enabled:
            return

        if not re.search('^[0-9]{%d,}$' % int(self.valid_link_phone_length), phone):
            return
        log_print('phone', phone)
        try:
            # return self.sync("%s.openByLink('%s', '%s')" % (self.ep(), phone, self.header_menu), PARAM1_JSCOMMAND_SYNC)
            return self.sync("%s.openByLinkResult(%s, '%s', '%s')" % (self.ep(), '%d', phone, self.header_menu), PARAM1_JSPROC_SYNC)
        except Exception as err:
            log_print('ERROR openByLink:', err)

    # Функция нажатия кнопки с интервалами и счетчиком, часто бывают конструкции в духе:
    # press esc
    # sleep 3
    # press esc
    # sleep 3
    # press esc 
    # sleep 3
    # Все это заменяется на 
    # press_button('esc', 3)
    # Так же возможно sleep_before избыточен, т.к. он эквивалентен sleep_after и сливается с ним при times > 1
    # R Возможно лучше во всех местах со sleep_before, если их немного проставить явный слип, а отсюда это выкосить
    def press_button(self, button, times=1, sleep_before=0.0, sleep_after=0.0):
        for i in range(times):
            time.sleep(sleep_before)
            pyautogui.press(button)
            time.sleep(sleep_after)

    # Проверка, можно ли удалять данный тип чата    
    def is_deletable(self, chat_type):
        if chat_type == "group":
            log_print('is {} deletable: {}'.format(chat_type, self.group_deletable))
            return self.group_deletable
        if chat_type == "broadcast":
            log_print('is {} deletable: {}'.format(chat_type, self.broadcast_deletable))
            return self.broadcast_deletable
        if chat_type == "base":
            log_print('is {} deletable: {}'.format(chat_type, True))
            return True
        return False

        # Удаление чата через хоткеи

    def delete_chat(self):
        pyautogui.hotkey('ctrlright', 'altright', 'backspace')
        time.sleep(self.after_chat_context_sleep)
        self.click_element(self.popup_button)
        time.sleep(self.after_chat_context_sleep)

    # Итерация по чатам при удалении
    def delete_item(self, chat_title=None):
        pyautogui.press('esc')
        pyautogui.press('esc')
        pyautogui.press('esc')
        time.sleep(1.5)
        # Получение типа чата
        chat_type = self.sync("%s.getCurrentChatType()" % self.ep())
        log_print('Chat type: ', chat_type)
        chat_title = chat_title or self.sync("%s.getActiveChatTitle()" % self.ep())
        log_print('Chat title: ', chat_title)

        if not self.is_deletable(chat_type):
            return False

        # Для групп удаление происходит 2 раза, т.к. первый вызов - выход из группы, второй - удаление
        if chat_type == "group":
            self.delete_chat()
            self.delete_chat()
            log_print(u'%s Deleted at: %s' % (chat_title, time.strftime('%H:%M:%S', time.localtime())))
            return True

        if chat_type == "broadcast":
            self.delete_chat()
            log_print(u'%s Deleted at: %s' % (chat_title, time.strftime('%H:%M:%S', time.localtime())))
            return True

        if chat_type == "base":
            self.delete_chat()
            log_print(u'%s Deleted at: %s' % (chat_title, time.strftime('%H:%M:%S', time.localtime())))
            return True

        return False

    def clear_path(self, d_path, days):
        """ удаляет все файлы в указаном пути, если они были модифицированы более чем N дней назад """
        path = d_path % self.device_number
        try:
            current_time = time.time()
            for f in os.listdir(path):
                c_file = path + f
                modification_time = os.stat(os.path.abspath(c_file)).st_ctime
                if (current_time - modification_time) // (24 * 3600) >= days:
                    log_print("removing: %s" % c_file)
                    os.remove(c_file)
                    log_print("removed: %s" % c_file)
        except Exception as e:
            pass

    def to_start_delete(self, non_deletable_chat_count=None, fast_scroll=False):
        '''
        Переход к старту удаления чатов
        :param non_deletable_chat_count:
        :param fast_scroll: быстрый переход к удаляемому чату (Js scroll)
        '''
        if non_deletable_chat_count is None:
            non_deletable_chat_count = self.non_deletable_chat_count + self.skipped_on_delete
        else:
            non_deletable_chat_count = non_deletable_chat_count + self.skipped_on_delete
        chat_height = self.get_chat_height()
        if fast_scroll:
            prev_scroll = non_deletable_chat_count - 10 if non_deletable_chat_count >= 10 else 0
            next_scroll = non_deletable_chat_count + 10
            self.scroll_paneside(prev_scroll * chat_height)
            time.sleep(1)
            self.scroll_paneside(next_scroll * chat_height)
            time.sleep(1)
            self.scroll_paneside(non_deletable_chat_count * chat_height)
        else:
            self.scroll_paneside(0)
            self.click_element(self.header_menu)
            for i in range(non_deletable_chat_count + 1):
                pyautogui.hotkey('ctrl', 'alt', 'shift', ']')
                self.scroll_paneside(non_deletable_chat_count * chat_height)
        return

    # Очистка списка диалогов
    def clearance(self):

        log_print('INSIDE CLEARANCE clear_enabled: %s' % self.clear_enabled)

        t = time.strftime('%H:%M', time.localtime())
        if self.clear_start_time and self.clear_end_time:
            if (self.clear_start_time < self.clear_end_time):
                if (t >= self.clear_end_time) or (t < self.clear_start_time):
                    return 0
            else:
                if (t >= self.clear_end_time) and (t < self.clear_start_time):
                    return 0
        # количество диалогов
        dialog_qty = self.get_dialog_qty()
        # log_print('[dialog qty]', dialog_qty)
        chat_height = self.get_chat_height()
        # количество не удаляемых диалогов
        # log_print('non del chats', self.non_deletable_chat_count, 'skiped', self.skipped_on_delete)
        # выход по количеству оставшихся диалогов
        if dialog_qty <= self.non_deletable_chat_count + self.skipped_on_delete:
            log_print("Mininal chat count reached")
            return
        cleared = 0
        # получим высоту списка диалогов (даже с учетом тех, которые не видно)
        viewport_height = self.get_viewport_height()
        # log_print('[viewport heigth]', viewport_height)
        # координата последнего проверенного чата - переходим для удаления нужного чата
        last_chat_coord_y = (self.non_deletable_chat_count + self.skipped_on_delete) * chat_height
        # log_print('[last chat coord]', last_chat_coord_y)
        # сразу перейдем на чат с которого начинается удаление
        self.to_start_delete(fast_scroll=True)
        # счетчик для подсчета пропущенных чатов - нужен для вычисления скролла к нужному чату при удалении
        local_skiped = 0

        # получаем координату верхнего чата в видимом списке чатов
        rect = self.sync("%s.inWindow(%s);" % (self.ep(), '%d'), PARAM1_JSPROC_SYNC)
        if rect in (0, '0', u'0'):
            log_print('DELETE RETUNED', rect)
            return
        # log_print('raw rect', rect)
        rect = [int(x) for x in json.loads(rect)]
        # log_print('rect', rect)
        x = (rect[1] + rect[0]) / 2
        y = ((rect[3] + self.chrome_offset_y) + (rect[2]) + self.chrome_offset_y) / 2
        # log_print('coords', x, y)
        # цикл с удалением чатов
        for i in range(dialog_qty - self.non_deletable_chat_count - self.skipped_on_delete):
            # log_print('[click on top dialog]', i + 1, 'range', dialog_qty - self.non_deletable_chat_count - self.skipped_on_delete)
            # time.sleep(1)
            # log_print('vp heigth', viewport_height, 'last y', last_chat_coord_y)
            if viewport_height - last_chat_coord_y < chat_height * 6:
                y += 72
                # log_print('yes, inc y, y=', y)
            # self.moveTo(x, y, duration=0.5)
            self.click(x, y)
            time.sleep(1.5)
            deleted = self.delete_item()
            if not deleted:
                self.skipped_on_delete = self.skipped_on_delete + 1
                local_skiped += 1
            else:
                # если чат удалился, то получим новую высоту списка диалогов
                viewport_height = self.get_viewport_height()
                pass
            # last_chat_coord_y += 72 * (1 + local_skiped)
            last_chat_coord_y += 72
            self.scroll_paneside(last_chat_coord_y)
            cleared = cleared + 1
            self.set_status(u'Deleting dialogs', '%d remaining' % (self.clear_limit - cleared))
            if cleared >= self.clear_limit:
                log_print("CLEAR LIMIT REACHED")
                break
        self.goto_first()


class debug_message_processor(message_processor):

    def typewrite_phone(self, phone):
        self.type_write_click(phone, self.search_editable)
        time.sleep(2)


if __name__ == "__main__":
    p = message_processor('2222')
    print filename_replace('figovoe/imay')
