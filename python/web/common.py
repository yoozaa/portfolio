# -*- coding: cp1251 -*-

import ConfigParser
import os


def show_error(msg, sql='', *args, **kwargs):
    if sql:
        print sql
    print msg


def init_data(config_filename='config.ini', section_name='global', *args, **kwargs):
    from gtd.db.data import get_data, db_dict_config
    dm = None
    if os.path.exists(config_filename):
        ini = ConfigParser.ConfigParser()
        ini.optionxform = str
        ini.read(config_filename)

        if ini.has_section(section_name):
            d = dict(ini.items(section_name))
            dm = get_data(db_dict_config(d), on_error=show_error, *args, **kwargs)
    else:
        print "init_data. no config file %s" % config_filename
    return dm


def parse_args_from_config(args, config_filename='config.ini', section_name='config', *args2, **kwargs):
    """
        Дополнительно с параметрами коммандной строки анализируем содержимое файла настроек
    """
    if os.path.exists(config_filename):
        ini = ConfigParser.ConfigParser()
        ini.optionxform = str
        ini.read(config_filename)

        if ini.has_section(section_name):
            d = dict(ini.items(section_name))
            for paramname in d:
                setattr(args, paramname, d[paramname])
    else:
        print "parse_args_from_config. no config file %s" % config_filename
    return args


def parse_args():
    import argparse
    import json
    from svn import svn_manager
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', help=u'port number', default='80')
    parser.add_argument('--altport', '-a', help=u'alternative port number', default='')
    parser.add_argument('--config', '-c', help=u'config file name', default='config.ini')
    parser.add_argument('--root', '-f', help=u'htdocs root folder', default='.\\htdocs')
    parser.add_argument('--debug', '-b', help=u'debug mode', action='store_true', default=False)
    parser.add_argument('--index', '-i', help=u'index file name', default='html/index.html')
    parser.add_argument('--tablename', '-n', help=u'test table name', default='valname')
    parser.add_argument('--sql', '-q', help=u'test sql script', default='')
    parser.add_argument('--dbver', '-v', help=u'database version number', default='1')
    parser.add_argument('--vars', '-m', help=u'template variables', default='{}', type=json.loads)
    parser.add_argument('--rev', '-r', help=u'revision number', default=svn_manager().revision())
    parser.add_argument('--tpath', '-t', help=u'template directories', default='../templates')
    parser.add_argument('--test', '-s', help=u'test mode', action='store_true', default=False)
    args, unknown = parser.parse_known_args()
    return args

