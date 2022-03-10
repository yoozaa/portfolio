# -*- coding: cp1251 -*-

from xml.sax import handler, SAXException
from node import xmlnode, xmlrootnode
from fileman import get_file_object
from gtd.xmlmap.xsd_sax import parse_file

def get_xmltree(filename, forcenew = False):
    return get_file_object(filename, xmltree, forcenew)


class StopParsing(SAXException):
    pass


class xmltree (handler.ContentHandler) :

    def __init__ (self, filename, parseString = False, stringEncoding = 'UTF-8', bytestream = False, *args, **kwargs) :
        self.data = None
        self.curnode = xmlrootnode("xml", None)
        self.rootnode = self.curnode
        parse_file(self, filename, parseString, stringEncoding, bytestream, *args, **kwargs)
        del self.curnode

    def startElement(self, name, attrs):
        self.data = []
        self.curnode = xmlnode(name, self.curnode)
        self.curnode.appendatts(attrs)

    def endElement(self, name):
        if not self.curnode.items and self.data:
            self.curnode.set_value(u''.join(self.data))
        self.curnode = self.curnode.parent
        self.data = None

    def characters(self, content):
        if self.data is not None:
            self.data.append(content)


