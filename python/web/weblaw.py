# -*- coding: cp1251 -*-

"""

    ����������������

"""

from gtd.db.manager import PureSQL, DataManager
from gtd.db.dbconsts import DB_PG

from datetime import timedelta, date, datetime
from webbase import BaseWebApp
import os

from bottle import request

# ToDo: ��� �������� �� python 3 ��������
import urlparse
import urllib

import django
from django.template import loader
from django.conf import settings
import os

DOCUMENT_TEMPLATE = 'document.html'
DOCUMENT_NOT_FOUND = 'document_not_found.html'
DOCUMENT_LIST = 'document_list.html'


PARAM_DNUMBER = 'dnumber'
PARAM_DNUMBERSTRICT = 'dnumberstrict'
PARAM_DDATE = 'ddate'
PARAM_OWNERID = 'ownerid'
PARAM_TYPEID = 'typeid'
PARAM_TOPICS = 'topics'
PARAM_DOCNAME = 'docname'
PARAM_DOCTEXT = 'doctext'
PARAM_LASTWEEK = 'lastweek'
PARAM_LASTMONTH = 'lastmonth'
PARAM_LASTYEAR = 'lastyear'
PARAM_T = 't'
PARAM_PAGE = 'page'
PARAM_PERPAGE = 'perpage'

LAST_CONFIG = {
    PARAM_LASTWEEK: 7,
    PARAM_LASTMONTH: 30,
    PARAM_LASTYEAR: 365
}

SEARCH_PARAMS = [
    PARAM_DNUMBER,
    PARAM_DNUMBERSTRICT,
    PARAM_DDATE,
    PARAM_OWNERID,
    PARAM_TYPEID,
    PARAM_TOPICS,
    PARAM_DOCNAME,
    PARAM_DOCTEXT,
    PARAM_T,
] + LAST_CONFIG.keys()


DID_OP = DataManager.OS_IN + 'DID'


STATUS_UNKNOWN = -1
STATUS_EFFECTIVE = 0
STATUS_EXPIRED = 1
STATUS_NOT_EFFECTIVE_YET = 2


class DocStatus(object):
    status = STATUS_UNKNOWN
    description = ''
    condition = {}

    def __init__(self, *args, **kwargs):
        map(lambda key: setattr(self, key, kwargs[key]), kwargs.keys())


STATUSES = {
    STATUS_EFFECTIVE: DocStatus(
        status=STATUS_EFFECTIVE,
        description='�����������',
        condition={'docstatusisvalid': True, 'revstatusisvalid': True}
    ),
    STATUS_EXPIRED: DocStatus(
        status=STATUS_EXPIRED,
        description='�������������',
        condition={'docstatusisvalid': False, 'revstatusisvalid': True}
    ),
    STATUS_NOT_EFFECTIVE_YET: DocStatus(
        status=STATUS_NOT_EFFECTIVE_YET,
        description='�� ������� � ����',
        condition={'docstatusisvalid': None, 'revislast': True}
    ),
}



class WebLawApp(BaseWebApp):

    def init_route(self):
        super(WebLawApp, self).init_route()
        self.route('/tks_law.css', method='GET', callback=self.tks_law_css)
        self.route('/document/tks_law.css', method='GET', callback=self.tks_law_css)
        self.route('/search', method='GET', callback=self.search)
        self.route('/document/<did>', method='GET', callback=self.get_document)
        self.route('/search_document', method='GET', callback=self.search_document)
        self.route('/topics', method='GET', callback=self.get_topics)
        self.route('/topics/<topic>', method='GET', callback=self.get_topics)
        self.route('/downers', method='GET', callback=self.get_downers)
        self.route('/downers/<owner>', method='GET', callback=self.get_downers)
        self.route('/dtypes', method='GET', callback=self.get_dtypes)
        self.route('/dtypes/<typename>', method='GET', callback=self.get_dtypes)
        # �������
        self.route('/status', method='GET', callback=self.get_status)
        self.route('/status/<status>', method='GET', callback=self.get_status)

    def beforeInit(self, *args, **kwargs):
        super(WebLawApp, self).beforeInit(*args, **kwargs)
        self.document_template = DOCUMENT_TEMPLATE
        self.document_not_found = DOCUMENT_NOT_FOUND
        self.document_list = DOCUMENT_LIST

    def tks_law_css(self):
        return self.static('styles', 'tks_law_v2.css')

    def param_in(self, params):
        for param in params:
            value = self.get_param(param)
            if value:
                return value
        return None

    def get_static_context(self):
        data = self.get_template_context({'empty': True})
        if (self.get_param('search') != '0') and self.param_in(SEARCH_PARAMS):
            data.update(self.get_search_data())
        return data

    def adapt_fieldvalue(self, fieldvalue):
        if isinstance(fieldvalue, str):
            return unicode(fieldvalue, 'utf-8')
        return fieldvalue

    def get_field_names(self, include_html=False):
        r = [
                'did', 'doctitle', 'docname', 'sortdate',
                'docstatusisvalid', 'revstatusisvalid', 'revislast',
                'docbegindate', 'revbegindate'
            ]
        if include_html:
            r += ['dochtml']
        return r

    def get_document(self, did):
        d = self.dm.select('tkslaw.docs',
                           self.get_field_names(include_html=True),
                           {'did': did},
                           on_calc_record=self.update_document_rec
                           )
        if not d:
            return self.not_found()
        return self.get_document_template(self.get_template_context(d[0]))

    def update_document_rec(self, data):
        data['TITLE'] = data['DOCTITLE'] or data['DOCNAME']
        data['DOCTEXTTITLE'] = data['DOCTITLE'] or u'����� ���������'
        docstatus = data.get('DOCSTATUSISVALID')
        revstatus = data.get('REVSTATUSISVALID')
        if docstatus is None:
            if revstatus == False:
                data['STATUS'] = u'������������� �������� ���������, �� ����������� � ����.'
            data['STATUS'] = u'�������� �� ������� � ����.'
        elif docstatus:
            if revstatus is None:
                data['STATUS'] = u'�� ���������� � �������� �������� ������������ ���������.'
            elif revstatus == False:
                data['STATUS'] = u'������������� �������� ������������ ���������.'
            else:
                data['STATUS'] = u''
        else:
            data['STATUS'] = u'�������� ������� ����.'
        return data

    def get_document_template(self, data):
        return self.html_template(filename=self.document_template, request=request, **data)

    def search_document(self):
        d = self.get_search_data(include_html=True)
        # � ����������� �� ����, ��� ���������
        data = d['documents']
        if not data:
            # �����. ������ �� �������
            d = {
                'TITLE': u'��������� ��������'
            }
            return self.html_template(filename=self.document_not_found, **d)
        elif len(data) == 1:
            # ���� ������. ������ ���� ��������.
            return self.get_document_template(data[0])
        else:
            # ����� �������. ��������� ����������. ���� �������� ������� ������.
            return self.html_template(filename=self.document_list, **d)

    def get_dict_data(self, paramvalue, fieldname, tablename, fields, addcond=None):
        where = {}
        if paramvalue:
            where[self.dm.OS_MATCH_START + fieldname] = self.adapt_fieldvalue(paramvalue)
        if addcond:
            where.update(**addcond)
        return self.dm.select(tablename, fields, where, order_by=(fieldname, ))

    def get_topics(self, topic=None):
        """ ����� �� ������ ������� """
        d = self.get_dict_data(topic, 'topic', 'tkslaw.topics', ('id', 'topic'), addcond={'hasvalid': True})
        return self.json_or_not_found(d)

    def get_data_byid(self, paramvalue, keyfield, tblname, fields):
        if paramvalue:
            where = {keyfield: [int(s) for s in paramvalue.split(',')]}
            d = self.dm.select(tblname, (keyfield, ) + fields, where)
            if self.debug:
                print self.dm.sql
            return d
        return []

    def get_byid(self, paramname, keyfield, tblname, fields):
        """ ����� �� ������ ������� """
        d = self.get_data_byid(self.get_query_param(paramname), keyfield, tblname, fields)
        return self.json(d)

    def get_downers(self, owner=None):
        """ ����� �� ������ ��������� ������� """
        if owner:
            where = [
                {self.dm.OS_MATCH_START + 'downer': self.adapt_fieldvalue(owner)},
                {self.dm.OS_MATCH_START + 'downershort': self.adapt_fieldvalue(owner)},
            ]
        else:
            where = {'hasvalid': True}
        d = self.dm.select('tkslaw.downers', ('id', 'downer', 'downershort'), where)
        return self.json_or_not_found(d)

    def get_status(self, status=None):
        d = [
            {
                'ID': s.status,
                'STATUS': s.description
            } for sid, s in STATUSES.items()
            if status is None or status == sid
        ]
        return self.json_or_not_found(d)

    def get_dtypes(self, typename=None):
        d = self.get_dict_data(typename, 'dtype', 'tkslaw.dtypes', ('ID', 'dtype as TYPENAME'), addcond={'hasvalid': True})
        return self.json_or_not_found(d)

    def append_match_field(self, data, param, fieldname=None, match=False):
        if fieldname is None:
            fieldname = param
        fieldvalue = self.adapt_fieldvalue(self.get_param(param))
        if fieldvalue:
            # ��������� ��������
            # tuple �� 2 ��������� (to_match (����� �� ts_vector), to_like (����� �� trgm))
            if match:
                data[self.dm.OS_ILIKE + fieldname] = fieldvalue
            else:
                data[self.dm.OS_ILIKE + fieldname] = (None, fieldvalue)
        return data

    def get_int_param(self, paramname, default):
        try:
            return int(self.get_param(paramname, default))
        except ValueError:
            return default

    def get_timestamp(self, d):
        t = d.timetuple()
        return datetime(*t[:6])

    def append_and_op(self, data, op, cond):
        if op not in data:
            data[op] = []
        data[op].append(cond)

    def get_last(self, r, cond):
        for param, days in cond.items():
            if self.get_param(param):
                delta = timedelta(days=days)
                r['}receiptdate'] = date.today() - delta
                r['revnumber'] = 0
        return r

    def return_empty_data(self):
        return {
            'documents': [],
            'stat': {
                'time': {
                    'seconds': 0,
                    'microseconds': 0,
                    'text': '0.000200sec'
                },
                'has_more': False,
                'version': self.version
            }
        }

    def get_pagecount(self, qty, perpage):
        """ ����������� ���������� ������� �� ���������� � ���-�� ������� � ������ � ���-�� ������� �� �������� """
        return max((qty + perpage - 1) / perpage, 1)

    def get_pages(self, page, pagecount):
        """ ���������� ������  ������� """
        r = []
        pages = 5
        arrlength = min(pagecount, pages)
        firstpage = min(page + 2, pagecount) - pages + 1
        i = firstpage
        while len(r) < arrlength:
            if i > 0:
                r.append(i)
            i += 1
        return r

    def create_page_info(self, pagename=u'1', pageno=1, active=False, disabled=False):
        cls = u''
        if active:
            cls = u'active'
        if disabled:
            cls = u'disabled'
        return {
            'cls': cls,
            'pagename': pagename,
            'href': self.update_url(request.url, {'page': pageno})
        }

    def update_url(self, url, params):
        """ ��������� �������� ���������� ������ � ������ """
        url_parse = urlparse.urlparse(url)
        query = url_parse.query
        url_dict = dict(urlparse.parse_qsl(query))
        url_dict.update(params)
        url_new_query = urllib.urlencode(url_dict)
        url_parse = url_parse._replace(query=url_new_query)
        return urlparse.urlunparse(url_parse)

    def return_data_result(self, d, pages, perpage, page, offset, limit, out):
        if pages:
            rdata = {'documents': d[:perpage]}
        else:
            rdata = {'documents': d}

        stat = {
            'time': {
                'seconds': self.dm.time_to_process.seconds,
                'microseconds': self.dm.time_to_process.microseconds,
                'text': str(self.dm.time_to_process)
            },
            'has_more': len(d) > perpage,
            'version': self.version
        }

        if self.debug:
            stat['debug'] = self.debug
            stat['sql'] = out['sql'].encode('utf-8'),
            #stat['params'] = self.dm.params
            print 'page', page, offset, limit
            print out['sql']
            print 'total:', len(d)

        qty = 0
        q = self.dm.select_sql('tkslaw.docs', out['count_sql'], out['params'])
        if q:
            qty = q[0].values()[0]
            stat['count'] = qty

        rdata['stat'] = stat

        if pages:
            parr = []
            if qty:
                pagecount = self.get_pagecount(qty, perpage)
                if pagecount > 1:
                    parr.append(self.create_page_info(pagename=u'������', pageno=1, disabled=page==1))
                for p in self.get_pages(page, pagecount):
                    parr.append(self.create_page_info(pagename=unicode(str(p)), pageno=p, active=p==page))
                if pagecount > 1:
                    parr.append(self.create_page_info(pagename=u'���������', pageno=page+1, disabled=page==pagecount))
            rdata['pages'] = parr

        rdata['empty'] = False
        rdata['htmltitle'] = {
            'qty': qty,
            'offset': offset,
            'limit': limit,
            'page': page
        }

        return rdata

    def append_not_empty(self, data, cond):
        if cond:
            data.append(cond)
        return data

    def get_docstonds_params(self):
        doctonds = {}

        # ��������� ������
        # ����� �� ������� tkslaw.doctonds
        # ����� ���������
        dnumber = self.get_param(PARAM_DNUMBER)
        if dnumber:
            strict = self.get_param(PARAM_DNUMBERSTRICT, True)
            if strict in (True, 'true', '1', 1):
                # ������ ����� � upper
                doctonds['+dnumber'] = dnumber
            else:
                doctonds['#dnumber'] = dnumber + '%'

        # ���� ���������
        ddate = self.get_param(PARAM_DDATE)
        if ddate:
            doctonds['ddate'] = date(*[int(s) for s in ddate.split('-')])
        # �������� �����
        ownerid = self.get_param(PARAM_OWNERID)
        if ownerid:
            doctonds['doid'] = [int(s) for s in ownerid.split(',')]
        # ��� ���������
        typeid = self.get_param(PARAM_TYPEID)
        if typeid:
            doctonds['dtid'] = [int(s) for s in typeid.split(',')]
        return doctonds

    def get_search_data(self, include_html=False):
        data = []
        pages = True
        query_params = self.dm.init_params()

        # ��������
        page = self.get_int_param(PARAM_PAGE, 1)
        perpage = self.get_int_param(PARAM_PERPAGE, 10)

        doctonds = self.get_docstonds_params()
        if doctonds:
            data.append({DID_OP: PureSQL({
                DB_PG: self.dm.get_select_clause('tkslaw.doctonds', ('DID', ), doctonds, params=query_params)
            })})

        # ������
        topics = self.get_param(PARAM_TOPICS)
        if topics:
            topics = [int(s) for s in topics.split(',')]
            if self.debug:
                print 'topics', topics
            data.append({DID_OP: PureSQL({
                DB_PG: self.dm.get_select_clause('tkslaw.doctopics', ('DID', ), {'TOPICID': topics}, params=query_params)
            })})

        # ����� ������ �� ������� tkslaw.docs
        last = self.get_last({}, LAST_CONFIG)
        if last:
            data.append(last)
            # ���������� ��� ���������� �� ���������
            # pages = False

        # ToDo:
        # ToDo: 1. �� ������������ ������ ������� ���� ���������� ����� �� docname and doctitle
        # ToDo: 2. ���������� ��� ������� ������ �� doctext (� �������� docname � doctitle ���� ����������)

        docs = []
        # ������������ ���������
        self.append_not_empty(docs, self.append_match_field({}, PARAM_DOCNAME))
        # ��������� ���������
        self.append_not_empty(docs, self.append_match_field({}, PARAM_DOCNAME, 'doctitle'))
        if docs:
            data.append(docs)

        # ����� ���������
        text = self.append_match_field({}, PARAM_DOCTEXT, match=True)
        if text:
            data.append(text)

        if not data:

            return self.return_empty_data()

        else:

            data.append({
                'revislast': True,
            })

            order_by = ('sortdate desc', )
            offset = perpage * (page - 1)
            limit = perpage + 1

            params = {}
            if pages:
                params['start'] = offset
                params['limit'] = limit

            out = {}

            d = self.dm.select(
                'tkslaw.docs',
                self.get_field_names(include_html=include_html),
                params=query_params,
                where=tuple(data),
                order_by=order_by,
                out=out,
                on_calc_record=self.update_document_rec,
                **params
            )

            return self.return_data_result(d, pages, perpage, page, offset, limit, out)

    def search(self):
        return self.json(self.get_search_data())


class DjangoWebLawApp(WebLawApp):
    def afterInit(self, *args, **kwargs):
        super(DjangoWebLawApp, self).afterInit(*args, **kwargs)
        self.configure(self.template_path)

    def configure(self, template_path=''):
        TEMPLATES = [
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': template_path.split(';')
            }
        ]
        settings.configure(TEMPLATES=TEMPLATES)
        django.setup()

    def render_template(self, filepath='', filename='', **data):
        template = loader.get_template(os.path.join(filepath, filename))
        r = template.render(data)
        return str(r.encode('utf-8'))


def main_old(*args, **kwargs):
    app, args = WebLawApp.init_weblaw_app(*args, **kwargs)
    return app.run(host='0.0.0.0', port=int(args.altport or args.port))


def main(*args, **kwargs):
    app, args = DjangoWebLawApp.init_weblaw_app(*args, **kwargs)
    if args.test:
        qty = 56
        perpage = 10
        page = 5
        pagecount = app.get_pagecount(qty, perpage)
        print 'get_pagecount', pagecount
        print 'get_pages', app.get_pages(page, pagecount)
    else:
        return app.run(host='0.0.0.0', port=int(args.altport or args.port))


if __name__ == "__main__":
    main(template_mode=True)
    # main_old(document_template="document_tks.thtml")
