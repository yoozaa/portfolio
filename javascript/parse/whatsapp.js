// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! //
// Теги комментариев                                          //
// //A - обрати внимание, может быть нарушение работы кликера //
// //R - требуется рефакторинг                                //
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! //
//R Общие рекомендации к рефакторингу
// 1) Все параметры надо вынести в Python и передавать в качестве аргументов функции
// поскольку сейчас в Python модуле происходит переопределение параметров при перезагрузке и запуске,
// либо найти способ не терять данные при этих событиях, какой-нибудь внешний js-модуль, доступный для редактирования саппортам
// 2) Повысить уровень абстракции, сделать общие функции, возвращающие данные
// 3) Упростить механизм присваивания айдишников, сейчас там сложная логика
// 4) Попытаться обновить cef & cef4delphi & delphi, поскольку многие функции js из коробки не работают/работают не так, как ожидается
// к примеру, клик на 2 элементах подряд, на колбеках, промисах, таймаутах, интервалах - работает из консоли, но не работает из скрипта
// это могло бы сильно упростить логику кода и минимизировать его, что крайне важно


// Основной скоуп(блок), вешается на window, доступен по паролю 'vlad', можно вызвать любую функцию/получить поле через консоль
// Пример: w(vlad).clicker_version - выведет версию, которая указана парой строк ниже
w(new function () {

    // Делаем шорткат на this, для единообразия кода с python-модулем
    //R избыточно, желательно откатить до this, посмотреть как будет с этим работать sync
    var self = this;

    // Версия кликера, выводится в плашке со статусом
    self.clicker_version = "v3.70";
    self.suppressed = {};


    // Запись в локал сторадж, необходима для присваивания айдишников сообщений и загрузки файлов
    // а так же доп. параметров, например счетчик пропуска аватарок клиента
    self.localStorage_setItem = function (key, value) {
        if (self.settings.send_only) {
            return true
        }
        self.console_log('localStorage_setItem ' + key + ' ' + value);
        return localStorage.setItem(key, value);
    };

    // Получение из локал стораджа
    self.localStorage_getItem = function (key) {
        let value = localStorage.getItem(key);
        if (self.settings.suppress) {
            let v = self.suppressed[key];
            if (v !== value) {
                self.suppressed[key] = value;
                if (key !== 'appStatus') {
                    self.console_log('localStorage_getItem', key, value);
                }
            }
        } else {
            if (key !== 'appStatus') {
                self.console_log('localStorage_getItem', key, value);
            }
        }
        return value;
    };

    self.makeTime = function (rawString) {
        let found = rawString.match(/\d+:\d+\s?[amp]*/i);
        if (found === null) {
            return ''
        }
        let result = found[0].split(':');
        let tableAM = {
            "12": "0"
        };
        let tablePM = {
            "1": "13",
            "2": "14",
            "3": "15",
            "4": "16",
            "5": "17",
            "6": "18",
            "7": "19",
            "8": "20",
            "9": "21",
            "10": "22",
            "11": "23",
            "12": "12"
        };
        if (/\s*AM/i.test(rawString)) {
            result = found[0].replace(/\s*AM/ig, '');
            result = result.split(":");
            result[0] = tableAM[result[0]] || result[0];
            if (result[0].length === 1) {
                result[0] = `0${result[0]}`
            }
        }
        if (/\s*PM/i.test(rawString)) {
            result = found[0].replace(/\s*PM/ig, '');
            result = result.split(":");
            result[0] = tablePM[result[0]];
        }
        if (result[0].length === 1) {
            result[0] = `0${result[0]}`
        }
        if (result[1].length === 1) {
            result[1] = `0${result[1]}`
        }
        return result.join(":")
    };

    self.consts = {
        // Статусы
        status: {
            // Запуск
            STARTING: 'STARTING',
            // Лострег
            LOST_REGISTRATION: 'LOST_REGISTRATION',
            // Потеря соединения
            LOST_CONNECT: 'LOST_CONNECT',
            ONLINE: 'ONLINE',
            SIGNIN: 'SIGNIN',
            OFFLINE: 'OFFLINE'
        },
        // Вспомогательные поля
        ls: {
            // В основном это префиксы для записи данных в локал сторадж
            devicePhone: 'devicePhone',
            qr_data_ref: "qr-data-ref",
            appStatus: "appStatus",
            // Префикс счетчика аватарки, счетчик аватарки клиента с номером 123 будет записан как avacount-123
            // логика работы со счетчиком описана далее в коде
            avacount: 'avacount-'
        },
        //R избыточно
        method: {
            https: 'https://',
            qrcode: '/wa/qrcode',
            status: '/?r=wa/status',
            log: '/wa-log.php',
            receiver: '/?r=wa/receiver'
        },
        css: {
            data_id: 'data-messageid',
            data_url: 'data-url',
            broadcast: 'broadcast'
        }
    };

    // Типы ответа при синхронном вызове, так же в некоторых местах возвращаются явно
    //R заменить явные возвраты
    // Пример обработки типа ответа можно увидеть в sendNewMessages, к примеру, ожидание загрузки картинки,
    // или любого цикла с последующим вызовом инициатора будет при reject_reason < 0
    self.reject_reason = {
        reason_scan_once: -1,
        reason_wait_for_message: -2,
        reason_screenshot: -10,
    };

    self.settings = {
        // Ссылка на гейт
        gateway: 'https://gateway.chat2desk.com',
        // Ссылка на основной сервис
        helpdesk: 'https://web.chat2desk.com',

        // Режим отключения приема сообщений,
        // перезаписывается если в настройках python указывается true
        send_only: false,

        // прозрачность плашки с версией
        opacity: 0.9,

        // Задержка перед приемом видео, время на его прогрузку
        video_timeout: 2000,
        // Параметр включения/отключения приема видео
        video_enabled: true,
        // Дополнительный уровень логгирования
        //R Не актуален, надо выпилить
        verbose: true,
        suppress: true,
        // Таймаут приема контакта?
        contact_timeout: 3000,
        // Селектор кнопки отмены загрузки картинки, т.е. признак того, что картинка грузится
        image_loading_css: '[data-icon="media-disabled"], circle',
        // Аналагично с документом
        document_loading_css: '[data-icon="audio-cancel-noborder"]',
        // Отправка автоответа?
        autoanswer: false,
        // Сообщения, которые подргружаются самим вотсаппом, выводится плашка со спец. текстом вместо сообщения
        waiting_css: '[data-icon="ciphertext"]',
        // Селектор сообщения
        msg_css: '.FTBzM, .GDTQm, ._2wUmf',
        msg_bubble: '._24wtQ, .cvjcv',
        // Селектор уведомления о разряженном аккамуляторе, необходимо его убирать, поскольку он может преравть отправку сообщения
        // Пример: при появлении сдвинет список диалогов вниз, если координата первого диалога уже была выщитана, то клик придется на
        // уведомление, вместо диалога, сообщение не отправится
        charge_popup: "._3O0po, .m6ZEb",
        // Селектор кнопки проигрывания видео
        play_video_css: "[data-icon=media-play]",
        // selector to preview contact card
        contact_preview_btn: '._1I1xx[role=button], ._2GhDW[role=button]',
        // contact card for parse data
        contact_card: '._36Jt6, .KPJpj',
        // Таймаут открытия карточки клиента
        client_card_timeout: 1500,
        // Получение имени нового клиента из карточки
        get_name_enable: true,
        // Искать сообщения только после последнего входящего сообщения
        // after_last_out_only: false,
        // Таймаут прокликивания изображений в блоке, мсек
        wrapped_images_click_timeout: 500,
        // Разрешить отправку свернутых картинок
        wrapped_enable: true,
        // задержка перед кликом по блоку с изображениями
        wrapped_block_click: 500,
        // после клика на закрузку первого изображения в блоке (если не прогрузилось сразу)
        wrapped_first_not_loaded: 2000,
        // задержка перед тем как отправить изображение, мсек
        // через это время кликер снова найдет все урлы у картинки и скачает с последнего
        image_download_delay: 3000,
        // формат таймлана
        // timeline_format: "mm dd yyyy",
        // время ожидания результата перехода по ссылке, сек
        open_by_link_timeout: 20,
    };

    self.css = {
        // Селектор выбранного группового чата, может ничего не вернуть,
        // поскольку выбранный чат может быть не групповым
        active_chat_group: ".fBf_N [data-icon=default-group], ._23P3O [data-icon=default-group]",
        // Селектор выбранного чата рассылок
        active_chat_broadcast: ".fBf_N [data-icon=default-broadcast], ._23P3O [data-icon=default-broadcast]",
        // Селектор архивного чата
        archive_chat: "._2EXPL:has(._15G96._3JEcM), ._2nY6U:has(._1pJ9J._3f7yK)",
    };

    // Функция логгирования
    //R Не знаю как она логгирует, лучше использовать console.log() из коробки
    self.console_log = function (...a) {
        if (self.settings.verbose) {
            self.logInfo(a.join(' '));
        }
    };

    self.css_settings = {
        // Функция поиска элементов
        get_elements: function (css_selector) {
            let r;
            if (typeof (css_selector) !== 'string') {
                r = $(css_selector[0]).find(css_selector[1])
            } else {
                r = $(css_selector);
            }
            return r;
        },
        group_css: '._23P3O [data-icon=default-group]',
        // Селектор чата
        css_chat: '.eJ0yJ, ._3Pwfx, ._2aBzC, ._2Z4DV, ._2nY6U',
        // уведомление проверить подключение телефона к интернету
        lost_connect: '._22XJC._3C1U5',
        // Наличие этого элемента показывает, что приложение еще не запущено.
        // whatsapp еще не прогрузил веб приложение
        startup: '#startup',
        // Определение статуса приложения
        popup_window: '._3NCh_, ._3J6wB',
        popup_start_chat: '._1bpDE',
        status: {
            lost_registration: '[data-ref]',
            lost_connect: '._22XJC._3C1U5',
            online: '#pane-side',
            signin: '#window'
        },
        // Элементы внутри qrcode
        lost_registration: {
            // Кнопка для перезагрузки qrcode
            // button: '[data-icon]',
            button: 'nope',
            // Картинка с qrcode
            img: 'img',
            // Название атрибута элемента status_lost_registration, где хранится значение кода
            data_ref: 'data-ref'
        },
        // Пропущенные звонки
        missed_calls: {
            missed: '.GDTQm._397qe:has([data-icon=miss]), ._2wUmf.V-zSs:has([data-icon=miss])',
            missed_video: '.GDTQm._397qe:has([data-icon=miss_video]), ._2wUmf.V-zSs:has([data-icon=miss_video])',
            bubble: '._24wtQ._2kR4B, .cvjcv.EtBAv',
            text: '[dir=ltr]',
            name: 'CALL',
            audio: {
                idname: 'ACALL_',
                name: 'ACALL',
                inside_element: '.xxx',
            },
            video: {
                idname: 'VCALL_',
                name: 'VCALL',
                inside_element: '.xxx',
            },
        },
        wrapped_images: {
            wrapped: '.GDTQm.message-in[data-id^=album], ._2wUmf.message-in[data-id^=album]', // признак свернутого сообщения
            images_in_wrapped: '._2IsiC, .-dRqA', // видимые сообщения в свернутом блоке
            hidden_count: '.qpqWq._1Yoli, ._3WYXy.VWPRY._1lF7t.WrYa3', // количество элементов в альбоме
            download_btn: '[data-icon="media-download"], button, image-thumb-lores', // первое изображение не прогрузилось
            // image: '.vahb0 img, .rN9sv img', // элемент изображение
            image: '._3WrZo._1SkhZ._3-8er, ._2dXkT._1ctu4.i0jNr', // элемент изображение
            video: '._3WrZo video, ._2dXkT video', // элемент видео
            next_btn: 'span [data-icon=chevron-right]', // пролистывание сообщений вперед
            prev_btn: 'span [data-icon=chevron-left]', // пролистыванеие сообщений назад
            close_btn: '[data-icon="x-viewer"]', // закрытие окна просмотра элементов в блоке
            date: '._2vfYK, ._1qB8f', // div с инфо, в т.ч. дата отправки, напр-р <сегодня в 9:20>
            bubble: '._24wtQ, .cvjcv',
            buttons: '._1ljzS [role=button], ._2OBzR [role=button]', // меню при пролистывании сообщений в блоке
            download_menu: '._1qAEq._11bi2, .o--vV.wGJyi', // раскрытое меню сообщения
        },
        basket: {
            bubble: '._1ij5F._3BV2U, ._24wtQ._1JXbp',
            idname: 'BASKET_',
            name: 'BASKET',
            show_button: '._2fS0O[role="button"], ._34JD_[role=button]',
            back_button: '[data-icon=back]',
            timeout: 1000,
            opened: '._3Xjbn._1RHZR, ._1C2Q3._36Jt6',
            shop_name: '._2Qgdf, ._1ofix',
            amount: '._2chLL, ._1eJr5',
            text: '._1wlJG._1xUAc ._1VzZY, ._3ExzF._3v99V ._3-8er',
            // time_main: '._3pDbE',
            goods: '._1MZWu, ._2aBzC',
            img_div: '.rvMOn, .Xh_zm'
        },
        // определение списка сообщений для приема
        messages: {
            // inbox: '#main ' + self.settings.msg_css + ':has(.message-in)',
            inbox: '#main ' + self.settings.msg_css + '.message-in',
            outbox: '#main ' + self.settings.msg_css + '.message-out',
            // Определение времени получения сообщения
            // inbox_datetime: '.message-datetime',
            inbox_datetime: '._3fnHB, ._3EFt_, ._18lLQ, ._2JNr-, ._17Osw, .kOrB_',
            // inbox_nextall: ':has(.message-in .message-text, ._1zGQT.a7otO.tail), :has(.message-in.message-text, ._1zGQT.a7otO.tail)',
            inbox_nextall: '.message-in, .FTBzM._3CGDY:has([data-icon=miss]), .vW7d1._3rjxZ:has([data-icon=miss])',
            // Отправка выбранных сообщений
            selected_messages: '#main ' + self.settings.msg_css + '.message-in:has(._3yThi.UF5Li)',
            // Для inbox выбираются только сообщения с data-id
            // Исключаем .image-caption - он идет с гео вместе с data-id
            //css
            inbox_exclude: '.image-caption, .not-for-send',
            //css
            quoted_message_text: '.text-quote .quoted-mention, .quoted-mention',
            // [role] для отсекания заголовка с автором
            //css
            selectable_text: '.selectable-text:not([role])',
            //css
            selectable_in_selectable_text: '.selectable-text:not([role]) .selectable-text:not([role])',
            // Элементы в текстовых сообщениях заменяются на текст из атрибута alt
            //css
            smiles: 'img.emoji, img.single-emoji, img.large-emoji, img.selectable-text',
            types: {
                text: {
                    // _3_7SH _3DFk6 message-in
                    bubble: '.bubble-text,.message-chat, ._24wtQ._2W7I-, .cvjcv._1Ilru',
                    idname: "TEXT_",
                    name: "TEXT",
                    inside_element: '.xxx',
                    // кнопка раскрытия длинного сообщения
                    read_more: 'span[role=button]._3WiqP, span[role=button]._208p2'
                },
                image: {
                    // _3_7SH _3qMSo message-in tail
                    bubble: '.bubble-image,.message-image, ._24wtQ.gZ4ft, .cvjcv._3QK-g',
                    // к idname прибавляется префикс, который потом определяется phone.data_id_short_pattern
                    idname: "IMAGE_",
                    name: "IMAGE",
                    //css
                    inside_element: '.image-thumb-body',
                    // блок в котором находится изображение сообщения
                    wrapper_div: '._1VwF0, ._3IfUe',
                    preview_img: '._2p30Q, .mFB5y',
                    // цитируемая картинка в сообщении
                    quoted: '._2UMoT, .Y2pgK, ._3e0Yi, .fX8hW'
                },
                location: {
                    // _3_7SH _1OI2B message-in
                    bubble: '.message-location, ._24wtQ._2KgTl, .cvjcv._3Y4UU',
                    idname: "MAP_",
                    name: "MAP",
                    inside_element: '.image-thumb img',
                    pattern: /(-?\d+\.\d+),(-?\d+\.\d+)/,
                    lat_index: 1,
                    lng_index: 2
                },
                audio: {
                    //FTBzM _17BiH message-in
                    // bubble: '._1zGQT.xPyAe,.bubble-audio,.message-ptt',
                    bubble: '.bubble-audio,.message-ptt, ._24wtQ._2Ye7z, .cvjcv.JZd-w, .cvjcv._2G-o1',
                    idname: "AUDIO_",
                    name: "AUDIO",
                    inside_element: 'audio'
                },
                video: {
                    // _3_7SH _3In2e message-in
                    bubble: '.bubble-video,.message-video, ._24wtQ._117Hx, .cvjcv._3bxPY',
                    idname: "VIDEO_",
                    name: "VIDEO",
                    inside_element: '.image-thumb-body',
                    download_btn_disable_class: '_3Ppmx'
                },
                video_gif: {
                    bubble: '._1ij5F._9pOn1, ._24wtQ._3UH4z, .cvjcv._29jDW',
                    play_btn: '[data-testid="media-state-gif-icon"]',
                    idname: "VIDEO_",
                    name: "VIDEO_GIF",
                },
                document: {
                    // _3_7SH _1ZPgd message-in
                    bubble: '.bubble-doc,.message-document, ._24wtQ.Hrc6x, .cvjcv._1CJ4I',
                    idname: 'DOC_',
                    name: "DOC",
                    inside_element: 'a.document_container'
                },
                contact: {
                    // _3_7SH kNKwo message-in
                    bubble: '.bubble-vcard,.message-vcard, ._24wtQ.i29yA, .cvjcv._3Q9cR',
                    idname: 'CONTACT_',
                    name: "CONTACT",
                    inside_element: '.XXX'
                },
            }
        },
        // Определение номера телефона по данным аттрибута data-id
        phone: {
            data_id_short_pattern: /(us_.*)/,
            data_id_short_index: 1
        },
        avatar: {
            // avaimg: '._1SwuT > div._3RWII > img'
            // avaimg: "#main > header > div._18tv- > div > img"
            avaimg: "#main > header > div > div > img"
        },
        chat_props: {
            active_title: '#main header [title]',
            // chat_title: '._19vo_ > ._19RFN'
            chat_title: '._2KQyF ._35k-1._1adfa._3-8er, ._23P3O ._ccCW.FqYAR.i0jNr'
        },
        get_name: {
            // Кнопка открытия карточки клиента
            open_btn: '#main header .fBf_N[role="button"], #main header ._24-Ff[role="button"]',
            // Селектор карточки
            // card: '._3HZor._1C9rS',
            card: '._1kkcj, ._2YEfx',
            // Блок с именем, аватаркой и телефоном
            card_top: '._3ZEdX._3hiFt.bRenh, ._2P1rL._1is6W.RVTrW',
            // div в котором span с текстом имени
            name_div: '._1TFjN, ._3l1_9',
            // Span в ктором непосредственно находится имя клиента
            name_span: 'span[dir="auto"]',
            // Кнопка закрытия карточки клиента
            close_btn: '._27F2N, ._18eKe'
        },
        // проставление телефона/имени в групповом чате
        group_chat_names: {
            // блок с телефоном и именем в сообщении
            phone_name: '._26iqs, ._1B9Rc',
            // телефон
            phone: '.ZJv7X[role=button], ._1BUvv[role=button]',
            // имя
            name: '._2F1Ns._35k-1.eHxwV._3-8er[dir=auto], ._1u3M2._ccCW._3xSVM.i0jNr[dir=auto]',
            // проставляемый аттрибут с именем
            nickname_attr: 'nickname',
            // проставляемый аттрибут с телефоном
            phone_attr: 'phone',
            // класс означающий что телефон/имя проставлены
            mark_class: 'withNickname'
        },
        // получение статуса сообщения
        message_status: {
            // ьлок с иконкой статуса сообщения
            acknowledge: '._1Tnge, ._2qo4q',
            check: '[data-icon="status-check"]',
            dbl_check: '[data-icon="status-dblcheck"]',
            dbl_check_ack: '[data-icon="status-dblcheck-ack"]',
            // read: '_2RFeE'
            read: '_3NIfV'

        }
    };

    /*Информация о загрузках документов*/
    self.documentinfo = {
        current_id: '',
        urls: {},
        set_current_url: function (url, text) {
            self.documentinfo.urls[self.documentinfo.current_id] = {'url': url, 'text': text};
            self.console_log('set_current_url', self.documentinfo.current_id, url, text);
            return true;
        },
        get_url: function (data_id) {
            if (self.documentinfo.urls[data_id]) {
                return self.documentinfo.urls[data_id].url;
            }
            return undefined;
        },
        get_text: function (data_id) {
            if (self.documentinfo.urls[data_id]) {
                return self.documentinfo.urls[data_id].text;
            }
            return undefined;
        }
    };

    // Функция генерации хеша, значение запишется в whatsapp.db3, далее будет фильтрация по хешу
    // сообщения с уже записанным хешем не уйдут повторно - защита от дублей
    self.hashCode = function (time, message, blob) {
        // let date = `${time}${new Date().getDate()}${new Date().getMonth()}`;
        let date = `${time}`; // добавление месяца и дня сломает хэш - при считывании сообщения в другой день хэши у одного и того же сообщения будет разный
        let blobSliced = blob ? blob.slice(-100) : '';
        let prepareForHash = `${blobSliced}${message}${date}`;
        return prepareForHash.split("").reduce(function (a, b) {
            a = ((a << 5) - a) + b.charCodeAt(0);
            return a & a
        }, 0)
    };

    // Добавление стилей на страницу, очень удобно для сокрытия различных элементов
    self.addStyles = function () {
        return $('body').append(
            "<style>" +
            // Добавляем кастомный стиль - подсветка зеленым, этот класс навешивается при приеме сообщения
            ".chat[broadcast] {background-color: lightgreen;}" +
            // Кастомный стиль на сокрытие попапа с уведомлением о разряде телефона, селектор вынес в параметр, на случай смены разметки
            self.settings.charge_popup + "{display: none;}" +
            "</style>"
        )
    };

    // Получение телефона из локал стораджа
    self.getPhone = function () {
        return localStorage.getItem(self.consts.ls.devicePhone);
    };

    // Отправка статуса кликера на гейт
    self.sendAppStatus = function (status) {
        return new Promise(function (resolve, reject) {
            if (self.localStorage_getItem(self.consts.ls.appStatus) === status) {
                resolve();
                return;
            }
            self.logInfo("App changed status from " + self.localStorage_getItem(self.consts.ls.appStatus) + " to " + status);
            ajax_post({
                    type: 'GET',
                    url: self.settings.gateway + self.consts.method.status,
                    data: {
                        status: status,
                        devicePhone: self.getPhone()
                    }
                },
                {
                    'always': function (result) {
                        if (result.code === 200) {
                            //сохраняем статус только в случае, если сервер принял его
                            self.localStorage_setItem(self.consts.ls.appStatus, status);
                        }
                        resolve();
                    }
                })
        });
    };

    // Корневая функция, начало инициализации
    $(document).ready(function () {
        self.sendAppStatus(self.consts.status.STARTING);
        setTimeout(
            function () {
                self.readyLog().then(function () {
                    self.startAll();
                });
            }, 1000);
    });

    self.elements = function (elname) {
        return self.css_settings.get_elements(elname);
    };

    self.element_exists = function (elname) {
        return self.elements(elname).length > 0;
    };

    self.readyLog = function () {
        return new Promise(function (resolve, reject) {
            let processing = function (proc, resolve) {
                if (self.elements(self.css_settings.startup).length === 0) {
                    resolve();
                } else {
                    setTimeout(function () {
                        proc(proc, resolve);
                    }, 1000);
                }
            };
            processing(processing, resolve);
        });
    };

    // Инициализация
    self.startAll = function () {
        self.logInfo("Started");
        self.logInfo(`CLICKER VERSION ${self.clicker_version}`);
        self.showVersion();
        self.addStyles();
        // Проверка статуса
        self.checkAppStatus();
        for (let key in self.settings) {
            self.logInfo(`${key} ${self.settings[key]}`);
        }
    };

    // Вывод версии, просто лепим плашку с инфой
    self.showVersion = function () {
        if ($('#remain').length === 0) {
            $('body').append(`<div style="display: block; z-index: 999; position: absolute; background-color: whitesmoke; line-height: 20px;
                         font-size: 12px; left: 65px; border: 1px solid gainsboro; width: auto; height: auto; padding: 5px; margin-top: 5px; pointer-events: none; opacity: ${self.settings.opacity};"
                         id="version"><span id="device_phone"></span><br><span id="clicker_version"></span><br><span id="qty">0/0</span><br /><span id="log">Idle due to service not running</span>
                         <br /><span id="remain"></span></div>`);
            document.getElementById("device_phone").textContent = "[" + self.getPhone() + "]"
            $("body").append("<style></style>")
            return document.getElementById("clicker_version").textContent = self.clicker_version
        }
    };

    // Получение статуса приложения
    self.getAppStatus = function () {
        // self.console_log('getAppStatus');
        if (self.element_exists(self.css_settings.status.lost_registration)) {
            return self.consts.status.LOST_REGISTRATION;
        } else if (self.element_exists(self.css_settings.status.lost_connect)) {
            return self.consts.status.LOST_CONNECT;
        } else if (self.element_exists(self.css_settings.status.online)) {
            return self.consts.status.ONLINE;
        } else if (self.element_exists(self.css_settings.status.signin)) {
            return self.consts.status.SIGNIN;
        } else {
            return self.consts.status.OFFLINE;
        }

    };

    // Коллбек на пайтон (скорее на делфи), чтоб вызвать физический клик из JS?
    self.click_element = function ($element) {
        self.console_log('click element', $element.length);
        if ($element) {
            if ($element.length > 0) {
                let offset = $element.offset();
                if (offset) {
                    let x = parseInt(offset['left'], 10);
                    let y = parseInt(offset['top'], 10);
                    let w = $element.width();
                    let h = $element.height();
                    self.logInfo('clickelement ' + x + ' ' + y + ' ' + w + ' ' + h);
                    return mouse_click(x, y, w, h);
                }
            }
        }
        return false;
    };

    // TODO: не знаю где используется
    self.findInPainSide = function (title) {
        console.log('title', title);
        let chat = $('._2UaNq:not(._2J5yE)').has('._19RFN').find(`[title="${title}"]`);
        if (chat.length > 0) {
            chat.get(0).scrollIntoView()
        }
        let coords = chat.get(0).getBoundingClientRect();
        console.log(`search ${title} in pain-side > ${chat.length}, top ${coords.top}`);
        // проверим что скролл выполнен верно и чат в окне (800х600)
        if (coords.top < 600) {
            self.click_element(chat)
        }

    };

    // Проверка статуса приложения
    self.checkAppStatus = function () {
        let status = self.getAppStatus();
        let interval = 1000 * 5;
        if (status === self.consts.status.LOST_REGISTRATION) {
            interval = 1000;
            let qrcode = self.elements(self.css_settings.status.lost_registration);
            if (qrcode.length > 0) {
                let data_ref = qrcode.attr(self.css_settings.lost_registration.data_ref);
                if (self.localStorage_getItem(self.consts.ls.qr_data_ref) !== data_ref) {
                    self.logInfo('qr code changed');
                    self.localStorage_setItem(self.consts.ls.qr_data_ref, data_ref);
                    let src = qrcode.find(self.css_settings.lost_registration.img).attr('src');
                    if (!src) {
                        let canvas = document.querySelector('canvas');
                        src = canvas.toDataURL();
                    }
                    self.sendqrcode(data_ref, src);
                }
            }
        } else {
            if (self.localStorage_getItem(self.consts.ls.appStatus) === self.consts.status.LOST_REGISTRATION) {
                self.localStorage_setItem(self.consts.ls.qr_data_ref, 'XXX');
            }
        }
        self.sendAppStatus(status).then(function () {
            setTimeout(self.checkAppStatus, interval);
        });
    };

    // Отправка qr-кода
    self.sendqrcode = function (data_ref, src) {
        return new Promise(function (resolve, reject) {
            if (!data_ref || !src) {
                self.logInfo('data_ref or src empty' + ' data_ref: ' + data_ref + ' src: ' + src);
                resolve();
                return;
            }
            self.logInfo('sending qrcode');
            ajax_post({
                    type: 'POST',
                    url: self.settings.helpdesk + self.consts.method.qrcode,
                    data: {
                        data_ref: data_ref,
                        devicePhone: self.getPhone(),
                        time: Date.now() / 1000 | 0,
                        qrBlob: src
                    }
                },
                {
                    'always': function (result) {
                        if (result.code === 200) {
                            self.logInfo('qrcode received');
                        } else {
                            self.logInfo('qrcode failed to send ' + result.code.toString());
                        }
                        resolve();
                    }
                })
        });
    };

    // Логгирование в лог
    self.logInfo = function (clientPhone, text) {
        if (text === undefined) {
            text = clientPhone;
            clientPhone = "COMMON";
        }
        self.logAjax(text, 'INFO', clientPhone);
    };

    // Логгирование на сервер
    self.logError = function (clientPhone, text) {
        if (text === undefined) {
            text = clientPhone;
            clientPhone = "COMMON";
        }

        console.error("[" + clientPhone + "] " + text);
        self.logAjax(text, 'ERROR', clientPhone);
        self.logAjax(text, 'ERROR', clientPhone, true);
    };

    /*
      commonLog - признак общего файла для логгирования.
      Сделано для сборка ошибок в одном файле.
    */
    self.logAjax = function (text, level, clientPhone, commonLog) {
        let devicePhone = self.getPhone();

        if (commonLog === true) {
            text = '[' + devicePhone + '] ' + text;
            devicePhone = 'COMMON';
        }

        ajax_post({
            type: 'POST',
            url: self.settings.gateway + self.consts.method.log,
            data: {
                log: text,
                level: level,
                devicePhone: devicePhone,
                clientPhone: clientPhone
            }
        });
    };

    // Получить все входящие в диалоге
    self.getAllInboxMessages = function () {
        return self.elements(self.css_settings.messages.inbox);
    };

    // Получить все сообщения в диалоге (вх + исх)
    self.getAllMessages = function () {
        return self.elements(`${self.css_settings.messages.inbox}, ${self.css_settings.messages.outbox}`);
    };

    // Фильтрует сообщения для отправки - выбирает только
    self.filterAfterLastOut = function (allMessages) {
        // находим последнее исходящее
        let lastOut = allMessages.filter(self.css_settings.messages.outbox).last();
        // если не нашли последнее исходящее, то ищем все входящие
        let messagesAfterLastMessageOut = lastOut.length > 0
            ? lastOut.nextAll(self.css_settings.messages.inbox)
            : self.getAllInboxMessages();
        console.log('last out>', lastOut);
        console.log('messagesAfterLastMessageOut>', messagesAfterLastMessageOut);
        return messagesAfterLastMessageOut
    };

    // Ищет пропущенные звонки в открытом чате
    self.getMissedCalls = function () {
        let result = self.elements(`${self.css_settings.missed_calls.missed},
         ${self.css_settings.missed_calls.missed_video}`);
        // console.log(result);
        // добавить класс входящего сообщения звонкам
        if (result.length > 0) {
            for (let msg of result) {
                // console.log(msg);
                msg.classList.add('message-in')
            }
        }
        return result
    };

    // Ищет сообщения - корзину товаров
    self.getBasket = function ($inboxMessages) {
        if ($inboxMessages) {
            return $inboxMessages.find(self.css_settings.basket.bubble)
        }
        return $(self.css_settings.messages.inbox).find(self.css_settings.basket.bubble)
    };

    // Ищет блоки свернутых изображений
    self.getWrappedImages = function ($inboxMessages) {
        if ($inboxMessages) {
            return $inboxMessages.filter(self.css_settings.wrapped_images.wrapped)
        }
        return $(self.css_settings.wrapped_images.wrapped)
    };

    // Ищет изображения (видимые) в свернутом блоке
    self.getImagesFromWrapped = function (wrapped) {
        return wrapped.last().find(self.css_settings.wrapped_images.images_in_wrapped);
    };

    // клик по первому изображению в свернутом блоке
    self.clickWrapped = function (wrapped) {
        let hiddenImgCount; // сколько скрытых изображений (это число больше на 1 чем фактическое)
        let firstNotLoaded = false; // (not used) первое изображение не загрузилось
        // проверяем в последнем видимом изображении блока наличие ниличие информации о скрытых изображениях, напр-р +2
        if (wrapped.last().text() && wrapped.last().text().startsWith('+')) {
            hiddenImgCount = parseInt(wrapped.last()[0].textContent);
            // если их нет, то выставляем 1
        } else {
            hiddenImgCount = 1
        }
        // console.log('click wrapped', hiddenImgCount);
        let stillLoading = wrapped.first().find(self.settings.image_loading_css);
        let downloadBtn = wrapped.first().find(self.css_settings.wrapped_images.download_btn);
        // если есть кнопка загрузки на первом изображении в блоке (оно не прогрузилось),
        // то кликаем на втором изображении и затем кликаем влево
        return new Promise(function (resolve, reject) {
            // if (stillLoading.length > 0) {
            //     self.logError('Image in album still loading');
            //     reject(-1)
            // }
            setTimeout(() => {
                if (stillLoading.length > 0) {
                    self.logError('Image in album still loading');
                    reject(-1)
                }
                wrapped[0].scrollIntoView();
                if (downloadBtn.length > 0) {
                    self.console_log(`first not loaded`);
                    setTimeout(() => {
                        console.log(`Click on second`);
                        self.console_log(`Click on second`);
                        // $(wrapped[1]).find('img').click();
                        console.log('click on image 2');
                        self.click_element($(wrapped[1]));
                        setTimeout(() => {
                            let prevButton = $(self.css_settings.wrapped_images.prev_btn);
                            // $(prevButton).click();
                            self.click_element($(prevButton));
                            resolve({hiddenImgCount: hiddenImgCount, firstNotLoaded: firstNotLoaded})
                        }, self.settings.wrapped_first_not_loaded)
                    }, self.settings.wrapped_block_click)
                } else {
                    setTimeout(() => {
                        console.log('click on image 1');
                        // wrapped.first().find('img').click();
                        self.click_element(wrapped.first());
                        resolve({hiddenImgCount: hiddenImgCount, firstNotLoaded: firstNotLoaded})
                    }, self.settings.wrapped_block_click)
                }
            }, 1000)
        })
    };

    /**
     * Возвращает последнее отосланное сообщение, или null, если нужно отослать всю историю

     * @param clientPhone
     * @param $inboxMessages
     * @returns $lastSentMsg
     */
    self.getLastSendMessage = function (clientPhone, $inboxMessages) {
        // console.log('get last: ', clientPhone);
        let savedLastUrl = self.STORAGE.getLastUrl(clientPhone);
        let savedLastId = self.STORAGE.getLastId(clientPhone);
        // console.log(`last id ${savedLastId} last url ${savedLastUrl}`);
        if (savedLastId == null) {
            self.logInfo(clientPhone, "New history (" + self.getChatTitle() + "). Sending all messages.");
            return null;
        }

        let $lastSentMsg = self.findMessageByDataId(savedLastId, $inboxMessages);
        console.log('LAST SENT', $lastSentMsg);
        if (!$lastSentMsg && savedLastUrl && savedLastUrl !== 'undefined') {
            self.logError(clientPhone, "LastId defined (" + savedLastId + ") but, we cant find in history. Try to search by data-url: " + savedLastUrl);
            $lastSentMsg = self.findMessageByDataUrl(savedLastUrl, $inboxMessages);
            self.logError(clientPhone, "found message by data-url: " + savedLastUrl);
        }
        //id есть. но не смог найти в истории сообщении. возвращаем последнее
        if ($lastSentMsg == null) {
            self.logError(clientPhone, "LastId defined (" + savedLastId + ") but, we cant find in history.");
            //последняя попытка найти сообщения по времени:
            return self.getLastMessageByTime(clientPhone, $inboxMessages);

        }

        //id есть. сообщение нашел. возвращем его
        return $lastSentMsg;

    };

    // Взять последнее сообщение по времени
    self.getLastMessageByTime = function (clientPhone, $inboxMessages) {
        let savedTime = self.STORAGE.getTimeLastId(clientPhone);
        let result = null;
        $inboxMessages.each(function (index) {
            let $msg = $(this);
            let msgTime = $msg.find(self.css_settings.messages.inbox_datetime).text();
            // проверим для пропущенных звонков
            if (msgTime === '') {
                msgTime = $msg.find(self.css_settings.missed_calls.text).text();
            }
            msgTime = self.makeTime(msgTime);
            if (savedTime === msgTime) {
                self.logInfo(clientPhone, "Same time: " + savedTime + "==" + msgTime + " message" + $msg[0].outerHTML);
                result = $msg;
            }
        });
        return result;
    };

    /**
     * Получить список сообщений для отправки
     * @param clientPhone
     * @param $inboxMsgs
     * @returns {*}
     */
    self.getMessagesForSend = function (clientPhone, $inboxMsgs) {
        self.console_log('getMessagesForSend', $inboxMsgs.length);
        let $lastSentMsg = self.getLastSendMessage(clientPhone, $inboxMsgs);
        console.log('LAST SENT', $lastSentMsg);
        let $newMsgs = $lastSentMsg === null
            ? $inboxMsgs.css("background-color", "green")
            : $lastSentMsg.nextAll(self.css_settings.messages.inbox_nextall).css("background-color", "gold");

        // .image-caption появился для .message-location. он идет с data-id
        self.console_log('before filter', $newMsgs.length);
        // console.log('before filter:', $newMsgs);
        $newMsgs = $newMsgs.find('[' + self.consts.css.data_id + ']').not(self.css_settings.messages.inbox_exclude);
        self.console_log('after filter', $newMsgs.length);
        // console.log('after filter:', $newMsgs.length);
        return $newMsgs;
        // return self.filterAfterLastOut($newMsgs)
    };

    /** ОТПРАВКА НОВЫХ СООБЩЕНИЙ.
     * Запускается периодически.
     * Ищет все входящие сообщения, вытаскивает из сообщений номер телефона.
     *  - если сообщения есть, а номера нет, бросает ошибку и прекращает работу
     *  - получает по номеру телефона lastSavedId из localStorage

     *
     */
    self.sendNewMessages = function (vid) {
        try {
            let $inboxMessages;
            if (self.settings.after_last_out_only) {
                //1. Получить все входяшие
                let $allMessages = self.getAllMessages();
                $inboxMessages = self.filterAfterLastOut($allMessages);
            } else {
                $inboxMessages = self.getAllInboxMessages();
            }
            self.console_log('try to send', $inboxMessages.length);
            console.log('try to send 1', $inboxMessages);
            // console.log('type chat: ', self.getCurrentChatType());
            // console.log('try to send: ', $inboxMessages.length);
            // console.log(`send nm from: ${self.getPhoneFromActiveChat()}`);

            // Ищем пропущенные звонки и проставляем им id
            let missedArr = self.getMissedCalls(vid);
            if (missedArr.length > 0) {
                // console.log('Here starting missed calls...');
                self.setDataIdForCalls(missedArr);
            }

            // set id for wrapped
            if (self.settings.wrapped_enable) {
                // let chatType = self.getCurrentChatType();
                let wrapped = self.getWrappedImages($inboxMessages);
                wrapped.length > 0 ? console.log('wrapped', wrapped) : null;
                if (wrapped.length > 0) {
                    wrapped.each(function (index) {
                        let elem = $(this).find(self.css_settings.wrapped_images.bubble);
                        let timeBlocks = elem[0].querySelectorAll(self.css_settings.messages.inbox_datetime);
                        let firstDate1 = timeBlocks[0].innerText;
                        firstDate1 = self.makeTime(firstDate1);
                        let blockSize1 = timeBlocks.length === 4 ? '+0' : elem[0].querySelector(self.css_settings.wrapped_images.hidden_count).innerText;
                        console.log(`*data ${firstDate1} size ${blockSize1}`);
                        let id;
                        if (blockSize1 && blockSize1.startsWith('+')) {
                            id = `us_WRAPPED_${firstDate1}${blockSize1}`
                        } else {
                            id = `us_WRAPPED_${firstDate1}+0`
                        }
                        let url = '';
                        elem.addClass('message-text').addClass('custom-img').attr(self.consts.css.data_id, id).attr(self.consts.css.data_url, url);
                    })
                }
            }

            if ($inboxMessages.length === 0) {
                return wapp_result(0, vid);
            }
            console.log('Set ids');
            // console.log('type chat again: ', self.getCurrentChatType());
            // 2.-1 Проставить data-id для текста
            self.setDataIdForText($inboxMessages);
            // 2.0 Проставить data-id для видео
            self.setDataIdForVideo($inboxMessages);
            self.setDataIdForVideoGif($inboxMessages);
            // 2.1 Проставить data-id для картинок
            self.setDataIdForImages($inboxMessages);
            // 2.2. Проставить data-id для location
            self.setDataIdForLocation($inboxMessages);
            // 2.3. Проставить data-id для Sound
            self.setDataIdForSound($inboxMessages);
            // 2.4 Проставить data-id для документов (pdf)
            self.setDataIdForDocument($inboxMessages);
            // 2.5 Проставить data-id для контактов (vcard)
            self.setDataIdForContact($inboxMessages);
            // Проставить data-id для корзины товаров
            self.setDataIdForBasket($inboxMessages);

            // Добавляем к сообщениям пропущенные звонки
            $inboxMessages = $inboxMessages.add(missedArr);

            // console.log($inboxMessages);
            // Только сообщения с data-id
            $inboxMessages = $inboxMessages.has('[' + self.consts.css.data_id + ']');
            // console.log($inboxMessages);

            //3. Вытащить телефон
            // console.log('chat title:', self.getActiveChatTitle());
            // console.log('type chat and again: ', self.getCurrentChatType());
            let clientPhone = self.getPhoneFromActiveChat();
            // console.log('client_phone:', clientPhone);
            self.console_log('clientPhone', clientPhone);

            //4. Найти сообщения для отправки
            console.log('try to send', $inboxMessages);
            let $messagesForSend = self.getMessagesForSend(clientPhone, $inboxMessages);
            // console.log('chat title more:', self.getActiveChatTitle());
            // console.log('type chat more: ', self.getCurrentChatType());

            self.console_log('for send', $messagesForSend.length);
            // console.log('for send:', $messagesForSend);

            if ($messagesForSend.length > 0) {
                //5. Прогрузить аватар
                // console.log('client_phone:', clientPhone);
                self.getAvatar(clientPhone).then(function (avablob) {
                    //6 Проставить никнеймы и телефоны
                    self.putNicknamesForGroupChat(clientPhone, $inboxMessages);
                    //7. Отправить сообщения
                    // console.log(avablob)
                    // console.log('Trying to sendMessages...');
                    // console.log('chat title: ', self.getActiveChatTitle());
                    self.sendMessages($messagesForSend, clientPhone, avablob, false).then(function (result) {
                        // console.log('chat title:', self.getActiveChatTitle());
                        return wapp_result(result, vid);
                    });
                });
            } else {
                return wapp_result(0, vid);
            }

        } catch (e) {
            self.logError(clientPhone, e.message);
            return wapp_result(0, vid);
        }
    };

    // Назначение никнеймов в групповом чате
    self.putNicknamesForGroupChat = function (clientPhone, $inboxMessages) {
        if (!self.isGroupChat(clientPhone)) {
            return;
        }

        let phone;
        let nickname;
        let defaultName;

        $inboxMessages.each(function (index) {
            let $msg = $(this).closest(self.settings.msg_css);
            if ($msg.find(self.css_settings.group_chat_names.phone_name).length > 0) {
                //css
                phone = $msg.find(self.css_settings.group_chat_names.phone).text();
                //css
                nickname = $msg.find(self.css_settings.group_chat_names.name).text();
                defaultName = $msg.find(self.css_settings.group_chat_names.phone_name).text();

                if (phone.length > 0) {
                    phone = phone.replace(/\D/g, '');
                }

                if (phone.length === 0) {
                    phone = defaultName;
                }

                if (nickname.length === 0) {
                    nickname = defaultName;
                }
            }

            if (!$msg.hasClass(self.css_settings.group_chat_names.mark_class)) {
                $msg.attr(self.css_settings.group_chat_names.nickname_attr, nickname);
                $msg.attr(self.css_settings.group_chat_names.phone_attr, phone);
                $msg.addClass(self.css_settings.group_chat_names.mark_class);
            }
        });
    };

    /*
      Проставить для картинок собственный data-id.
      Нужно, т.к. у картинок его нет. А мы ориентируемся на него.
      todo: Оптимизировать, чтобы не ходить по ДОМУ
    */
    self.setDataId = function ($inboxMessages, elem_css, data_prefix, src_css) {
        // console.log('in set id');
        let $images = $inboxMessages.find(elem_css);
        // console.log($images);
        let oldTime;
        let i = 1;
        $images.each(function (index) {
            let $msgEl = $(this);
            let newTime = $msgEl.find(self.css_settings.messages.inbox_datetime).text();
            newTime = self.makeTime(newTime);
            // console.log(newTime);
            if (newTime === oldTime) {
                i++;
            } else {
                i = 1;
            }
            self.replaceSmiles($msgEl);
            let textLength = self.get_selectable_text($msgEl).length;
            // console.log('len', textLength);
            let id = "us_" + data_prefix + newTime + "_" + i + "_length_" + textLength;
            // console.log('id', id);
            oldTime = newTime;
            let url = '';
            let $src_elem = $msgEl.find(src_css);
            if ($src_elem.length > 0) {
                url = $src_elem.attr('src');
            }
            $msgEl.addClass('message-text').addClass('custom-img').attr(self.consts.css.data_id, id).attr(self.consts.css.data_url, url);
            // !!! Исключаем внутри наших bubble .message-text[data-id] чтобы они потом не отправлялись отдельно !!!
            // Помечаем их .not-for-send
            //css
            $msgEl.find(`.message-text[${self.consts.css.data_id}]`).addClass('not-for-send')
        });
        return i;
    };

    // Куча легаси, что делает до сих пор не понял, вроде айдишники проставляет
    self.setDataIdForText = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.text.bubble,
            self.css_settings.messages.types.text.idname,
            self.css_settings.messages.types.text.inside_element
        );
    };

    self.setDataIdForImages = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.image.bubble,
            self.css_settings.messages.types.image.idname,
            self.css_settings.messages.types.image.inside_element
        );
    };

    self.setDataIdForLocation = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.location.bubble,
            self.css_settings.messages.types.location.idname,
            self.css_settings.messages.types.location.inside_element
        );
    };

    self.setDataIdForSound = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.audio.bubble,
            self.css_settings.messages.types.audio.idname,
            self.css_settings.messages.types.audio.inside_element
        );
    };

    self.setDataIdForDocument = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.document.bubble,
            self.css_settings.messages.types.document.idname,
            self.css_settings.messages.types.document.inside_element
        );
    };

    self.setDataIdForContact = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.contact.bubble,
            self.css_settings.messages.types.contact.idname,
            self.css_settings.messages.types.contact.inside_element
        );
    };

    self.setDataIdForVideo = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.video.bubble,
            self.css_settings.messages.types.video.idname,
            self.css_settings.messages.types.video.inside_element
        );
    };

    self.setDataIdForVideoGif = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.messages.types.video_gif.bubble,
            self.css_settings.messages.types.video_gif.idname,
            self.css_settings.messages.types.video_gif.inside_element
        );
    };

    self.setDataIdForBasket = function ($inboxMessages) {
        return self.setDataId($inboxMessages,
            self.css_settings.basket.bubble,
            self.css_settings.basket.idname
        )
    };

    //
    self.setDataIdForCalls = function (missedArr) {
        let missedLabels = missedArr.find(self.css_settings.missed_calls.bubble);
        let oldTimeA, oldTimeV;
        let iA = 1;
        let iV = 1;
        missedLabels.each(function (index) {
            let elem = $(this);
            let callType = elem.find('[data-icon=miss]').length ? 'audio' : 'video';
            let str = elem.find(self.css_settings.missed_calls.text).text();
            let newTime = self.makeTime(str);
            if (callType === 'audio' && newTime === oldTimeA) {
                iA++;
            } else if (callType === 'audio' && newTime !== oldTimeA) {
                iA = 1;
            } else if (callType === 'video' && newTime === oldTimeV) {
                iV++;
            } else if (callType === 'video' && newTime !== oldTimeV) {
                iV = 1;
            }
            console.log(`type: ${callType}, counter ${callType === 'audio' ? iA : iV}`, newTime);
            let idName = self.css_settings.missed_calls[callType].idname;
            let id = `us_${idName}${newTime}_${callType === 'audio' ? iA : iV}`;
            let url = '';
            callType === 'audio' ? oldTimeA = newTime : oldTimeV = newTime;
            elem.addClass('message-text').addClass('custom-img').attr(self.consts.css.data_id, id).attr(self.consts.css.data_url, url);
        })
    };

    // базовый элемент для отправки сообщений из блока картинок, тут разметка не важна, т.к. используется только внутри
    self.baseImageElement = function (data_id, data_url, src, time, clientPhone, wa_data_id) {
        return `<div class="FTBzM message-in" data-id="${wa_data_id}"><span></span><div class="_1zGQT _26GKj message-text custom-img" data-id="${wa_data_id} data-clientphone="${clientPhone}" data-messageid="${data_id}" data-url="${data_url}" data-wrapped="true"><div class="_2Wx_5 _3LG3B"><div class="_3SaET"><div><div class="_3mdDl"><img src="${src}" class="_18vxA" style="width: 100%;"><div class="_3TrQs"></div></div><div class="iVt71"><div class="_3MYI2 _3UgZX"><span class="_3fnHB" dir="auto">${time}</span></div></div></div></div></div><span></span><div class="gxf3C" role="button"><span data-icon="forward-chat" class=""><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25 25" width="25" height="25"><path fill-rule="evenodd" clip-rule="evenodd" fill="#FFF" d="M14.248 6.973a.688.688 0 0 1 1.174-.488l5.131 5.136a.687.687 0 0 1 0 .973l-5.131 5.136a.688.688 0 0 1-1.174-.488v-2.319c-4.326 0-7.495 1.235-9.85 3.914-.209.237-.596.036-.511-.268 1.215-4.391 4.181-8.492 10.361-9.376v-2.22z"></path></svg></span></div></div></div>`
    };

    // получить валидный урл картинки
    self.getImageUrl = function () {
        return new Promise(function (resolve, reject) {
            let result;
            let counter = 0;
            let interval = setInterval(() => {
                let image = $(self.css_settings.wrapped_images.image); // элемент картинка
                let video = $(self.css_settings.wrapped_images.video); // элемент видео
                if (image.length < 0 || video.length < 0) {
                    console.log(`IMAGE ${image} or VIDEO ${video} not found`);
                    self.console_log(`IMAGE ${image} or VIDEO ${video} not found`);
                }
                let curEl = image.length > 0 ? image : video; // текущая картитнка (в блоке также может быть видео!)
                let type = image.length > 0 ? 'image' : 'video'; // тип элемента
                let url = curEl.attr('src'); // урл картинки
                let decodedUrl = decodeURIComponent(url);
                // получили валидный урл - очищаем интервал и возвращаем урл
                if (decodedUrl.indexOf('https://') > -1) {
                    result = decodedUrl;
                    clearInterval(interval);
                    resolve({url: result, type: type})
                }
                // после n попыток урл не получили - очищаем интервал и возвращаем 0
                if (counter > 30) {
                    clearInterval(interval);
                    resolve({url: 0, type: type, badUrl: decodedUrl})
                }
                counter++;
            }, 500)
        })
    };

    // refactor 05/2020
    self.setDataIdForWrappedImages = function (wrappedBlock, $inboxMessages) {
        // получим телефон (название чата) для передачи его в аттрибуты базового элемента
        // необходимо чтобы сообщение ушло от правильного клиента
        let waId = $(wrappedBlock[0]).parents(self.css_settings.wrapped_images.wrapped).attr('data-id'); // id сообщения проставляемый whatsapp
        console.log(wrappedBlock);
        console.log(waId);
        let elCount = 0; // подсчет добавленных на отправку элементов из альбома
        let clientPhone = self.getPhoneFromActiveChat();
        console.log(`phone from [setDataIdWrapped] ${clientPhone}`);
        self.console_log(`phone from [setDataIdWrapped] ${clientPhone}`);
        let imgElms = []; // массив с изображениями на отправку
        let oldTimeImg = null;
        let oldTimeVid = null;
        let counterImg = 1; // начать отчет изображений с новым временем заново
        let counterVid = 1; // начать отчет видео с новым временем заново
        let globalCounter = 1; // подсчет итераций setInterval
        let prevUrl; // урл пердыдущей картинки
        // console.log('next btn', nextButton);

        return new Promise(function (resolve, reject) {
            self.clickWrapped(wrappedBlock)
                .then((fromClicked) => {
                    console.log(fromClicked);
                    let count = fromClicked.hiddenImgCount; // количество скрытых изображений в свернутом блоке
                    let goLeft = fromClicked.firstNotLoaded; // not used сделать первый клик влево, чтобы прогрузилась первая картинка. если тут true то клик на второй картинке
                    let total = !goLeft ? count + 2 : count + 3; // сколько раз нажимать кнопку перелистывания картинок
                    let skipOnce = goLeft; // not used нажать кнопку вправо два раза - чтобы не считывать одно изображение два раза в случае непрогруза первого изображения в блоке
                    self.console_log(`Hidden in wrapped ${count}`);
                    console.log(`Hidden in wrapped ${count}`);
                    console.log(`1>>count ${count} go left ${goLeft}`);
                    console.log(`times to click ${total}`);
                    self.console_log(`times to click ${total}`);
                    let startAlbumTime = new Date().getTime(); // время обработки всего альбома
                    let startTime = new Date().getTime(); // засекаем время обработки урла картинки
                    let hasStarted = false; // для выхода из функции если при начале простановки id не получится обработать изображение
                    let clickInterval = setInterval(() => {
                        let image = $(self.css_settings.wrapped_images.image); // элемент картинка
                        let video = $(self.css_settings.wrapped_images.video); // элемент видео
                        if (!image.length && !video.length) {
                            // console.log('[REJECTED] no image or video');
                            // self.console_log('[REJECTED] no image or video in set data id for wrapped images');
                            console.log(`IMAGE ${image} or VIDEO ${video} not found`);
                            self.console_log(`IMAGE ${image} or VIDEO ${video} not found`);
                            // clearInterval(clickInterval);
                            // reject(-1);
                        }
                        let curEl = image.length > 0 ? image : video; // текущая картитнка (в блоке также может быть видео!)
                        let type; // тип элемента
                        if (image.length > 0) {
                            type = 'image'
                        } else if (video.length > 0) {
                            type = 'video'
                        } else {
                            type = 'undefined'
                        }
                        let url = curEl.attr('src'); // урл картинки
                        let decodedUrl = decodeURIComponent(url);

                        // видео еще не прогрузилось
                        if (type === 'video' && decodedUrl.indexOf('/stream/') > -1) {
                            self.logError(`**TYPE ${type} URL ${url}`);
                            let buttons = $(self.css_settings.wrapped_images.buttons);
                            self.logError(`**buttons ${buttons.length} URL ${url}`);
                            let downloadMenuBtn = $(buttons[buttons.length - 2]);
                            self.logError(`**button title ${downloadMenuBtn.attr('title')}`);
                            if (downloadMenuBtn) {
                                downloadMenuBtn.click();
                                let menu = $(self.css_settings.wrapped_images.download_menu);
                                if (menu.length) {
                                    // let downloadEnable = menu.find('li').last().hasClass('_1VBFT');
                                    // if (!downloadEnable) {
                                    if (buttons.length === 6) {
                                        console.log('Can be downloaded!');
                                        self.logError(`**Can be downloaded!`);
                                        // let prevButton = document.querySelector(self.css_settings.wrapped_images.prev_btn);
                                        // let nextButton = document.querySelector(self.css_settings.wrapped_images.next_btn);
                                        // prevButton.click();
                                        // nextButton.click();

                                        console.log('finally', imgElms);
                                        clearInterval(clickInterval);
                                        let endBlockTime = new Date().getTime();
                                        self.console_log(`Processed all from album ${imgElms.length} in ${(endBlockTime - startAlbumTime) / 1000} sec (counter ${globalCounter})`);
                                        let closeBtn = $(self.css_settings.wrapped_images.close_btn);
                                        self.click_element(closeBtn);
                                        reject(self.reject_reason.reason_scan_once)

                                    }
                                }

                            }

                        }

                        // получили валидный урл - очищаем интервал и возвращаем урл
                        else if (decodedUrl.indexOf('https://') > -1) {
                            let endTime = new Date().getTime();
                            let timeDiff = (endTime - startTime) / 1000;
                            startTime = new Date().getTime();
                            self.console_log(`Got good url for ${globalCounter} in ${timeDiff} sec`);
                            let newTime = document.querySelector(self.css_settings.wrapped_images.date).textContent.split(' ')[2];
                            newTime = self.makeTime(newTime);
                            // проставляем время для изображений или видео
                            if (type === 'image' && newTime !== oldTimeImg) {
                                oldTimeImg = newTime;
                                counterImg = 1;
                            } else if (type === 'video' && newTime !== oldTimeImg) {
                                oldTimeVid = newTime;
                                counterVid = 1;
                            }

                            let data_id;
                            // генерируем data_id в зависимости от типа - image или video
                            // увеличиваем счетчик для image или video
                            if (type === 'image') {
                                data_id = `us_IMAGE_${newTime}_${counterImg}_length_0`;
                                counterImg++;
                            } else if (type === 'video') {
                                data_id = `us_VIDEO_${newTime}_${counterVid}_length_0`;
                                counterVid++
                            }

                            // создаем новый элемент для сообщения с изображением или видео
                            self.console_log(`Add ${type} from wrapped, id ${data_id} src ${url} (go left ${goLeft}, skip ${skipOnce})`);
                            elCount = elCount + 1;
                            console.log(`[*] Add ${type} from wrapped, id ${data_id} src ${url} wa id ${waId}_${elCount}`);
                            let element = $.parseHTML(self.baseImageElement(data_id, url, url, newTime, clientPhone, `${waId}_${elCount}`));
                            imgElms.push(element[0]); // кладем созданный элемент в массив сообщений на отправку

                            if (imgElms.length === (count + 3)) {
                                console.log('finally', imgElms);
                                clearInterval(clickInterval);
                                let endBlockTime = new Date().getTime();
                                self.console_log(`Processed all from album ${imgElms.length} in ${(endBlockTime - startAlbumTime) / 1000} sec (counter ${globalCounter})`);
                                let closeBtn = $(self.css_settings.wrapped_images.close_btn);
                                self.click_element(closeBtn);
                                resolve(imgElms)
                            } else {
                                self.console_log(`click next #${globalCounter}`);
                                globalCounter = globalCounter + 1;
                                let nextButton = document.querySelector(self.css_settings.wrapped_images.next_btn);
                                // self.console_log(`counter now #${globalCounter}, click next ${nextButton}`);
                                if (!nextButton) {
                                    console.log('[REJECT] no next btn');
                                    self.console_log('[REJECT] no next btn in set data id for wrapped images');
                                    clearInterval(clickInterval);
                                    reject(-1)
                                }
                                hasStarted = true;
                                nextButton.click();
                                // self.click_element($(nextButton));
                            }
                        } else {
                            self.logError(`TYPE ${type} URL ${url}`);
                            let checkTime = new Date().getTime();
                            if (!hasStarted && (checkTime - startAlbumTime) / 1000 > 5) {
                                console.log('[REJECT] failed to process first');
                                self.console_log('[REJECT] failed to process first');
                                clearInterval(clickInterval);
                                reject(-1)
                            } else if (imgElms.length === (count + 3)) {
                                clearInterval(clickInterval);
                                console.log('[RESOLVE] images array filled');
                                self.console_log('[RESOLVE] images array filled');
                                resolve(1)
                            }
                        }
                    }, 500)
                }, () => {
                    self.logError('reject in setDataIdForWrappedImages');
                    reject(-1)
                })
        })
    };


    self.setDataIdForWrappedBlock = function () {
    };

    // Получить аватараку
    self.getAvatar = function (clientPhone) {
        // console.log('ava start: ', clientPhone);
        return new Promise(function (resolve, reject) {
            let avacount = self.localStorage_getItem(self.consts.ls.avacount + clientPhone);
            if (avacount == null || avacount % 15 === 0) {
                self.loadAvatar(clientPhone).then(function (data) {
                    if (data && data.indexOf('data:image/gif') == -1) {
                        self.localStorage_setItem(self.consts.ls.avacount + clientPhone, 1);
                        resolve(data);
                    } else {
                        resolve(null);
                    }
                });
            } else {
                resolve(null);
            }
        });
    };

    self.readasdataurl = function (blob) {
        return new Promise(function (resolve, reject) {
            try {
                let reader = new window.FileReader();
                reader.onloadend = function () {
                    resolve(reader.result);
                };
                reader.readAsDataURL(blob);
            } catch (e) {
                reject(e);
            }
        });
    };

    self.requestblob = function (url) {
        return new Promise(function (resolve, reject) {
            let xhr = new XMLHttpRequest();
            xhr.open('GET', url);
            xhr.responseType = 'blob';
            xhr.onload = function () {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr.response);
                } else {
                    reject({
                        status: xhr.status,
                        statusText: xhr.statusText
                    });
                }
            };
            xhr.onerror = function () {
                reject({
                    status: xhr.status,
                    statusText: xhr.statusText
                });
            };
            xhr.send();
        });
    };

    // Так же получить аватарку
    self.loadAvatar = function (clientPhone) {
        return new Promise(function (resolve, reject) {
            //если авы нет, ставим none
            let avaEl = document.querySelector(self.css_settings.avatar.avaimg);
            if (!avaEl || avaEl.length === 0) {
                self.logInfo(clientPhone, "Set avatar = none");
                resolve('none');
            }
            //ава есть
            let avaSrc = avaEl.getAttribute('src');
            let decoded_avaSrc = decodeURIComponent(avaSrc);
            if (decoded_avaSrc !== undefined) {
                if (decoded_avaSrc.indexOf(self.consts.method.https) > -1) {
                    self.requestblob(avaSrc)
                        .then(function (data) {
                            self.readasdataurl(data)
                                .then(function (data) {
                                    resolve(data);
                                })
                        }, function (err) {
                            self.logError(clientPhone, "Error load avatar" + err.status + " " + err.statusText + " occurred while receiving " + avaSrc);
                            resolve('none');
                        })
                } else {
                    resolve(avaSrc)
                }
            } else {
                self.logError(clientPhone, 'decoded_avaSrc === undefined');
                resolve('none');
            }
        });
    };

    /*
      Преобразование
      "false_79215953292@c.us_07D3B1AFDF8FDFA737"
      в
      "us_07D3B1AFDF8FDFA737"
      остальное без изменений
    */
    self.parseLastIdToShortId = function (clientPhone, lastId) {
        let result;
        if (lastId != null) {
            let matchLastId = lastId.match(self.css_settings.phone.data_id_short_pattern);
            if (matchLastId == null || matchLastId[self.css_settings.phone.data_id_short_index] == null) {
                self.logError(clientPhone, "Can't parse lastId (" + lastId + ") by regexp!");
                result = lastId;
            } else {
                result = matchLastId[self.css_settings.phone.data_id_short_index];
            }
        }

        if (result === undefined || result === null || result === 'undefined') {
            self.logError(clientPhone, "Can't parse lastId (" + lastId + "), it is undefined!");
        }
        return result;
    };

    /**
     * Получить элемент с последним отосланным сообщением.
     * @param $inboxMsgs
     * @param dataId
     * @returns {null} либо jquery элемент
     */
    self.findMessageByDataId = function (dataId, $inboxMsgs) {
        console.log('start search last id');
        let $resultEl = null;
        // console.log(dataId, $inboxMsgs);
        // проверим на предмет изменения блока свернутых изображений (добавления к блоку новых изображений)
        // если последнее сообщение - блок с картинками и его id отличается от сохраненного количеством изображений
        // (время первого изображения одинаково)
        // то вернем предпоследнее сообщение
        let $checkLast = $inboxMsgs.last();
        console.log($checkLast);
        let lastID = $checkLast.find(`.message-text[${self.consts.css.data_id}]`).attr(self.consts.css.data_id);
        console.log(lastID);

        if (self.settings.wrapped_enable) {
            if (dataId && dataId.startsWith('us_WRAPPED') && lastID !== dataId) {
                //
                if (lastID && lastID.startsWith(dataId.split('+')[0])) {
                    console.log($inboxMsgs[$inboxMsgs.length - 2]);
                    return $($inboxMsgs[$inboxMsgs.length - 2])
                }
            }
        }

        // Остальные случаи
        $inboxMsgs.each(function (index) {
            let $msgEl = $(this);
            //css
            if ($msgEl.find(`.message-text[${self.consts.css.data_id}]`).length > 0
                && $msgEl.find(`.message-text[${self.consts.css.data_id}]`).attr(self.consts.css.data_id).indexOf(dataId) > -1) {
                $resultEl = $msgEl;
            }
        });
        console.log($resultEl);
        return $resultEl;
    };

    // Найти последнее сообщение в диалоге по dataUrl
    self.findMessageByDataUrl = function (dataUrl, $inboxMsgs) {
        let $resultEl = null;
        $inboxMsgs.each(function (index) {
            let $msgEl = $(this);
            //css
            if ($msgEl.find('.message-text').length > 0) {
                let attr = $msgEl.find('.message-text').attr(self.consts.css.data_url);
                if (attr && attr.indexOf(dataUrl) > -1) {
                    $resultEl = $msgEl;
                }
            }
        });
        return $resultEl;
    };

    // Является ли чат групповым
    self.isGroupChat = function (clientPhone) {
        return $(self.css_settings.group_css).length > 0;
    };


    self.get_names = function ($msg) {
        let data = {};
        data.nickname = '';
        data.client_phone = '';
        // Получаем само сообщение в списке
        let $msgroot = $msg.closest(self.settings.msg_css);
        // проверим сообщение на предмет наличия аттрибутов имени и телефона
        if ($msgroot.hasClass(self.css_settings.group_chat_names.mark_class)) {
            data.nickname = $msgroot.attr(self.css_settings.group_chat_names.nickname_attr);
            data.client_phone = $msgroot.attr(self.css_settings.group_chat_names.phone_attr);
            // если требуемого класса нет (аттрибуты имени и телефона не проставлены) - получим их как в self.putNicknamesForGroupChat
        } else {
            let phone = $msg.find(self.css_settings.group_chat_names.phone).text();
            let nickname = $msg.find(self.css_settings.group_chat_names.name).text();
            let defaultName = $msg.find(self.css_settings.group_chat_names.phone_name).text();
            if (phone.length > 0) {
                phone = phone.replace(/\D/g, '');
            }
            if (phone.length === 0) {
                phone = defaultName;
            }
            if (nickname.length === 0) {
                nickname = defaultName;
            }
            data.client_phone = phone;
            data.nickname = nickname;
        }
        return data;
    };


    self.getWAiD = function (msgEl) {
        return msgEl.parent(self.settings.msg_css).attr('data-id');
    };

    // Прием единичного сообщения от клиента и последующая отправка кликером на гейт
    // вызывается в основной функции приема сообщений, которая написана далее
    self.sendMessage = function (clientPhone, $msg, data, avablob, name, selected = false, missedCall = false, wrapped = false, wrappedId = null, wrappedNames = null) {
        console.log('send message', `selected ${selected}, call ${missedCall}, wrapped ${wrapped}`);
        console.log('send message', $msg);
        return new Promise(function (resolve, reject) {
            data.wa_id = self.getWAiD($msg);
            data.device_phone = self.getPhone();
            data.transport = 'whatsapp';
            data.selected = selected;
            if (selected) {
                data.body = 'Restored message:\n' + data.body
            }
            if (name) {
                data.data_name = name;
            }

            if (avablob) {
                data.avablob = avablob;
            }
            if (self.isGroupChat(clientPhone)) {
                let names = wrappedNames ? wrappedNames : self.get_names($msg);
                data.nickname = names.nickname;
                data.client_phone = names.client_phone;
                data.clientPhone = names.client_phone;
                data.group_id = clientPhone;
                data.group = true;
                data.chat_title = self.getChatTitle();
            } else {
                data.client_phone = clientPhone;
                data.clientPhone = clientPhone;
                data.nickname = self.getChatTitle();
                data.group = false;
            }
            data.data_id = $msg.attr(self.consts.css.data_id);
            data.data_url = $msg.attr(self.consts.css.data_url);


            let msgTime;
            let msgText;

            // Парсим пропущенный звонок
            if (missedCall) {
                msgTime = $msg[0].textContent.slice(-5);
                msgText = $msg[0].textContent.slice(0, -5);
            } else {
                msgTime = $msg.find(self.css_settings.messages.inbox_datetime).text();
                msgTime = self.makeTime(msgTime);
                msgText = self.get_selectable_text($msg);
            }

            // let msgBlob = data.imageBlob ? data.imageBlob : '';

            msgTime = msgTime.replace(/\n/g, '');

            // data.msg_hash = self.hashCode(msgTime, msgText, msgBlob);
            data.msg_time = msgTime;
            data.msg_text = msgText;

            let timeNow = new Date;
            data.timestamp = String(timeNow.getTime());

            console.log(data);

            if (!self.settings.autoanswer) {
                ajax_post({
                        type: 'POST',
                        async: false,
                        url: self.settings.gateway + self.consts.method.receiver,
                        data: data
                    },
                    {
                        'always': function (result) {
                            if ((result.code != 200) && (result.code != 602)) {
                                self.logError(data.client_phone, "Err response: " + JSON.stringify(result));
                            } else {
                            }
                        }
                    });
            }

            if (!selected) {
                self.logInfo('ids saved ' + data.data_id);
                if (name) {
                    self.logInfo('NAME SENT ' + data.data_name);
                }
                if (wrapped) {
                    self.localStorage_setItem(clientPhone, wrappedId);
                    self.localStorage_setItem(`time-${clientPhone}`, wrappedId.split('_')[2].split('+')[0]);
                } else {
                    self.STORAGE.saveLastId(clientPhone, $msg);
                    self.STORAGE.saveTimeLastId(clientPhone, $msg);
                }
            }
            resolve(1);
        });

    };

    // Замена смайлов
    self.replaceSmiles = function ($msgDiv) {
        $msgDiv.find(self.css_settings.messages.selectable_text + ' ' + self.css_settings.messages.smiles).replaceWith(function () {
            return "<span>" + $(this).attr('alt') + "</span>";
        });
        $msgDiv.find(self.css_settings.messages.smiles).replaceWith(function () {
            return "<span class='selectable-text'>" + $(this).attr('alt') + "</span>";
        });
        // Случай, когда selectable включается внутрь selectable. например всякие a href. костыль.
        // ToDo: переделать
        $msgDiv.find(self.css_settings.messages.selectable_in_selectable_text).replaceWith(function () {
            return "<span>" + $(this).text() + "</span>";
        });
    };

    self.check_bubble = function ($e, css) {
        return $e.is(css) || ($e.find(css).length > 0)
    };

    // Получение типа сообщения
    self.getMsgType = function ($msgRootEl) {
        console.log($msgRootEl);
        console.log('classlist', $msgRootEl[0].classList);

        if (self.check_bubble($msgRootEl, self.css_settings.basket.bubble)) {
            return self.css_settings.basket.name
        }

        for (let key in self.css_settings.messages.types) {
            if (self.check_bubble($msgRootEl, self.css_settings.messages.types[key].bubble)) {
                return self.css_settings.messages.types[key].name
            }
        }
        //css
        if ($msgRootEl.find('.image-thumb img').not('.emoji, .single-emoji, .large-emoji').length > 0) {
            return "IMAGE";
        }

        // Получаем тип пропущенный звонок CALL
        if (self.check_bubble($msgRootEl, self.css_settings.missed_calls.bubble)) {
            return self.css_settings.missed_calls.name
        }

        if (self.settings.wrapped_enable) {
            if ($msgRootEl.attr('data-messageid').startsWith('us_WRAPPED')) {
                return 'WRAPPED'
            }
        }

        return "TEXT";
    };

    // поменять фотмат таймлайна на обратный таймлайну из настроек
    self.reverseTimelineFormat = function () {
        if (!self.settings.timeline_format) {
            return null
        }
        let timelineFormatArr = self.settings.timeline_format.split(' ');
        return `${timelineFormatArr[1]} ${timelineFormatArr[0]} yyyy`
    };

    // Получение текущей даты/времени
    self.getNowDateTimeParsed = function () {
        let options = {
            year: 'numeric',
            month: 'numeric',
            day: 'numeric',
            hour: 'numeric',
            minute: 'numeric'
        };
        let date_idx = 0, time_idx = 1;
        let date = new Date().toLocaleString("ru", options);
        let arr = date.split(', ');
        date_idx, time_idx = arr[1].match(':') ? (0, 1) : (1, 0);
        let time = arr[1].match(':') ? self.makeTime(arr[1]) : self.makeTime(arr[0]);
        let s_date = arr[0].split(/\.|\//);
        return `${s_date[2]}-${s_date[1]}-${s_date[0]}T${time}`;
    };

    // Парсинг даты
    self.parseDate = function (date, format) {
        let arr = date.split(', ');
        let time = self.makeTime(arr[0]);
        let s_date = arr[1].split(/\.|\//);
        let first = s_date[0].length === 1 ? `0${s_date[0]}` : s_date[0];
        let second = s_date[1].length === 1 ? `0${s_date[1]}` : s_date[1];
        // return -> 'yyyy-mm-ddTHH:MM'
        let timeline_format = format ? format : self.settings.timeline_format;
        if (timeline_format === "mm dd yyyy") {
            return `${s_date[2]}-${first}-${second}T${time}`;
        }
        if (timeline_format === "dd mm yyyy") {
            return `${s_date[2]}-${second}-${first}T${time}`;
        }
    };

    self.filterByTimeline = function ($msgEl) {
        if ($msgEl[0].innerHTML.match("\\[(.*)]") !== null) {
            let msgTimelineString = $msgEl[0].innerHTML.match("\\[(.*)]")[1];
            self.console_log(`[TIMELINE STRING] ${msgTimelineString}`);
            let msgTimelineStringParsed = self.parseDate(msgTimelineString);
            self.console_log(`[TIMELINE STRING PARSED] ${msgTimelineStringParsed}`);
            let msg_timeline;
            msg_timeline = new Date(Date.parse(msgTimelineStringParsed));
            if (!self.isValidDate(msg_timeline)) {
                // не получилось собрать дату - попробуем поменять формат таймлайна
                let timelineFormatReversed = self.reverseTimelineFormat();
                if (timelineFormatReversed) {
                    msgTimelineStringParsed = self.parseDate(msgTimelineString, timelineFormatReversed);
                    self.console_log(`[TIMELINE REVERSED STRING PARSED] ${msgTimelineStringParsed}`);
                    msg_timeline = new Date(Date.parse(msgTimelineStringParsed));
                } else {
                    msg_timeline = self.getNowDateTimeParsed();
                }
            }
            let global_timeline = new Date(Date.now() - 864e5);
            if (self.settings.timeline) {
                global_timeline = new Date(Date.parse(self.parseDate(self.settings.timeline)));
            }

            self.logInfo('[MESSAGE TIME] ' + msg_timeline);
            if (msg_timeline <= global_timeline) {
                self.logInfo('TIMELINE ' + global_timeline);
                self.logError('MSG WAS REJECTED');
                return 1;
            }
        }
        return 0
    };

    // Основная функция приема сообщений от клиента
    self.sendMessages = function ($newMessages, clientPhone, avablob, selected = false) {
        // console.log(`sending selected: ${selected}`);
        return new Promise(function (resolve, reject) {
            let result = $newMessages.length;
            let ready = Promise.resolve(0);
            let send_element = function ($msgEl) {
                // console.log('send elem: ', clientPhone);
                return function (r) {
                    let $waiting = $msgEl.find(self.settings.waiting_css);
                    if ($waiting.length > 0) {
                        self.logError(clientPhone, self.settings.waiting_css + ' ' + $waiting.length);
                        console.error(clientPhone);
                        return Promise.reject(self.reject_reason.reason_wait_for_message);
                    }
                    let msgType = self.getMsgType($msgEl);
                    console.log('MSG TYPE->', msgType);
                    self.console_log('=====', msgType);
                    if (!selected) {
                        self.logInfo(clientPhone, msgType + ' ' + $msgEl.attr(self.consts.css.data_id));
                        self.logInfo(clientPhone, msgType + ' ' + $msgEl.parent(self.settings.msg_css).attr('data-id'));
                    } else {
                        self.logInfo(clientPhone, msgType + ' selected message');
                    }

                    // console.log('sending to:', clientPhone, 'type:', msgType);
                    switch (msgType) {
                        case 'IMAGE':
                            return self.sendImage($msgEl, clientPhone, avablob, selected);
                        case 'CONTACT':
                            return self.sendContact($msgEl, clientPhone, avablob, selected);
                        case 'MAP':
                            return self.sendMap($msgEl, clientPhone, avablob, selected);
                        case 'AUDIO':
                            return self.sendAudio($msgEl, clientPhone, avablob, selected);
                        case 'VIDEO':
                            return self.sendVideo($msgEl, clientPhone, avablob, selected);
                        case 'VIDEO_GIF':
                            return self.sendVideoGif($msgEl, clientPhone, avablob, selected);
                        case 'DOC':
                            return self.sendDoc($msgEl, clientPhone, avablob, selected);
                        case 'TEXT':
                            return self.sendText($msgEl, clientPhone, avablob, selected);
                        case 'CALL':
                            return self.sendMissedCall($msgEl, clientPhone, avablob, selected);
                        case 'WRAPPED':
                            return self.sendWrapped($msgEl, clientPhone, avablob, selected);
                        case 'BASKET':
                            return self.sendBasket($msgEl, clientPhone, avablob, selected);
                        default:
                            self.logError(clientPhone, 'Cant identify type of message! ' + msgType + ' Msg: ' + $msgEl.text());
                            return Promise.resolve(0);
                    }
                }
            };

            for (let i = 0; i < $newMessages.length; ++i) {
                ready = ready
                    .then(
                        send_element($($newMessages[i])),
                        function (err) {
                            resolve(err);
                        })
            }

            ready.then(function (value) {
                self.logInfo(clientPhone, result);
                resolve(result);
            }, function (err) {
                self.logInfo(clientPhone, 'reject ' + err);
                resolve(err);
            });
        });
    };

    // получение изображения в цитируемом сообщении
    self.get_quoted_image = function ($msg, preview = false) {
        // блок с цитируемым вложением
        // let quotedImg = $msg.find('._3ssLP');
        let quotedImg = $msg.find(self.css_settings.messages.types.image.quoted);
        // console.log(1, quotedImg);
        if (quotedImg.length === 0) {
            return ''
        }
        // Отправляем превью по аргументу или если в блоке нет урла
        if (preview || quotedImg.length === 1) {
            quotedImg = quotedImg.first();
            let quotedImgSrc = quotedImg.css('background-image');
            quotedImgSrc = quotedImgSrc.slice(5, -2);
            console.log(`[quoted image] ${quotedImgSrc}`);
            return quotedImgSrc
        } else {
            // Отпрвляем полное изображение
            quotedImg = quotedImg.last();
            let quotedImgSrc = quotedImg.css('background-image');
            quotedImgSrc = quotedImgSrc.slice(5, -2);
            console.log(`[quoted image] ${quotedImgSrc}`);
            return quotedImgSrc
        }
    };

    // Получение цитируемого текста
    self.get_quoted_text = function ($msg) {
        let $q = $msg.find(self.css_settings.messages.quoted_message_text);
        if ($q.length > 0) {
            let t = $q.text();
            if (t) {
                if (t === 'Photo') {
                    console.log('****** do smth to send image')
                } else if (t === 'Video') {
                    console.log('****** do smth to send video')
                }
                return '«' + t + '»\n— ';
            }
        }
        return '';
    };

    // Получение коммента к цитате
    self.get_not_quoted_text = function ($msg) {
        let $span = $msg.find(self.css_settings.messages.selectable_text).not(self.css_settings.messages.quoted_message_text + ' ' + self.css_settings.messages.selectable_text);
        if ($span.length > 0) {
            return $span.last().text();
        }
        return '';
    };

    /*
      Получить текст сообщения, который будет в поле body
    */
    self.get_selectable_text = function ($msg) {
        // Формирование текста с цитатой, если текст без цитаты, он не исказится
        return self.get_quoted_text($msg) + self.get_not_quoted_text($msg);
    };

    /*если есть картинка в сообщении
      проверяем прогружена ли она
      НЕТ - кликаем на ней, и через секунду запускаем себя снова
      ДА - вызываем отправку сообщения
    */
    self.sendImage = function ($msgEl, clientPhone, avablob, selected) {
        // self.console_log('=====', 'send image');

        return new Promise(function (resolve, reject) {
            $msgEl[0].scrollIntoView();
            // изображение с классом :not(... ) - превью
            let imgEl = $msgEl.find(self.css_settings.messages.types.image.wrapper_div).find('img')
                .not(self.css_settings.messages.types.image.preview_img);
            let imgSrc = imgEl.attr('src');
            if (imgEl.length > 1) {
                imgSrc = $(imgEl[imgEl.length - 1]).attr('src');
            }
            self.console_log(`1) IMAGE urls len: ${imgEl.length}, download: ${imgEl.length}`);
            let decoded_imgSrc = decodeURIComponent(imgSrc);
            //картинка прогружена, можно слать
            if (decoded_imgSrc.indexOf(self.consts.method.https) > -1) {
                console.log('OK->', decoded_imgSrc);
                self.console_log(`image has good url`);
                // self.testDownloader(decoded_imgSrc);

                let $read_more = $msgEl.find(self.css_settings.messages.types.text.read_more);
                // console.log(`read more btn ${$read_more.length}`);
                if ($read_more.length > 0) {
                    // скроллим до кнопки раскрытия и кликаем на нее
                    $read_more[0].scrollIntoView();
                    $read_more[0].click();
                    // скроллим до времени сообщения - т.е. до низа сообщения
                    $msgEl.find(self.css_settings.messages.inbox_datetime)[0].scrollIntoView();
                    reject(self.reject_reason.reason_scan_once);
                } else {
                    $msgEl[0].scrollIntoView();
                }

                setTimeout(() => {
                    console.log('start to send image');
                    self.console_log('[START TO SEND IMAGE]');
                    imgEl = $msgEl.find(self.css_settings.messages.types.image.wrapper_div).find('img')
                        .not(self.css_settings.messages.types.image.preview_img);
                    imgSrc = imgEl.attr('src');
                    if (imgEl.length > 1) {
                        imgSrc = $(imgEl[imgEl.length - 1]).attr('src');
                    }
                    self.console_log(`2) IMAGE urls len: ${imgEl.length}, download: ${imgEl.length}`);
                    if (self.localStorage_getItem(imgSrc) == null) {
                        self.localStorage_setItem(imgSrc, true); //флаг, чтоб не слать дважды
                        self.convertAudio(imgSrc, function (base64Img, imgSrc) {
                            self.replaceSmiles($msgEl);
                            // Заменяем data-url потому что после последней обработки он поменялся
                            $msgEl.attr('data-url', imgSrc);
                            let text = self.get_selectable_text($msgEl);

                            self.getNameFromCard($msgEl)
                                .then((name) => {
                                    // console.log('name: ', name);
                                    self.sendMessage(clientPhone, $msgEl, {
                                            type: "image",
                                            body: text,
                                            imageBlob: base64Img
                                        },
                                        avablob, name, selected)
                                        .then(() => {
                                            self.closeClientCard();
                                            localStorage.removeItem(imgSrc);
                                            resolve(1)
                                        })
                                })
                        });
                    }
                }, self.settings.image_download_delay)


            } else {
                console.log('Image not uploaded!', $msgEl);
                console.log('NOT OK->', decoded_imgSrc);
                self.console_log(`image not loaded!`);
                // let $clickable = $msgEl.find('[data-icon="media-download-noborder"], button, image-thumb-lores').not(':has([data-icon="media-cancel"])');
                let $clickable = $msgEl.find('[data-icon="media-download"], button, image-thumb-lores').not(':has([data-icon="media-cancel"])');
                self.console_log(`image can be downloaded ${$clickable.length}`);
                if ($clickable.length > 0) {
                    $clickable[0].scrollIntoView();
                    self.click_element($clickable);
                } else {
                    console.log('Second!');
                    let image_loading = '[data-icon="media-cancel"]';
                    if (self.settings.image_loading_css) {
                        image_loading = image_loading + ', ' + self.settings.image_loading_css;
                    }
                    let $clickable = $msgEl.find(image_loading);
                    self.console_log(`image still loading ${$clickable.length}`);
                    if ($clickable.length === 0) {
                        self.logError(clientPhone, 'no click element for image');
                        self.logError(clientPhone, $msgEl[0].outerHTML);
                        self.logError(clientPhone, image_loading);
                        self.logError('skip send image (image deleted?)');
                        // пометим пропущенную картинку как отправленную, иначе кликер на ней зависнет
                        self.STORAGE.saveLastId(clientPhone, $msgEl);
                        self.STORAGE.saveTimeLastId(clientPhone, $msgEl);
                        return resolve(1);
                        // reject(self.reject_reason.reason_scan_once)
                    } else {
                        self.logError(clientPhone, '(js) image still loading...', $msgEl.attr(self.consts.css.data_id));
                        // return resolve(1)
                        reject(self.reject_reason.reason_scan_once)
                    }
                }
                reject(self.reject_reason.reason_scan_once);
            }
        });
    };

    /* Грузим документы
       Кликаем, дожидаемся, пока программа поставить url, если url стоит - грузим
    */
    self.sendDoc = function ($msgEl, clientPhone, avablob, selected) {

        return new Promise(function (resolve, reject) {
            let docInterval = setInterval(() => {
                let data_id = $msgEl.attr(self.consts.css.data_id);
                let src = self.documentinfo.get_url(`${clientPhone}_${data_id}`);
                //document прогружен, можно слать
                if (src) {
                    clearInterval(docInterval);
                    if (self.localStorage_getItem(src) == null) {
                        self.localStorage_setItem(src, true); //флаг, чтоб не слать дважды
                        self.convertAudio(src, function (base64Img, src) {
                            self.replaceSmiles($msgEl);
                            // Заменяем data-url потому что после последней обработки он поменялся
                            $msgEl.attr('data-url', src);
                            let text = self.documentinfo.get_text(`${clientPhone}_${data_id}`);

                            // self.getNameFromCard($msgEl)
                            //     .then((name) => {
                            //         console.log('name: ', name);
                            let name = '';
                            self.sendMessage(clientPhone, $msgEl, {
                                    type: "pdf",
                                    body: text,
                                    pdfBlob: base64Img
                                },
                                avablob, name, selected)
                                .then(() => {
                                    self.closeClientCard();
                                    localStorage.removeItem(src);
                                    resolve(1)
                                })
                            // })
                        });
                    }
                } else {
                    self.documentinfo.current_id = `${clientPhone}_${data_id}`;
                    let $clickable = $msgEl.find('[data-icon="audio-download"]');
                    if ($clickable.length > 0) {
                        $clickable[0].scrollIntoView();
                        self.click_element($clickable);
                    } else {
                        let document_loading = self.settings.document_loading_css;
                        // let document_loading = 'circle1';
                        $clickable = $msgEl.find(document_loading);
                        if ($clickable.length === 0) {
                            let title = $msgEl.find('a').attr('title');
                            self.logError(clientPhone, `*** DOCUMENT ${title || ''} message received (system error occured - 1) ***`);
                            self.logError(clientPhone, 'no click element for document');
                            // self.logError(clientPhone, $msgEl[0].outerHTML);
                            let logEl = $($msgEl[0].outerHTML);
                            logEl.find('[style]').removeAttr('style');
                            self.logError(clientPhone, logEl[0].outerHTML);
                            clearInterval(docInterval);
                            resolve(1);
                        } else {
                            self.logError(clientPhone, `(js) document ${data_id} still loading...`);
                        }
                    }
                }
            }, 1000);
        });

    };

    // Отправка текста
    self.sendText = function ($msgEl, clientPhone, avablob, selected) {
        // console.log('send text:', selected);
        // console.log('send text chat: ', self.getActiveChatTitle());
        return new Promise(function (resolve, reject) {
            let rejectByTimeline = !selected ? self.filterByTimeline($msgEl) : 0;
            if (rejectByTimeline === 1) {
                return resolve(1)
            }
            let $read_more = $msgEl.find(self.css_settings.messages.types.text.read_more);
            console.log('1. send text');
            // self.console_log('read more', $read_more.length, '<<')
            if ($read_more.length > 0) {
                // скроллим до кнопки раскрытия и кликаем на нее
                $read_more[0].scrollIntoView();
                $read_more[0].click();
                // скроллим до времени сообщения - т.е. до низа сообщения
                $msgEl.find(self.css_settings.messages.inbox_datetime)[0].scrollIntoView();
                reject(-1);
            } else {
                // console.log('before smiles: ', self.getActiveChatTitle());
                self.replaceSmiles($msgEl);
                console.log('before get name: ', self.getActiveChatTitle());
                self.getNameFromCard($msgEl)
                    .then((name) => {
                        // если есть изображение - отправляем IMAGE
                        let quotedImg = self.get_quoted_image($msgEl);
                        // console.log('after get name: ', self.getActiveChatTitle());
                        self.console_log('MSG TIME', $msgEl.find('[data-pre-plain-text]').attr('data-pre-plain-text'));
                        if (!quotedImg) {
                            // отправка текстового сообщения - нет изображения в цитируемом сообщении
                            self.sendMessage(clientPhone, $msgEl, {
                                type: "text",
                                body: self.get_selectable_text($msgEl)
                            }, avablob, name, selected)
                                .then(() => {
                                    self.closeClientCard();
                                    resolve(1)
                                })
                        } else {
                            // отправка изображения - в цитируемом сообщении есть изображение
                            // отправка превью
                            if (quotedImg.indexOf(self.consts.method.https) < 0) {
                                let base64Img = quotedImg;
                                self.replaceSmiles($msgEl);
                                let text = self.get_selectable_text($msgEl);
                                self.getNameFromCard($msgEl)
                                    .then((name) => {
                                        self.sendMessage(clientPhone, $msgEl, {
                                                type: "image",
                                                body: text,
                                                imageBlob: base64Img
                                            },
                                            avablob, name, selected)
                                            .then(() => {
                                                self.closeClientCard();
                                                resolve(1)
                                            })
                                    })
                            } else {
                                // отправка полного изображения
                                self.convertAudio(quotedImg, function (base64Img, imgSrc) {
                                    self.replaceSmiles($msgEl);
                                    let text = self.get_selectable_text($msgEl);
                                    self.getNameFromCard($msgEl)
                                        .then((name) => {
                                            self.sendMessage(clientPhone, $msgEl, {
                                                    type: "image",
                                                    body: text,
                                                    imageBlob: base64Img
                                                },
                                                avablob, name, selected)
                                                .then(() => {
                                                    self.closeClientCard();
                                                    resolve(1)
                                                })
                                        })
                                })
                            }
                        }
                    })
            }
        });
    };

    // Отправка аудио
    self.sendAudio = function ($msgEl, clientPhone, avablob, selected) {
        $msgEl[0].scrollIntoView();
        let audioEl = $msgEl.find('audio');
        let audioSrc = audioEl.attr('src');
        let decoded_audioSrc = decodeURIComponent(audioSrc);
        return new Promise(function (resolve, reject) {
            //аудио прогружена, можно слать
            if (decoded_audioSrc.indexOf('https://') > -1 && self.localStorage_getItem(audioSrc) == null) {
                self.localStorage_setItem(audioSrc, true); //флаг, чтоб не слать дважды
                self.convertAudio(audioSrc, function (base64Audio, audioSrc) {
                    self.replaceSmiles($msgEl);
                    let text = '';

                    self.getNameFromCard($msgEl)
                        .then((name) => {
                            // console.log('name: ', name);
                            self.sendMessage(clientPhone, $msgEl, {
                                type: "audio",
                                body: text,
                                audioBlob: base64Audio
                            }, avablob, name, selected)
                                .then(() => {
                                    self.closeClientCard();
                                    localStorage.removeItem(audioSrc);
                                    resolve(1)
                                })
                        })
                });
            } else {
                reject(self.reject_reason.reason_scan_once);
            }
        });
    };

    self.sendVideoGif = function ($msgEl, clientPhone, avablob, selected) {
        return new Promise(function (resolve, reject) {
            $msgEl.find(self.css_settings.messages.types.video_gif.play_btn).click()
            let data_id = $msgEl.attr(self.consts.css.data_id);
            // console.log(data_id);
            let src = $msgEl.find('video').attr('src');
            // console.log($msgEl.find('video'));
            // console.log(src);
            self.console_log('get_url', data_id, src);
            //document прогружен, можно слать
            if (src) {
                self.console_log('src ok');
                if (self.localStorage_getItem(src) == null) {
                    self.localStorage_setItem(src, true); //флаг, чтоб не слать дважды
                    self.console_log('before convertAudio');
                    self.convertAudio(src, function (base64Img, src) {
                        self.replaceSmiles($msgEl);
                        // Заменяем data-url потому что после последней обработки он поменялся
                        $msgEl.attr('data-url', src);
                        let text = self.get_selectable_text($msgEl);
                        self.getNameFromCard($msgEl)
                            .then((name) => {
                                // console.log('name: ', name);
                                self.sendMessage(clientPhone, $msgEl, {
                                    type: "video",
                                    body: text,
                                    videoBlob: base64Img
                                }, avablob, name, selected)
                                    .then(() => {
                                        self.closeClientCard();
                                        localStorage.removeItem(src);
                                        resolve(1)
                                    })
                            })
                    });
                }
            }
        });
    };

    // Отправка видео
    self.sendVideo = function ($msgEl, clientPhone, avablob, selected) {
        // console.log($msgEl, clientPhone);
        if (!self.settings.video_enabled) {
            return new Promise(function (resolve, reject) {
                self.getNameFromCard($msgEl)
                    .then((name) => {
                        // console.log('name: ', name);
                        self.sendMessage(clientPhone, $msgEl, {
                            type: "text",
                            body: "*** VIDEO message received (not supported yet) ***"
                        }, avablob, name, selected)
                            .then(() => {
                                self.closeClientCard();
                                resolve(1)
                            })
                    })
            });
        }

        return new Promise(function (resolve, reject) {
            let data_id = $msgEl.attr(self.consts.css.data_id);
            let src = self.documentinfo.get_url(`${clientPhone}_${data_id}`);
            self.console_log('get_url', data_id, src);
            //document прогружен, можно слать
            if (src) {
                self.console_log('src ok');
                if (self.localStorage_getItem(src) == null) {
                    self.localStorage_setItem(src, true); //флаг, чтоб не слать дважды
                    self.console_log('before convertAudio');
                    self.convertAudio(src, function (base64Img, src) {
                        self.replaceSmiles($msgEl);
                        // Заменяем data-url потому что после последней обработки он поменялся
                        $msgEl.attr('data-url', src);
                        let text = self.get_selectable_text($msgEl);

                        self.getNameFromCard($msgEl)
                            .then((name) => {
                                // console.log('name: ', name);
                                self.sendMessage(clientPhone, $msgEl, {
                                    type: "video",
                                    body: text,
                                    videoBlob: base64Img
                                }, avablob, name, selected)
                                    .then(() => {
                                        self.closeClientCard();
                                        localStorage.removeItem(src);
                                        resolve(1)
                                    })
                            })
                    });
                }
            } else {
                self.documentinfo.current_id = `${clientPhone}_${data_id}`;
                $msgEl[0].scrollIntoView();
                let media_play_css = self.settings.play_video_css;
                let $clickable = $msgEl.find(media_play_css);
                if (!$clickable.length > 0) {
                    self.logError(clientPhone, 'no click element for video ' + media_play_css);
                    resolve(1);
                }

                $clickable.click();
                self.console_log('setInterval ' + self.settings.video_timeout.toString());
                let timer = setInterval(function () {
                    let download_css = '[role="button"]:has([data-icon="download"])';
                    let $download = $(download_css);
                    self.console_log('inside clicking on download button');
                    // console.log('is download button found?');
                    if (!($download.length > 0)) {
                        // console.log('download button not found!');
                        self.logError(clientPhone, 'no video download element found ' + download_css);

                        self.getNameFromCard($msgEl)
                            .then((name) => {
                                // console.log('name: ', name);
                                self.sendMessage(clientPhone, $msgEl, {
                                    type: "text",
                                    body: "*** VIDEO message received (system error occured - 1) ***"
                                }, avablob, name, selected)
                                    .then(() => {
                                        self.closeClientCard();
                                        resolve(1)
                                    })
                            })
                    }

                    self.console_log('download button ok', $download.length);
                    // console.log('download button found');
                    //css
                    // видео еще не загрузилось, скачать его нельзя (кнопка не активна)
                    self.console_log('download class: ', $download.parent().attr('class'), 'aria disabled: ', $download.attr('aria-disabled'));
                    if ($download.parent().hasClass(self.css_settings.messages.types.video.download_btn_disable_class)
                        || $download.attr('aria-disabled') === 'true') {
                        self.console_log('download button disabled');
                    } else {

                        self.click_element($download);
                        self.logInfo('download clicked');
                        clearInterval(timer);
                        self.console_log('download button clicked');
                        setTimeout(function () {
                            self.console_log('inside clicking on close button');
                            let close_css = '[data-icon="x-viewer"]';
                            let $close = $(close_css);
                            self.logInfo('!!!!!!!!!!! VIDEO CLOSE LEN ' + $close.length);
                            if ($close.length > 0) {
                                self.click_element($close);
                                self.console_log('close button clicked');

                                src = self.documentinfo.get_url(`${clientPhone}_${data_id}`);
                                self.console_log('get_url after download', data_id, src);
                                //document прогружен, можно слать
                                if (src) {
                                    self.console_log('src ok');
                                    if (self.localStorage_getItem(src) == null) {
                                        self.localStorage_setItem(src, true); //флаг, чтоб не слать дважды
                                        self.console_log('before convertAudio');
                                        self.convertAudio(src, function (base64Img, src) {
                                            self.replaceSmiles($msgEl);
                                            // Заменяем data-url потому что после последней обработки он поменялся
                                            $msgEl.attr('data-url', src);
                                            let text = self.get_selectable_text($msgEl);

                                            self.getNameFromCard($msgEl)
                                                .then((name) => {
                                                    // console.log('name: ', name);
                                                    self.sendMessage(clientPhone, $msgEl, {
                                                        type: "video",
                                                        body: text,
                                                        videoBlob: base64Img
                                                    }, avablob, name, selected)
                                                        .then(() => {
                                                            self.closeClientCard();
                                                            localStorage.removeItem(src);
                                                            resolve(1)
                                                        })
                                                })
                                        });
                                    }
                                }

                            } else {
                                self.logError(clientPhone, 'no video close element found ' + '[data-icon="x-viewer"]');
                                reject(-1);
                            }
                            resolve(1);
                        }, self.settings.video_timeout)
                    }
                }, self.settings.video_timeout);
            }
        });
    };

    // Отправка контакта
    self.sendContact = function ($msgEl, clientPhone, avablob, selected) {

        return new Promise(function (resolve, reject) {
            $msgEl[0].scrollIntoView();
            let data_id = $msgEl.attr(self.consts.css.data_id);
            self.console_log(data_id);
            console.log(data_id);
            self.documentinfo.current_id = `${clientPhone}_${data_id}`;
            let contact_card_css = self.settings.contact_preview_btn;
            let $clickable = $msgEl.find(contact_card_css);
            if ($clickable.length <= 0) {
                self.logError(clientPhone, 'no click element for contact ' + contact_card_css);

                self.getNameFromCard($msgEl)
                    .then((name) => {
                        // console.log('name: ', name);
                        self.sendMessage(clientPhone, $msgEl, {
                            type: "text",
                            body: "*** contact message received (system error occured - 2) ***"
                        }, avablob, name, selected)
                            .then(() => {
                                self.closeClientCard();
                                resolve(1)
                            })
                    })
            }
            self.click_element($clickable);
            let content = '';
            let timer = setTimeout(function () {
                // console.log('in timer contacts');
                content += '*** Whatsapp Contact ***\n';
                const iterEl = function (el) {
                    let e = $(el);
                    if (!e.children().length) {
                        if (e.text()) {
                            content += '\n' + e.text();
                        }
                        return true;
                    }
                    $.each(e.children(), function (i, elem) {
                        iterEl(elem);
                    })
                };
                iterEl(self.settings.contact_card);
                let $e = $('[data-icon="x"]');
                $e.click();

                if (self.isGreenMessage($msgEl)) {
                    let timerOpen = setTimeout(() => {
                        // console.log('in timer open');
                        let openBtn = $(self.css_settings.get_name.open_btn);
                        self.click_element(openBtn);
                        let timerClient = setTimeout(function () {
                            let clientCard = $(self.css_settings.get_name.card);
                            let clientCardTop = clientCard.find(self.css_settings.get_name.card_top);
                            let clientName = clientCardTop.find(self.css_settings.get_name.name_div).find(self.css_settings.get_name.name_span);
                            let name = clientName.length > 0 ? clientName.html() : '';
                            self.sendMessage(clientPhone, $msgEl, {
                                data_name: name,
                                type: "text",
                                body: content
                            }, avablob, name, selected)
                                .then(function () {
                                    let closeBtn = clientCard.find(self.css_settings.get_name.close_btn);
                                    self.click_element(closeBtn);
                                    resolve(1);
                                });
                        }, self.settings.client_card_timeout);
                    }, 500)
                } else {
                    self.sendMessage(clientPhone, $msgEl, {
                        type: "text",
                        body: content
                    }, avablob, name, selected)
                        .then(function () {
                            $e = $('[data-icon="x-light"]');
                            $e.click();
                            resolve(1);
                        });
                }
            }, self.settings.contact_timeout);
        });
    };


    // Отправка геолокации
    self.sendMap = function ($msgEl, clientPhone, avablob, selected) {
        try {
            self.console_log(clientPhone, "sendMap");
            self.replaceSmiles($msgEl);
            let href = decodeURIComponent($msgEl.find('a').attr('href'));
            let matched = href.match(self.css_settings.messages.types.location.pattern);
            let lat, lng;
            if (matched == null) {
                self.logError(clientPhone, 'Cant parse map coordinates!' + href);
                lat = '1.0';
                lng = '1.0';
            } else {
                lat = matched[self.css_settings.messages.types.location.lat_index];
                lng = matched[self.css_settings.messages.types.location.lng_index];
            }

            return self.getNameFromCard($msgEl)
                .then((name) => {
                    // console.log('name: ', name);
                    self.sendMessage(clientPhone, $msgEl, {
                        type: "map",
                        lat: lat,
                        lng: lng
                    }, avablob, name, selected)
                        .then(() => {
                            self.closeClientCard();
                            resolve(1)
                        })
                })

        } catch (e) {
            self.logError(clientPhone, 'Error send Map');
            self.logError(clientPhone, e);
        }
    };


    // Отправка пропущенного звонка
    self.sendMissedCall = function ($msgEl, clientPhone, avablob, selected) {
        // console.log('send call', `selected ${selected}`);
        let callType = $msgEl.find('[data-icon=miss]').length ? 'audio' : 'video';
        return new Promise(function (resolve, reject) {
            self.sendMessage(
                clientPhone,
                $msgEl,
                {
                    type: 'text',
                    // body: $msgEl[0].outerText
                    body: `*** Incoming WhatsApp ${callType} call ***`
                },
                avablob, '', selected, true).then(resolve(1))
        })
    };

    //Отарвка свернутых изображений с таймаутом на прогрузку
    self.sendWrapped = function ($msgElRoot, clientPhone, avablob, selected) {
        return new Promise(function (resolve, reject) {
                console.log('Send wrapped=>', $msgElRoot);
                let names = null;
                if (self.isGroupChat(clientPhone)) {
                    names = self.get_names($msgElRoot);
                }
                let wrappedImages = self.getImagesFromWrapped($msgElRoot);
                console.log('Send [IMAGES] wrapped=>', wrappedImages);
                // let firstDate = wrappedImages.prevObject[0].querySelector('._3fnHB').textContent;
                let firstDate = wrappedImages[0].querySelector(self.css_settings.messages.inbox_datetime).textContent;
                firstDate = self.makeTime(firstDate);
                // let blockSize = wrappedImages.prevObject[3].querySelector('._1drsQ') ? wrappedImages.prevObject[3].querySelector('._1drsQ').textContent: '+0';
                let blockSize = wrappedImages[3].textContent && wrappedImages[3].textContent.startsWith('+') ? wrappedImages[3].textContent : '+0';
                // console.log('wrapped id', blockSize.startsWith('+') ? firstDate + blockSize : firstDate + "0");
                if (blockSize) {
                    console.log('wrapped id', blockSize.startsWith('+') ? firstDate + blockSize : firstDate + "0");
                }
                self.console_log(`in sendWrapped`);
                // Добавить изображения из свернутого блока
                self.setDataIdForWrappedImages(wrappedImages)
                    .then((wrappedImagesArr) => {
                            console.log('wrapped with ids', wrappedImagesArr.length, wrappedImagesArr);
                            let data = {};
                            data.body = '';
                            console.log('get here', wrappedImagesArr.length);
                            for (let wrappedElem of wrappedImagesArr) {
                                if (wrappedElem !== null) {
                                    console.log('in cycle');
                                    console.log(wrappedElem);
                                    // try to fix send images to wrong client
                                    let clientPhoneFromEl = wrappedElem.querySelector('._1zGQT._26GKj').getAttribute('data-clientphone');
                                    console.log(`clientPhoneFromEl ${clientPhoneFromEl}`);
                                    let phone;
                                    if (clientPhoneFromEl !== null) {
                                        phone = clientPhoneFromEl
                                    } else {
                                        phone = clientPhone
                                    }
                                    // let clientPhone = clientPhone === clientPhoneFromEl ? clientPhone : clientPhoneFromEl;
                                    console.log(`clientPhone ${phone}`);
                                    let $msgEl_1 = $(wrappedElem);
                                    let $msgEl = $msgEl_1.find('._26GKj ');
                                    let msgType = $msgEl.attr(self.consts.css.data_id).search(/VIDEO/g) > 0 ? 'video' : 'image';
                                    // let imgEl = $msgEl.find('img').length > 0 ? $msgEl.find('img') : $msgEl.find('video');
                                    let imgEl = $msgEl.find('img');
                                    let imgSrc = imgEl.attr('src');
                                    data.type = msgType;
                                    let decodedImgSrc = decodeURIComponent(imgSrc);
                                    console.log('decoded src', decodedImgSrc, decodedImgSrc.indexOf(self.consts.method.https));
                                    console.log('wrapped msg', $msgEl);
                                    console.log('type msg', msgType);
                                    if (decodedImgSrc.indexOf(self.consts.method.https) > -1) {
                                        self.convertAudio(imgSrc, function (base64Img, imgSrc) {
                                            console.log('in convert Audio', imgSrc);
                                            $msgEl.attr('data-url', imgSrc);
                                            self.sendMessage(phone, $msgEl, {
                                                    type: msgType,
                                                    body: '',
                                                    imageBlob: base64Img
                                                },
                                                avablob, '', selected, false, true, `us_WRAPPED_${firstDate + blockSize}`, names)
                                                .then(() => {
                                                    // self.closeClientCard();
                                                    localStorage.removeItem(imgSrc);
                                                    resolve(1)
                                                })
                                        })
                                    } else if (decodedImgSrc.indexOf('data:image/jpeg') > -1) {
                                        self.console_log(phone, 'NO HTTPS IN WRAPPED MSG, SEND BLOB (PREVIEW). MAYBE NEED TO SET BIGGER TIMEOUT');
                                        self.sendMessage(phone, $msgEl, {
                                                type: msgType,
                                                body: `${msgType} не загрузилось`,
                                                imageBlob: decodedImgSrc
                                            },
                                            avablob, '', selected, false, true, `us_WRAPPED_${firstDate + blockSize}`).then((resolve(1)))
                                    }
                                }
                            } // конец цикла отправки
                        }, (error) => {
                            self.console_log(`sendWrapped error ${error}`);
                            reject(-1);
                        }
                    )
            }
        )
    };

    self.defaultBasketItem = function (clientPhone, data_id, src, time, wa_data_id, item_text) {
        return $(`<div class="FTBzM message-in" data-id="${wa_data_id}"><span></span><div class="_1zGQT _26GKj message-text custom-img" data-clientphone="${clientPhone}" data-messageid="${data_id}" data-url="${src}" data-basket_item="true"><div class="_2Wx_5 _3LG3B"><div class="_3SaET"><div><div class="_3mdDl"><img src="${src}" class="_18vxA" style="width: 100%;"><div class="_3TrQs"></div></div><div class="iVt71"><div class="_3MYI2 _3UgZX"><span class="_3fnHB" dir="auto">${time}</span></div></div></div></div></div><span></span><div class="gxf3C" role="button"><span data-icon="forward-chat" class=""><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25 25" width="25" height="25"><path fill-rule="evenodd" clip-rule="evenodd" fill="#FFF" d="M14.248 6.973a.688.688 0 0 1 1.174-.488l5.131 5.136a.687.687 0 0 1 0 .973l-5.131 5.136a.688.688 0 0 1-1.174-.488v-2.319c-4.326 0-7.495 1.235-9.85 3.914-.209.237-.596.036-.511-.268 1.215-4.391 4.181-8.492 10.361-9.376v-2.22z"></path></svg></span></div><span dir="ltr" class="_1VzZY selectable-text invisible-space copyable-text"><span>${item_text}</span></span></div></div>`)
    };

    self.sendBasket = function ($msgEl, clientPhone, avablob, selected) {
        return new Promise(function (resolve, reject) {
            console.log('Send Basket!');
            let wa_data_id = self.getWAiD($msgEl);
            let data_time = $msgEl.find(self.css_settings.messages.inbox_datetime).text();
            let shopName = $msgEl.find(self.css_settings.basket.shop_name).text();
            let amount = $msgEl.find(self.css_settings.basket.amount).text();
            let basketText = $msgEl.find(self.css_settings.basket.text).text();
            let textMessage = `Basket: ${shopName}\nin basket: ${amount}\ntext: ${basketText}`;
            let name = '';
            let basketItems = 0;
            let processedBasketItems = 0;
            console.log('basket text msg:', textMessage);
            self.sendMessage(clientPhone, $msgEl, {
                type: "text",
                body: textMessage
            }, avablob, name, selected)
                .then(() => {
                    // resolve(1)
                    $(self.css_settings.basket.show_button).click();
                    setTimeout(() => {
                        let basket = $(self.css_settings.basket.opened);
                        console.log(basket);
                        let goods = basket.find(self.css_settings.basket.goods);
                        console.log(goods);
                        basketItems = goods.length;
                        for (let idx in goods) {
                            if (goods.hasOwnProperty(idx) && parseInt(idx + 1)) {
                                let good_idx = parseInt(idx);
                                let good = $(goods[good_idx]);
                                let good_wa_id = `${wa_data_id}_${good_idx + 1}`;
                                console.log(good);
                                let goodText = good.text();
                                console.log(goodText);
                                let goodImgSrc = good.find(self.css_settings.basket.img_div).css('backgroundImage');
                                goodImgSrc = goodImgSrc ? goodImgSrc.slice(5, -2) : '';
                                console.log(goodImgSrc);
                                let data_id = `us_IMAGE_${data_time}_${good_idx + 1}_length_${goodText.length}`;
                                console.log(data_id);
                                let itemElem = self.defaultBasketItem(clientPhone, data_id, goodImgSrc, data_time, good_wa_id, goodText);
                                console.log(itemElem);
                                let msgEl = itemElem.find('._26GKj');
                                let imgEl = msgEl.find('img');
                                let imgSrc = imgEl.attr('src');
                                // let decodedImgSrc = decodeURIComponent(imgSrc);
                                self.convertAudio(imgSrc, function (base64Img, imgSrc) {
                                    console.log('in convert Audio', imgSrc);
                                    $msgEl.attr('data-url', imgSrc);
                                    self.sendMessage(clientPhone, msgEl, {
                                            type: 'image',
                                            body: goodText,
                                            imageBlob: base64Img
                                        },
                                        avablob, '', selected, false, false)
                                        .then(() => {
                                            localStorage.removeItem(imgSrc);
                                            processedBasketItems++;
                                            // close basket preview
                                            console.log(`basket len: ${basketItems}, processed: ${processedBasketItems}`);
                                            if (processedBasketItems === basketItems) {
                                                let closeBtn = basket.parent().find(self.css_settings.basket.back_button);
                                                closeBtn.click();
                                                resolve(1)
                                            }
                                        })
                                })
                            }
                        }
                    }, self.css_settings.basket.timeout);
                });
        })
    };

    // Конвертирование медиа в base64
    self.convertAudio = function (url, callback) {
        let xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'blob';
        xhr.onload = function (e) {
            if (xhr.status === 200) {
                var reader = new window.FileReader();
                reader.onloadend = function (e) {
                    self.console_log('[SEND]', reader.result.length, url);
                    callback(reader.result, url);
                };
                reader.readAsDataURL(xhr.response);
            }
        };
        xhr.onerror = function (e) {
            self.console_log("Error " + e.target.status + " occurred while receiving " + url);
        };
        xhr.send();
    };

    // Получить заголовок чата
    self.getChatTitle = function () {
        return document.querySelector(self.css_settings.chat_props.chat_title).textContent;
    };

    self.STORAGE = {
        saveLastId: function (clientPhone, $msgEl) {
            self.console_log('saveLastId');
            let $msg = $msgEl;
            if ($msg.attr(self.consts.css.data_id) === undefined) {
                $msg = $msgEl.find('[' + self.consts.css.data_id + ']').not(self.css_settings.messages.inbox_exclude);
            }
            if ($msg.attr(self.consts.css.data_id) === undefined) {
                self.logError(clientPhone, "CANT EXTRACT DATA_ID FROM: " + $msgEl[0].outerHTML);
            } else {
                let lastMsgId = self.parseLastIdToShortId(clientPhone, $msg.attr(self.consts.css.data_id));
                self.localStorage_setItem(clientPhone, lastMsgId);
                self.localStorage_setItem('url_' + clientPhone, $msg.attr(self.consts.css.data_url));
            }
        },
        getDataId: function (clientPhone, $msgEl) {
            let $msg = $msgEl;
            if ($msg.attr(self.consts.css.data_id) === undefined) {
                $msg = $msgEl.find('[' + self.consts.css.data_id + ']').not(self.css_settings.messages.inbox_exclude);
            }
            if ($msg.attr(self.consts.css.data_id) === undefined) {
                self.logError(clientPhone, "CANT EXTRACT DATA_ID FROM: " + $msgEl[0].outerHTML);
            } else {
                return self.parseLastIdToShortId(clientPhone, $msg.attr(self.consts.css.data_id))
            }
        },
        getLastId: function (clientPhone) {
            return self.localStorage_getItem(clientPhone);
        },
        getLastUrl: function (clientPhone) {
            return self.localStorage_getItem('url_' + clientPhone);
        },
        saveTimeLastId: function (clientPhone, $msg) {
            let time = $msg.find(self.css_settings.messages.inbox_datetime).text();
            time = time.length > 0 ? time : $msg[0].outerText.slice(-5);
            time = self.makeTime(time);
            return self.localStorage_setItem("time-" + clientPhone, time);
        },
        getTimeLastId: function (clientPhone) {
            return self.localStorage_getItem("time-" + clientPhone);
        }
    };


    /*
      Вытаскиваем номер телефона из названия диалога
    */
    self.isdigit = function (c) {
        return "" + parseInt(c) != "NaN"
    };

    // Парсинг телефона
    self.extractPhone = function (title) {
        if (title) {
            let p = '';
            let pp = '';
            let r = '';
            for (let i = 0; i < title.length; i++) {
                let c = title[i];
                try {
                    if (self.isdigit(c)) {
                        if ((p === '+') || (p === '-') || (p === ' ') || (p === '(') || (p === ')') || self.isdigit(pp) || !p) {
                            if ((p === '-') && !r) {
                                continue;
                            }
                            r += c;
                        } else {
                            r = '';
                        }
                    } else if ((c !== '+') && (c !== '-') && (c !== ' ') && (c !== '(') && (c !== ')')) {
                        if (r.length > 8) {
                            break;
                        }
                        r = '';
                    } else {
                        pp = '';
                    }
                } finally {
                    if ((c !== '+') && (c !== '-') && (c !== ' ') && (c !== '(') && (c !== ')')) {
                        pp += c;
                    }
                    p = c;
                }
            }
            if (r.length > 8) {
                return r;
            }
            return title;
        }
        return title;
    };

    // Получить заголовок чата
    self.getActiveChatTitle = function () {
        let $span_title = $(self.css_settings.chat_props.active_title);
        // console.log($span_title);
        if ($span_title.length > 0) {
            let e = $span_title[0];
            return e.textContent;
        }
        return '';
    };

    // Получить телефон выбранного чата
    self.getPhoneFromActiveChat = function () {
        return self.extractPhone(self.getActiveChatTitle());
    };

    /*
      Тестирование функций
    */
    self.vlad = {
        extractphone: function (phone) {
            return self.extractPhone(phone);
        },
        activechattitle: function () {
            return self.getActiveChatTitle();
        },
        mark_active_chat: function (mark_id) {
            let $active_chats = $('.chat.active');
            $active_chats.each(function (index, value) {
                let $chat_title = $(value).find('[title]');
                if (($chat_title.length > 0) && ($chat_title.attr('title') === self.vlad.activechattitle())) {
                    $(value).attr('broadcast', mark_id);
                    return false
                }
            });
            return $active_chats.length;
        },
        getappstatus: function () {
            return self.localStorage_getItem("appStatus") || self.getAppStatus();
        },
        get_element_coord: function ($element) {
            if ($element) {
                let offset = $element.offset();
                if (offset) {
                    return '(' + [offset['left'], offset['top'], $element.width(), $element.height()].join() + ')'
                }
            }
            return 'None'
        },
        getcoord: function (css_selector) {
            return self.vlad.get_element_coord($(css_selector));
        },
        image_filename: '',
        get_last_unread: function (start, stop, css_selector) {
            let $unread = $(css_selector);
            let $last = null;
            if ($unread) {
                $last = null;
                $unread.each(function (index) {
                    var $un = $(this);
                    if (($last == null) || ($un.offset()['top'] > $last.offset()['top'])) {
                        if ((start === 0) || ($un.offset()['top'] >= start)) {
                            if ((stop === 0) || ($un.offset()['top'] + $un.height()) <= stop) {
                                $last = $un;
                            }
                        }
                    }
                });
            }
            return self.vlad.get_element_coord($last);
        },
        get_first_element: function (start, stop, css_selector) {
            let $last = null;
            let $unread = $(css_selector);
            if ($unread) {
                $last = null;
                $unread.each(function (index) {
                    let $un = $(this);
                    if (($last === null) || ($un.offset()['top'] < $last.offset()['top'])) {
                        if ((start === 0) || ($un.offset()['top'] >= start)) {
                            if ((stop === 0) || ($un.offset()['top'] + $un.height()) <= stop) {
                                $last = $un;
                            }
                        }
                    }
                });
            }
            return $last;
        },
        get_first: function (start, stop, css_selector) {
            let $last = self.vlad.get_first_element(start, stop, css_selector);
            return self.vlad.get_element_coord($last);
        },
        get_first_status: function (start, stop, css_selector) {
            self.console_log('checking status');
            console.log('checking status', start, stop, css_selector, typeof (css_selector));
            let $chat = self.vlad.get_first_element(start, stop, css_selector);
            console.log('get_first_status', $chat);
            if ($chat.length > 0) {
                let $icon_ack = $chat.find(self.css_settings.message_status.acknowledge);
                if ($icon_ack.length > 0) {
                    console.log($icon_ack[0].classList, $icon_ack[0].classList.contains(self.css_settings.message_status.read));
                    if ($icon_ack.has(self.css_settings.message_status.check).length > 0) {
                        // console.log('SENT');
                        return 'sent';
                    } else if (
                        $icon_ack.has(self.css_settings.message_status.dbl_check_ack).length > 0
                        || ($icon_ack.has(self.css_settings.message_status.dbl_check).length > 0
                        // && $icon_ack.hasClass(self.css_settings.message_status.read))
                        && $icon_ack[0].classList.contains(self.css_settings.message_status.read))
                    ) {
                        // console.log('READ');
                        return 'read';
                    } else if ($icon_ack.has(self.css_settings.message_status.dbl_check).length > 0) {
                        // console.log('DELIVERED');
                        return 'delivered';
                    } else if ($icon_ack.has('[title]').length > 0) {
                        // console.log('READ*');
                        return 'read';
                    }
                }
            }
            return 'not found';
        },
        broadcast_processed: [],
        clear_broadcast: function () {
            let r = self.vlad.broadcast_processed.length;
            self.vlad.broadcast_processed = [];
            return r;
        },
        get_first_broadcast: function (start, stop, css_selector) {
            let $unread = $(css_selector);
            let $last = null;
            if ($unread) {
                $last = null;
                $unread.each(function (index) {
                    var $un = $(this);
                    if (($last === null) || ($un.offset()['top'] < $last.offset()['top'])) {
                        if ((start === 0) || ($un.offset()['top'] >= start)) {
                            if ((stop === 0) || ($un.offset()['top'] + $un.height()) <= stop) {
                                if ($.inArray($un.find('[title]').attr('title'), self.vlad.broadcast_processed) === -1) {
                                    $last = $un;
                                }
                            }
                        }
                    }
                });
            }
            if ($last) {
                self.vlad.broadcast_processed.push($last.find('[title]').attr('title'));
                $last.attr(self.consts.css.broadcast, '1')
            }
            return self.vlad.get_element_coord($last);
        },
        set_status: function (total, unread, log_message, remaining) {
            $('#version').find('#qty').text(total.toString() + '/' + unread.toString());
            $('#version').find('#log').text(log_message);
            $('#version').find('#remain').text(remaining);
        },
        send_status: function (status) {
            self.logInfo('send_status ' + status);
            self.sendAppStatus(status);
        },
    };

    self.check_selection = function (css_selector) {
        let $e = $(css_selector);
        if ($e.length > 0) {
            if (document.getSelection().toString() === $e.text()) {
                return '1';
            } else if (document.getSelection().toString() === $e.val()) {
                return '1';
            }
        }
        return '0';
    };

    // Триггер ивентов
    self.triggerEvent = function (element, event_name) {
        try {
            let event = new Event(event_name);
            element.dispatchEvent(event);
        } catch (e) {
            !self.settings.send_only ? console.log(e) : null
        }

    };

    self.searchPhoneFunc = function (phone, search_editable, phone_input_div) {
        let btn = $(search_editable).has(phone_input_div).find(phone_input_div).text(phone);
        console.log('CLICKING FROM DELPHI', self.click_element(btn));
    };

    self.typeMessage = function (message_text) {

    };

    // Вставка значения в инпут
    self.pasteInputVal = function (css, val, searchPhone = 0) {
        console.log('paste message', val);
        self.console_log(`paste val: (${css}) val: ${val}`);
        if (searchPhone == 1) {
            let btn = $('._3u328').first().text(val);
            console.log('CLICKING FROM PYTHON', self.click_element(btn));
            // self.click_element(btn);
        } else {
            let input = document.querySelector(css);
            console.log('INPUT FIELD FOCUSED');
            // self.console_log('input', input);
            // self.console_log('value', val);
            !self.settings.send_only ? console.log('tryin to focus', css, val) : null;
            try {
                self.triggerEvent(input, "focus");
                let valSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                valSetter.call(input, val);
                let load = new Event("input", {bubbles: true});
                input.dispatchEvent(load);
            } catch (e) {
                console.error(e);
                let field = $(css).text(val);
                self.console_log(`found (${css}) ${field.length}; ${$(css).text(val)}`);
                // self.click_element(field)
            }
        }
    };

    self.openByLinkResult = function (vid, phone, header_menu) {
        self.openByLink(phone, header_menu).then(function (result) {
            return wapp_result(result, vid)
        })
    };

    /**
     * Открытие диалога по ссылке
     * @param phone
     * @param header_menu
     * @return 0 - невреный номер телефона, 1 - перешли в чат с названием phone, 2 - вышли по таймауту
     */
    self.openByLink = function (phone, header_menu) {
        return new Promise(function (resolve, reject) {
            try {
                let customLink = document.createElement("a");
                customLink.href = "https://wa.me/" + phone;
                customLink.title = "https://wa.me/" + phone;
                customLink.target = "_blank";
                customLink.rel = "noopener noreferrer";
                customLink.id = "customLink";
                console.log(customLink);
                self.console_log(`create link ${customLink}`);
                let block = document.querySelector(header_menu); // хедер с меню
                console.log(block);
                self.console_log(`find header ${block}`);
                if (block) {
                    block.appendChild(customLink);
                    let l = document.querySelector('#customLink');
                    self.console_log(`find link ${l}`);
                    l.click();
                    block.removeChild(customLink)
                    //document.location.assign("https://web.whatsapp.com/send?phone=" + phone)
                }
            } catch (e) {
                self.logError(phone, e);
                return reject(-1)
            }
            let counter = 0;
            let timer = setInterval(() => {
                let chatPhone = self.getPhoneFromActiveChat();
                let popup = document.querySelector(self.css_settings.popup_window);
                if (popup && popup.querySelector(self.css_settings.popup_start_chat)) {
                    popup = null
                }
                counter++;
                console.log(`[open by link (${counter} sec)] passed phone ${phone}, chat title ${chatPhone}`);
                self.console_log(`[open by link (${counter} sec)] passed phone ${phone}, chat title ${chatPhone}`);
                console.log(`popup ${self.css_settings.popup_window}`);
                if (chatPhone === phone) {
                    console.log('check phone');
                    clearInterval(timer);
                    resolve(1)
                }
                if (popup) {
                    console.log('check popup');
                    self.console_log(`popup: ${popup.innerHTML}`);
                    clearInterval(timer);
                    resolve(0)
                }
                if (counter >= self.settings.open_by_link_timeout) {
                    console.log('check counter');
                    clearInterval(timer);
                    resolve(2)
                }
                console.log(`[*open by link (${counter} sec)] passed phone ${phone}, chat title ${chatPhone}`);
            }, 1000)
        })
    };


    /**
     * Получить границы элемента
     * Необходимо для рандомизации координаты клика внутри элемента
     * @param css
     * @returns array из 4 элементов, левая, правая, верхняя и нижняя грани, с внутренним отступом в 10 процентов, либо None
     */
    self.getRect = (css) => {

        if (!document.querySelector(css)) {
            return 'None'
        }

        let rect = document.querySelector(css).getBoundingClientRect();
        return rect ? [rect['left'] + rect['width'] * 0.1, rect['right'] - rect['width'] * 0.1, rect['top'] + rect['height'] * 0.1, rect['bottom'] - rect['height'] * 0.1].map(el => parseInt(el)) : 'None'
    };

    // Получение типа выбранного чата
    self.getCurrentChatType = () => {
        if (document.querySelector(self.css.active_chat_group) !== null) {
            return 'group'
        }
        if (document.querySelector(self.css.active_chat_broadcast) !== null) {
            return 'broadcast'
        }
        return 'base'
    };

    // Триггер ивентов мыши
    self.fireMouseEvents = (query, eventNames) => {
        let element = document.querySelector(query);
        if (element && eventNames && eventNames.length) {
            for (let index in eventNames) {
                let eventName = eventNames[index];
                if (element.fireEvent) {
                    element.fireEvent('on' + eventName);
                } else {
                    let eventObject = document.createEvent('MouseEvents');
                    eventObject.initEvent(eventName, true, false);
                    element.dispatchEvent(eventObject);
                }
            }
        }
    };


    // Убирает смайлики из строки
    self.remSmilesFromStr = function (rawStr) {
        let pattern = /(<([^>]+)>)/ig;
        // console.log(rawStr.replace(pattern, ""));
        return rawStr.replace(pattern, "");
    };

    // Получаем имя из карточки клиента
    self.getNameFromCard = function ($msgEl) {
        // self.console_log('start get name from card');
        // console.log('start get name from card', self.getActiveChatTitle());
        if (self.settings.get_name_enable && self.getCurrentChatType() === 'base' && self.isGreenMessage($msgEl)) {
            return new Promise(function (resolve, reject) {
                let openBtn = $(self.css_settings.get_name.open_btn);
                openBtn.click();
                // self.click_element(openBtn);
                // console.log('open card');
                setTimeout(() => {
                    let clientCard = $(self.css_settings.get_name.card);
                    let clientCardTop = clientCard.find(self.css_settings.get_name.card_top);
                    let clientName = clientCardTop.find(self.css_settings.get_name.name_div).find(self.css_settings.get_name.name_span);
                    console.log(`>>> ${clientName} >> ${clientName.length}`);
                    console.log(clientName);
                    let name = clientName.length > 0 ? clientName.html() : '';
                    name = self.remSmilesFromStr(name);
                    console.log('>>> ', name);
                    resolve(name)
                }, self.settings.client_card_timeout)
            })
        } else {
            // console.log('getName return empty');
            return new Promise(function (resolve, reject) {
                resolve('')
            })
        }
    };

    // Закрывает кароточку клиента
    self.closeClientCard = function () {
        let clientCard = $(self.css_settings.get_name.card);
        if (clientCard.length > 0) {
            let closeBtn = clientCard.find(self.css_settings.get_name.close_btn);
            // self.click_element(closeBtn);
            closeBtn.click();
        }
    };

    // Удаляет из LocalStorage записи кликера
    // appStatus, devicePhone, qr-data-ref, avacount, time-*, url_* и последнего сообщения для клиента
    self.clearLocalStorage = () => {
        let clickerKeys = ['appStatus', 'devicePhone', 'qr-data-ref'];
        let storageKeys = Object.keys(localStorage);
        for (let key of storageKeys) {
            if (clickerKeys.indexOf(key) !== -1
                || key.match(/avacount-|time-|url_|name-/)
                || localStorage.getItem(key) && localStorage.getItem(key).startsWith('us_')) {
                // console.log(`remove ${key}`);
                localStorage.removeItem(key);
            }
        }
    };

    // Проверяет, что клиент отправил сообщение впервые
    self.isGreenMessage = function ($msg) {
        return $msg[0].parentElement.style.backgroundColor === 'green'
    };

    // Находим выбранные сообщения
    self.getSelectedMessages = function () {
        return $(self.css_settings.messages.selected_messages).children(self.settings.msg_bubble);
    };

    // Отправляем выбранные сообщения
    self.sendSelectedMessages = function () {
        // let selectedMessages = self.getSelectedMessages();
        // let messagesForSend = selectedMessages.find('.vW7d1');
        let messagesForSend = self.getSelectedMessages();
        let clientPhone = self.getPhoneFromActiveChat();
        // console.log(`1. ${clientPhone}`);
        let sendSelected = new Promise.resolve(1);
        self.console_log(`Send selected from ${clientPhone}`);
        console.log(messagesForSend);
        sendSelected
            .then((res) => {
                console.log(res);
                self.console_log(`Send msg ${clientPhone}`);
                self.sendMessages(messagesForSend, clientPhone, '', selected = true)
            })
            .then((res) => {
                self.console_log(`Send ${messagesForSend.length} selected messages!`);
                if (messagesForSend.length > 0) {
                    alert(`Send ${messagesForSend.length} selected messages!`)
                }
            })
    };

    // Проверяет наличие непрочитанных сообщений в найденном диалоге
    self.hasDialogUnreadMessages = function (vid) {
        let dialog = $('._2UaNq').first();
        // console.log(dialog);
        return wapp_result(dialog ? dialog.hasClass('_2ko65') : 0, vid)

    };

    // Проверяет архивный чат или нет
    self.isArchiveChat = function (vid) {
        let isArchive = $(self.css.archive_chat).length > 0;
        // console.log('Archive?:', isArchive);
        return wapp_result(isArchive ? 1 : 0, vid)
    };

    // закрыть предупреждение о низком заряде батареи
    self.lowBatteryClose = function () {
        self.console_log('trying to close battery');
        let lowBattery = $('[data-icon="alert-battery"]');
        if (lowBattery.length === 0) {
            self.console_log('close battery 0');
        } else {
            let pEl = lowBattery.closest('div').parent().closest('div');
            // console.log(pEl);
            let closeBtn = pEl.find('[data-icon="x"]');
            // console.log(closeBtn);
            // closeBtn.click();
            self.click_element(closeBtn);
            self.addStyles();
            self.console_log('close battery 1');
        }
    };

    self.changeVersionStyle = function () {
        $("#version").css("opacity", parseFloat(self.settings.opacity))
    };


    /**
     * верхний элемент (чат) в видимой области списка чатов
     * @param s
     * @return array из 4 элементов, левая, правая, верхняя и нижняя грани, с внутренним отступом в 10 процентов, либо None
     */
    self.inWindow = function (vid) {
        let scrollTop = $('#pane-side').scrollTop();
        let paneSideHeight = $('#pane-side').height(); // const
        let currentEls = $(self.css_settings.css_chat);
        let lostConnect = $(self.css_settings.lost_connect).height() ? 1 : 0;
        // console.log(lostConnect);
        // console.log(`scrollTop: ${scrollTop}, height: ${paneSideHeight}`);
        let result = [];
        try {
            currentEls.each(function () {
                let el = $(this);
                let offset = el.offset();
                // console.log(offset);
                if (0 <= offset.top && (el.height() + offset.top) < (scrollTop + paneSideHeight))
                    result.push(this);
            });
            result = result.sort(function (a, b) {
                return $(a).offset().top > $(b).offset().top
            });
            if (scrollTop === 0) {
                let topChat = $(result)[lostConnect];
            }
            console.log(result);
            let topChat = $(result)[1 + lostConnect];
            console.log(topChat);
            $(topChat).click();
            let rect = topChat.getBoundingClientRect();
            let coords = rect ? [rect['left'] + rect['width'] * 0.1, rect['right'] - rect['width'] * 0.1, rect['top'] + rect['height'] * 0.1, rect['bottom'] - rect['height'] * 0.1].map(el => parseInt(el)) : 'None';
            console.log(coords);
            return wapp_result(coords, vid)
        } catch (e) {
            self.console_log('DELETE', e);
            return wapp_result(0, vid)
        }

    };

    self.visibleHeight = function (vid) {
        let scrollTop = $('#pane-side').scrollTop();
        let paneSideHeight = $('#pane-side').height(); // const
        let paneSideAbsCoord = scrollTop + $('#pane-side').offset().top; // координата верха списка чатов относительно window
        console.log(`scrollTop: ${scrollTop}, height: ${paneSideHeight}`);
        console.log('ps start', paneSideAbsCoord);
        console.log('ps end', paneSideAbsCoord + paneSideHeight);
        let currentEls = $(self.css_settings.css_chat);
        let result = [];
        currentEls.each(function () {
            let el = $(this);
            let offset = el.offset();
            let elBottomBord = el.height() + offset.top;
            // console.log(`el offset`, offset.top, elBottomBord, paneSideAbsCoord + paneSideHeight);
            if (scrollTop <= offset.top && elBottomBord < (paneSideAbsCoord + paneSideHeight))
                result.push(this);
        });
        console.log(result);
        result = result.sort(function (a, b) {
            return $(a).offset().top > $(b).offset().top
        });
        console.log(result.length);
        // return wapp_result(result.length, vid)
    };

    self.testDownloader = function (url) {
        let xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'blob';
        xhr.onload = function (e) {
            if (xhr.status === 200) {
                var reader = new window.FileReader();
                reader.onloadend = function (e) {
                    let image = new Image();
                    image.src = reader.result;
                    image.onload = function () {
                        console.log(this.height, this.width, this.sizes);
                        self.console_log('[DOWNLOADED BEFORE DELAY]', this.height, this.width, this.sizes);
                    };
                    console.log(reader.result.length, url);
                    // console.log(reader.result, url);
                    self.console_log('[DOWNLOADED BEFORE DELAY]', reader.result.length, url)
                };
                reader.readAsDataURL(xhr.response);
            }
        };
        xhr.onerror = function (e) {
            console.log("Error " + e.target.status + " occurred while receiving " + url);
        };
        xhr.send();
    };

    self.isValidDate = function (d) {
        return d instanceof Date && !isNaN(d);
    };

    self.testTimeline = function (msgTimelineString) {
        console.log(`[TIMELINE STRING] ${msgTimelineString}`);
        let msgTimelineStringParsed = self.parseDate(msgTimelineString);
        console.log(`[TIMELINE STRING PARSED] ${msgTimelineStringParsed}`);
        let msg_timeline;
        msg_timeline = new Date(Date.parse(msgTimelineStringParsed));
        if (!self.isValidDate(msg_timeline)) {
            // не получилось собрать дату - попробуем поменять формат таймлайна
            let timelineFormatReversed = self.reverseTimelineFormat();
            if (timelineFormatReversed) {
                msgTimelineStringParsed = self.parseDate(msgTimelineString, timelineFormatReversed);
                console.log(`[TIMELINE REVERSED STRING PARSED] ${msgTimelineStringParsed}`);
                msg_timeline = new Date(Date.parse(msgTimelineStringParsed));
            } else {
                msg_timeline = self.getNowDateTimeParsed();
            }
        }
        let global_timeline = new Date(Date.now() - 864e5);
        if (self.settings.timeline) {
            global_timeline = new Date(Date.parse(self.parseDate(self.settings.timeline)));
        }

        console.log('[MESSAGE TIME] ' + msg_timeline);
        if (msg_timeline <= global_timeline) {
            console.log('TIMELINE ' + global_timeline);
            console.log('MSG WAS REJECTED');
            return 1;
        }
    };


});
