# -*- coding: cp1251 -*-

import time

def ungettext(a, b, c, count):
    if count > 1 and count < 5:
        b
    elif count >= 5:
        return c
    return a

def time_since_now(dt, ago = False):
    """
    Навеяно http://jehiah.cz/a/printing-relative-dates-in-python
    """
    chunks = (
      (60 * 60 * 24 * 365, lambda n: ungettext('год', 'года', 'лет', n)),
      (60 * 60 * 24 * 30, lambda n: ungettext('месяц', 'месяца', 'месяцев', n)),
      (60 * 60 * 24 * 7, lambda n : ungettext('неделя', 'недели', 'недель', n)),
      (60 * 60 * 24, lambda n : ungettext('день', 'дня', 'дней', n)),
      (60 * 60, lambda n: ungettext('час', 'часа', 'часов', n)),
      (60, lambda n: ungettext('минута', 'минуты', 'минут', n))
    )

    now = round(time.mktime(time.localtime()))
    t = round(time.mktime(dt))

    # ignore microsecond part of 'd' since we removed it from 'now'
    since = now - t
    if since <= 0:
        return 'Только что'
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break
    s = '%(number)d %(type)s' % {'number': count, 'type': name(count)}
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            s += ', %(number)d %(type)s' % {'number': count2, 'type': name2(count2)}
    if s and ago:
        s += ' назад'
    return s

def time_since_now_2(dt, ago = False):

    if not dt:
        return None

    names_1 = (
        lambda n: ungettext('год', 'года', 'лет', n),
        lambda n: ungettext('месяц', 'месяца', 'месяцев', n),
        lambda n : ungettext('неделя', 'недели', 'недель', n),
        lambda n : ungettext('день', 'дня', 'дней', n),
        lambda n: ungettext('час', 'часа', 'часов', n),
        lambda n: ungettext('минута', 'минуты', 'минут', n),
        )

    names_2 = (
        lambda n: ungettext('года', 'лет', 'лет', n),
        lambda n: ungettext('месяца', 'месяцев', 'месяцев', n),
        lambda n : ungettext('недели', 'недель', 'недель', n),
        lambda n : ungettext('дня', 'дней', 'дней', n),
        lambda n: ungettext('часа', 'часов', 'часов', n),
        lambda n: ungettext('минуты', 'минут', 'минут', n),
        )

    chunks = (
        60 * 60 * 24 * 365,
        60 * 60 * 24 * 30,
        60 * 60 * 24 * 7,
        60 * 60 * 24,
        60 * 60,
        60,
        )

    now = round(time.mktime(time.localtime()))
    t = round(time.mktime(dt))

    # ignore microsecond part of 'd' since we removed it from 'now'
    since = now - t
    if since <= 0:
        return 'Только что'
    elif since < 60:
        return 'Менее минуты'
    count = 0
    rest = 0
    i = -1
    for seconds in chunks:
        i += 1
        count, rest = divmod(since, seconds)
        if count != 0:
            break

    if rest:
        return 'Более %(number)d %(type)s' % {'number': count, 'type': names_2[i](count)}

    return '%(number)d %(type)s' % {'number': count, 'type': names_1[i](count)}

def time_since_now_3(dt, ago = False):

    if not dt:
        return None


    lt = time.localtime()
    now = round(time.mktime(lt))
    t = round(time.mktime(dt))

    # ignore microsecond part of 'd' since we removed it from 'now'
    since = now - t
    if since <= 0:
        return 'Только что'
    elif since < 60:
        return 'Минуту назад'
    elif lt[0] == dt[0] and lt[1] == dt[1] and lt[2] == dt[2]:
        return 'Сегодня, %-2.2d:%-2.2d' % (dt[3], dt[4])

    dt_days = t // 60 * 60 * 24
    now_days = now // 60 * 60 * 24
    since_days = now_days - dt_days
    if since_days == 1:
        return 'Вчера, %-2.2d:%-2.2d' % (dt[3], dt[4])

    if lt[0] == dt[0]:
        return '%-2.2d.%-2.2d, %-2.2d:%-2.2d' % (dt[2], dt[1], dt[3], dt[4])

    return '%-2.2d.%-2.2d.%d, %-2.2d:%-2.2d' % (dt[2], dt[1], dt[0], dt[3], dt[4])


def format_date_today(dt):
    """ Форматирует дату. Выдает сегодня, вчера """
    if dt:
        now = time.localtime()
        if now[2] == dt[2] and now[1] == dt[1] and now[0] == dt[0]:
            datestr = 'Сегодня'
        else:
            datestr = "%-2.2d.%-2.2d.%d" % (dt[2], dt[1], dt[0])
        return "%s %-2.2d:%-2.2d" % (datestr, dt[3], dt[4])

def format_date(dt):
    if dt:
        return "%-2.2d.%-2.2d.%d" % (dt[2], dt[1], dt[0])
    return ''


from columns import time_column

class since_column(time_column):

    def beforeInit(self, *args, **kwargs):
        super(since_column, self).beforeInit(*args, **kwargs)
        self.text_align = 'left'

    def format_rec_value(self, v):
        return self.format_value(time_since_now_3(v))
