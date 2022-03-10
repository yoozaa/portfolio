# -*- coding: cp1251 -*-

"""

    Базовый класс для построения сервисов на базе технологии tks

"""

import warnings
warnings.filterwarnings("ignore")

import sys
import os
from OpenSSL import crypto
import base64
from bottle import Bottle, static_file, request, response, hook, HTTPError, template
from tks.jsontools import jsondumps
import common
import io


def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        if request.method != 'OPTIONS':
            # actual request; reply with the actual response
            return fn(*args, **kwargs)

    return _enable_cors


class BaseWebApp(Bottle):
    """ Базовое приложение """
    def __init__(self,
                 debug=False,
                 dm=None,
                 htdocs='..\\..\\htdocs',
                 index='index.html',
                 version=1,
                 *args, **kwargs):
        super(BaseWebApp, self).__init__()
        self.beforeInit(*args, **kwargs)
        # Режим, при котором работает template_path + .html - шаблоны
        self.template_mode=False
        # Если указан каталог шаблонов, то шаблоны берутся из него
        self.template_path = ''
        # Расширения файлов, которые считаются шаблонами
        self.template_ext = ['.thtml', ]
        self.debug = debug
        self.version=version
        self.init_route()
        self.after_init_route()
        self.localpath = htdocs
        if not self.localpath:
            self.localpath = os.path.abspath(os.path.split(__file__)[0])
            if not self.localpath:
                self.localpath = os.path.abspath(os.getcwd())
        self.dm = dm
        self.index_filename = index
        if self.debug:
            print 'dm', self.dm
        self.store = None
        self.init_store()
        self.setkwargs(**kwargs)
        self.afterInit(*args, **kwargs)

    def beforeInit(self, *args, **kwargs):
        pass

    def setkwargs(self, **kwargs):
        map(lambda key: setattr(self, key, kwargs[key]), kwargs.keys())

    def afterInit(self, *args, **kwargs):
        # Если включен режим шаблонов, то добавляем туда .html файлы
        if self.template_mode:
            self.template_ext.append('.html')

    def init_route(self):
        # отдаем статику
        self.route('/', method='GET', callback=self.index)
        self.route('/<:re:.*>', method='OPTIONS', callback=self.options)
        self.route('/favicon.ico', method='GET', callback=self.favicon)

    def after_init_route(self):
        self.route('/<filepath:path>/<filename>', method='GET', callback=self.static)
        self.route('/<filename>', method='GET', callback=self.static)

    def init_store(self):
        self.store = crypto.X509Store()
        with open(os.path.join(os.path.abspath(os.path.split(__file__)[0]), 'rootca_calcservice.crt'), 'r') as cert_file:
            cert = cert_file.read()
        rootcert = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
        self.store.add_cert(rootcert)

    @enable_cors
    def options(self):
        pass

    def get_template_context(self, init=None):
        r = {
            'revision': getattr(self, 'rev', '0'),
        }
        r.update(getattr(self, 'vars', {}))
        if init:
            r.update(init)
        return r

    def render_template(self, filepath='', filename='', **data):
        return template(self.get_template(filepath, filename), **data)

    def index(self):
        filepath, filename = os.path.split(self.index_filename)
        return self.static(filepath=filepath, filename=filename)

    def favicon(self):
        return self.static('', 'favicon.ico')

    def get_root(self, filepath=''):
        return os.path.join(self.localpath, filepath)

    def get_static_context(self):
        return self.get_template_context()

    def dostatic(self, filepath='', filename='', *args, **kwargs):
        # Определяем, что файл - это шаблон и его надо обработать
        fname, fext = os.path.splitext(filename)
        is_template = fext in self.template_ext
        if is_template:
            data = self.get_static_context()
            return self.html_template(filepath, filename, **data)
        return static_file(filename, root=self.get_root(filepath), *args, **kwargs)

    def static(self, filepath='', filename='', *args, **kwargs):
        # Раздаем js файлы только
        # - вида script.min.js
        # - вида license_что_то_там.js
        # - из каталога js
        # это сделано для того, чтобы не раздавать исходники скриптов
        fname, fext = os.path.splitext(filename)
        is_js = fext.lower() == '.js'
        if is_js:
            fname, fext2 = os.path.splitext(fname)
            if fext2.lower() != '.min' and not fname.startswith('license'):
                if filepath != 'js':
                    return HTTPError(404, "Not found.")
        return self.dostatic(filepath=filepath, filename=filename, *args, **kwargs)

    def get_template(self, filepath='', filename=''):
        root = ''
        if self.template_mode:
            root = os.path.join(self.template_path, filepath)
        else:
            root = self.get_root(filepath)
        filename = os.path.join(root, filename)
        with io.open(filename, 'r', encoding='utf-8') as f:
            return f.read()

    def verify(self, cert):
        store_ctx = crypto.X509StoreContext(self.store, cert)
        result = store_ctx.verify_certificate()
        if result is None:
            return True
        else:
            return False

    def verify_client_certificate(self, certificate):

        if self.debug:
            for key, value in request.headers.items():
                print key, value

        if not certificate:
            return False

        try:
            origin = request.headers['ORIGIN']
        except KeyError:
            return False

        cert = crypto.load_certificate(crypto.FILETYPE_ASN1, base64.b64decode(certificate))
        subj = cert.get_subject()
        subj_origin = subj.organizationalUnitName
        if self.debug:
            print 'O =', subj.organizationName
            print 'OU =', subj_origin
            print 'ORIGIN =', origin

        if not subj_origin or origin not in subj.organizationalUnitName.split(';'):
            return False

        r = self.verify(cert)
        if r:
            response.headers['Access-Control-Allow-Origin'] = origin
        return r

    def json(self, data, encoding='utf-8'):
        response.content_type = 'application/json'
        return jsondumps(data, encoding=encoding)

    def html(self, html):
        response.content_type = 'text/html'
        return html

    def html_template(self, filepath='', filename='', **context):
        return self.html(self.render_template(filepath=filepath, filename=filename, **context))

    def httperror(self, code, status):
        return HTTPError(code, status)

    def not_found(self, status='Not found.'):
        return self.httperror(404, status)

    def json_or_not_found(self, data, status='Not found.'):
        if not data:
            return self.not_found(status)
        return self.json(data)

    def get_param(self, param, default=None):
        return request.params.get(param, default)

    def get_query_param(self, param):
        return request.query.get(param)

    @classmethod
    def init_weblaw_app(cls, *a, **kwargs):
        args = common.parse_args()
        common.parse_args_from_config(args, args.config)
        if args.debug:
            print 'params:', '='*20
            arg_strings = []
            for arg in args._get_args():
                arg_strings.append(repr(arg))
            for name, value in args._get_kwargs():
                arg_strings.append('%s=%r' % (name, value))
            for line in arg_strings:
                print line
            print 'params:', '='*20
            print

        dm = common.init_data(args.config)

        return cls(
            debug=args.debug,
            dm=dm,
            htdocs=os.path.abspath(args.root),
            index=args.index,
            version=int(args.dbver),
            vars=args.vars,
            rev=args.rev,
            template_path=os.path.abspath(args.tpath),
            *a, **kwargs
        ), args
