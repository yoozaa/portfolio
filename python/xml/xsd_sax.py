# -*- coding: cp1251 -*-
from xml.sax import make_parser, handler
from xmlnames import *
from maputils import *
from fileman import get_file_object
import os.path as ospath
from xml.sax.xmlreader import InputSource
from cStringIO import StringIO
from tks.strutils import uformat

#THandlerState
hs_None = 0
hs_Doc = 1
hs_Restriction = 2
hs_Enumeration = 3
hs_Enumeration_value = 4

def process_xsd(filename):
    return XSD(filename)


def parse_file(hndl, filename, parseString = False, stringEncoding = 'UTF-8', bytestream = False, *args, **kwargs) :
    parser = make_parser()
    parser.setContentHandler(hndl)
    txt = ''
    inpsrc = ''
    if not (parseString or bytestream):
        inpsrc = filename
        if not ospath.exists(inpsrc):
            raise IOError(2, 'Файл не существует', inpsrc)

    if (parseString or bytestream) or bool(txt):
        if not txt:
            txt = filename
        inpsrc = InputSource()
        if bytestream:
            inpsrc.setByteStream(txt)
        elif isinstance(txt, unicode):
            inpsrc.setByteStream(StringIO(txt.encode(stringEncoding)))
        else:
            inpsrc.setByteStream(StringIO(str(txt)))
    parser.parse(inpsrc)

class choice_name_producer(object):
    """ Класс для генерирования уникальных имен для choice """
    def __init__ (self):
        self.names = {}

    def get_name(self, key):
        if key not in self.names:
            self.names[key] = 0
            return key
        self.names[key] += 1
        return '%s_%d' % (key, self.names[key])


class XSDElement(object):
    def __init__ (self, name, parentElement, attrs, is_element = False):
        self.elements = []
        self.name = name
        self.annotation = ""
        self.parent = parentElement
        self.sequence = False
        self.complexType = False
        self.isattr = False
        self.is_typedef = False
        self.attrs = {}
        self.appendattrs(attrs)
        self.restriction = {}
        self.enumeration = {}
        self.extension = ''
        self.any = False
        self.data = None
        self.root = None
        self.is_element = is_element
        self.force_optional = False
        self.choice_name = ''
        self.locationPrefix = ''
        if self.parent != None:
            self.parent.appendElement(self)
        self.basetypecache = {}  # кэш для метода getbasetype

    def appendElement(self, element):
        self.elements.append(element)

    def istype(self):
        return self.attrs.has_key('type') or self.attrs.has_key('ref')

    def iscomplex(self):
        """ указывает на сложные элементы (т.е. те, у которых могут быть подэлементы)"""
        return not self.is_element and not self.is_attr

    def optional(self):
        if self.force_optional:
            return True
        elif ('minOccurs' in self.attrs):
            return self.attrs['minOccurs'] == "0"
        else:
            return False

    def cycle(self):
        return ('maxOccurs' in self.attrs) and not (self.attrs['maxOccurs'].isdigit() and (int(self.attrs['maxOccurs']) == 1))

    def get_maxOccurs(self):
        if 'maxOccurs' in self.attrs:
            if self.attrs['maxOccurs'].isdigit():
                return int(self.attrs['maxOccurs'])
            else:
                return None  # unbounded
        return 1

    def typename(self):
        r = ''
        if self.istype():  # TODO: убрать istype
            if self.attrs.has_key('type'): r = self.attrs['type']
            else: r = self.attrs['ref']
        return r

    def isextension(self):
        return self.extension != ''

    def appendattrs(self, a):
        for key in a.keys():
            self.attrs[key] = a[key]

    def getoutname(self, prefix):
        if (self.name.find(':') != -1) or (prefix == ""):
            return self.name
        else:
            return "%s:%s" % (prefix, self.name)

    def getbasetype(self, xtype=''):
        res = self.basetypecache.get(xtype, None)
        if res is None:
            r = {}
            if ('base' in self.restriction):
                elem = self.root.getbytype(self.restriction['base'])
                if elem != None:
                    r = elem.getbasetype(xtype)
                else:
                    r['origin'] = self.restriction['base']
                    r['basetype'] = self.restriction['base']
            elif self.istype():
                elem = self.root.getbytype(self.typename())
                if elem != None:
                    r = elem.getbasetype(xtype)

            if xtype:
                r['basetype'] = xtype

            if self.is_positive():
                r['positive'] = r['basetype']

            r.update(self.restriction)
            self.basetypecache[xtype] = r
            res = r
        return dict(res)

    def dump_atts(self):
        return '\n'.join(["%s=%s"%(aname, self.attrs[aname]) for aname in self.attrs])

    def get_enumeration_text(self):
        return '\n'.join(self.enumeration.values())

    def get_enumeration_key(self, value):
        return dict([(v, k) for (k, v) in self.enumeration.items()]).get(value, '')

    def get_enumeration_value(self, key):
        return self.enumeration.get(key, '')

    def is_positive(self):
        """ д.б. положительное число? """
        return self.restriction.get('minInclusive') == "0"


class XSDType(XSDElement):
    def __init__ (self, name, parentElement, attrs):
        super(XSDType, self).__init__(name, parentElement, attrs)

class XSDRoot(XSDElement):
    def __init__ (self, name, parentElement, attrs, path, *args, **kwargs):
        map(lambda key: setattr(self, key, kwargs[key]), kwargs.keys())
        self.path = path
        self.root = self
        self.ns = {}
        self.imports = {}
        self.import_xsd = {}
        self.targetPrefix = ''
        self.targetNamespace = ''
        self.has_root_element = False
        super(XSDRoot, self).__init__(name, parentElement, attrs)

    def appendElement(self, element):
        """
        Необходима отдельная процедура добавления элементов для корневого элемента схему
        В схемах иногда указывают несколько корневых элементов (xmldsig) нам нужен только один -
        первый. остальные удаляются в mapping.domap
        """
        element.is_typedef = len(self.elements) > 0
        self.elements.append(element)
        if element.is_element:
            self.has_root_element = True

    def istype(self):
        return False

    def isextension(self):
        return False

    def processNamespaces(self):
        if (self.attrs.has_key('targetNamespace')):
            self.targetNamespace = self.attrs['targetNamespace']
        ns_keys = [s for s in self.attrs.keys() if s.startswith('xmlns:')]
        for key in ns_keys:
            self.ns[key[6:]] = self.attrs[key]
            if (self.attrs[key] == self.targetNamespace) and not self.targetPrefix:
                self.targetPrefix = key[6:]
        self.processimports()

    def processimports(self):
        for imp in self.imports.keys():
            self.importNamespace(imp)

    def importNamespace(self, namespace):
        xsd = self.get_xsd(namespace)
        self.import_xsd[namespace] = xsd.rootnode
        self.ns.update(xsd.rootnode.ns)

    def get_xsd(self, namespace):
        filename = self.path + self.imports[namespace]
        return get_file_object(filename, XSD)

    def getbytype(self, tname):
        r = None
        try:
            p, lname = splitqname(tname)
            if (lname):
                xsd = None
                if (str(p) == str(self.targetPrefix)) or (p == ""):
                    xsd = self
                    r = xsd.getbytypename(lname)
                else:
                    xsd = self.getbyprefix(p)
                    if (xsd != None):
                        r = xsd.getbytype(tname)
        except Exception, e:
            dump('%s' % (e))
        return r

    def getbyprefix(self, prefix):
        r = None
        if (prefix != ''):
            namespace = self.ns[prefix]
            if (namespace) and (namespace in self.import_xsd):
                r = self.import_xsd[namespace]
        return r

    def getbytypename(self, tname):
        r = None
        for elem in self.elements:
            if (elem.name == tname) and not elem.istype():
                r = elem
                break
        return r


class XSD (handler.ContentHandler):

    def __init__(self, filename, parseString = False, stringEncoding = 'UTF-8', bytestream = False, *args, **kwargs):

        self.choice_names = choice_name_producer()
        path = filename[:filename.rfind("\\")]
        if path:
            path = path + "\\"
        self.filename = filename
        self.curnode = self.get_xsd_root_class()("XSD", None, {}, path, *args, **kwargs)
        self.rootnode = self.curnode
        self.state = [hs_None]
        self.current_choice = ''
        self.current_enum_key = ''
        self.choices = ['']
        self.tree_arr = []
        parse_file(self, filename, parseString, stringEncoding, bytestream, *args, **kwargs)
        self.rootnode.processNamespaces()

    def get_xsd_root_class(self):
        return XSDRoot

    def startElement(self, name, attrs):
        ln = localname(name)
        element = None
        if (ln in ['element', 'attribute', 'simpleType']):
            if attrs.has_key('name'): a = 'name'
            elif attrs.has_key('ref'): a = 'ref'
            else: a = ''
            if a:
                self.curnode = XSDElement(attrs[a], self.curnode, attrs, ln == 'element')
                self.curnode.root = self.rootnode
                self.curnode.isattr = (ln == 'attribute')
                if ln == 'element':
                    self.curnode.choice_name = self.current_choice
                element = self.curnode
        elif (ln == 'schema'):
            self.curnode.appendattrs(attrs)
        elif (ln == 'import'):
            if attrs.has_key('namespace') and \
                attrs.has_key('schemaLocation'):
                location = attrs['schemaLocation']
                (head, tail) = ospath.split(location)
                if head:
                    self.curnode.locationPrefix = head+'/'
                    self.curnode.imports[unicode(attrs['namespace'])] = unicode(location)
                else:
                    self.curnode.locationPrefix = self.curnode.parent and self.curnode.parent.locationPrefix or ''
                    self.curnode.imports[unicode(attrs['namespace'])] = unicode(self.curnode.locationPrefix+location)
        elif ln == "documentation":
            if hs_Enumeration in self.state:
                self.state.append(hs_Enumeration_value)
            elif self.curnode and self.curnode.annotation == "":
                self.state.append(hs_Doc)
        elif ln == "choice":
            self.choices.append(self.current_choice)
            self.current_choice = self.choice_names.get_name(self.curnode.name)
            if 'minOccurs' in attrs and attrs['minOccurs'] == '0':
                self.current_choice = self.current_choice + '!'
        elif ln == "sequence":
            self.curnode.sequence = True
        elif ln == "complexType":
            if attrs.has_key('name'):
                self.curnode = XSDType(attrs['name'], self.rootnode, attrs)
                self.curnode.root = self.rootnode
                element = self.curnode
            self.curnode.complexType = True
        elif ln == 'extension':
            self.curnode.extension = attrs['base']
        elif ln == "restriction":
            self.state.append(hs_Restriction)
            self.curnode.restriction['base'] = attrs['base']
        elif ln == "enumeration":
            self.state.append(hs_Enumeration)
            if attrs.has_key('value'):
                self.current_enum_key = attrs['value']
                # лишний элемент для возможности не указывать значение элемента
                if not self.curnode.enumeration:
                    self.curnode.enumeration[''] = ''
                self.curnode.enumeration[self.current_enum_key] = ''
        elif hs_Restriction in self.state:
            if attrs.has_key('value'):
                self.curnode.restriction[ln] = attrs['value']
        elif ln == 'any':
            self.curnode.any = True

        self.tree_arr.append(element)

    def state_off(self, s):
        if self.state:
            current_state = self.state.pop()
            while current_state != s and self.state:
                current_state = self.state.pop()

    def endElement(self, name):
        ln = localname(name)
        if ln == 'documentation':
            self.state_off(hs_Doc)
        elif ln == 'restriction':
            self.state_off(hs_Restriction)
        elif ln == 'enumeration':
            if not self.curnode.enumeration[self.current_enum_key]:
                self.curnode.enumeration[self.current_enum_key] = self.current_enum_key
            self.current_enum_key = ''
            self.state_off(hs_Enumeration)
        elif ln == 'choice':
            self.current_choice = self.choices.pop()
        element = self.tree_arr.pop()
        if element:
            self.curnode = element.parent

    def characters(self, content):
        if self.curnode != None:
            if hs_Enumeration_value in self.state:
                self.curnode.enumeration[self.current_enum_key] += content
            elif hs_Doc in self.state:
                self.curnode.annotation += content
