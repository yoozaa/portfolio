# -*- coding: cp1251 -*-

"""

    Проверка документа по схеме
    !!! текст ошибки - unicode

"""


import restrict
import re
from gtd import system, in_program

from maputils import is_date, is_datetime, is_time, is_gYearMonth, is_gYear
from xmltree_sax import xmltree
from nodetypes import MAX_MEMOSTR

SCHEMA_ERROR, CUSTOM_ERROR = range(2)

class choice_verifier(object):
    """ Проверяем choice """
    def __init__(self, verify_obj):
        self.verify_obj = verify_obj
        self.choices = {}
        self.choice_nodes = {}
        self.choice_node = None

    def init_node(self, node):
        if not self.verify_obj.choice_verify:
            return
        cn = node.get_choice_name()
        if cn:
            node.choice_name = cn
        if node.choice_name:
            if node.choice_name not in self.choices:
                self.choices[cn] = None
                self.choice_nodes[cn] = [node]
            else:
                self.choice_nodes[cn] += [node]

    def verify(self, node):
        if not self.verify_obj.choice_verify:
            return
        if node.choice_name in self.choices:
            if self.choices[node.choice_name] is None:
                self.choices[node.choice_name] = [node, False]
            else:
                # один из возможных узлов choice уже встретился, однако бывают узлы с числом вхождений > 1
                if node.name != self.choices[node.choice_name][0].name:
                    # это не повторяющийся узел, а другой узел из choice - ошибка
                    self.choices[node.choice_name][1] = True
            if self.choices[node.choice_name][1] \
                   and not self.choice_node:
                self.choice_node = self.choices[node.choice_name][0]

    def ignore_node(self, node):
        if not self.verify_obj.choice_verify:
            return
        return

    def verify_end(self, node):
        if not self.verify_obj.choice_verify:
            return
        if self.choice_node and self.choice_node.choice_name == node.choice_name:
            self.choice_node = None

    def check_for_empty(self):
        """ Проверяет на наличие вообще незаполненных choice """
        if not self.verify_obj.choice_verify:
            return
        for cn in self.choices.keys():
            if not cn.endswith('!') and self.choices[cn] is None:
                for node in self.choice_nodes[cn]:
                    self.mark_as_required(node)

    def mark_as_required(self, node):
        """ Добавляет ошибки в список с напоминанием о возможном заполнении """
        if node.items:
            for n in node.items:
                self.mark_as_required(n)
        else:
            self.verify_obj.errors.append((node, u'Возможно поле должно быть заполнено', SCHEMA_ERROR))


class verifier(object):

    """ Проверка документа XML по схеме """

    def __init__(self, node, custom_ignore_node = None, custom_verify_proc = None, *args, **kwargs):
        self.node = node
        self.errors = None
        self.old_errors = None
        self.custom_ignore_node = custom_ignore_node
        self.custom_verify_proc = custom_verify_proc
        # Пользовательская функция, вызывается у обязательных элементов, позволяет их игнорировать
        self.custom_optional = None
        self.c_v = choice_verifier(self)
        self.choice_verify = True
        self.verbose_mode = False
        map(lambda k: setattr(self, k, kwargs[k]), kwargs.keys())

    def info(self, *args):
        if self.verbose_mode:
            print ' '.join([str(a) for a in args])

    def get_error_list(self, err_list = None):
        """
           собственно проверка дерева элементов
           err_list - старый список ошибок - используется, когда проверяется
           только часть дерева
        """
        self.errors = []
        if err_list is not None:
            err_list.remove_node_and_children(self.node)
        self.old_errors = err_list and err_list.errors or []
        count_info = {}
        self.node.traverse3(self.process_node, self.ignore_node, self.process_node_end, count_info)
        self.c_v.check_for_empty()
        self.old_errors.extend(self.errors)
        desc = ''
        if self.node.xsd_element and self.node.xsd_element.parent:
            desc = self.node.xsd_element.parent.annotation
        return error_list(self.old_errors, desc)

    def get_error_list_fast(self, err_list=None):
        """
           собственно проверка дерева элементов
           err_list - старый список ошибок - используется, когда проверяется
           только часть дерева
        """
        self.errors = []
        if err_list is not None:
            err_list.remove_node_and_children(self.node)
        self.old_errors = err_list and err_list.errors or []
        count_info = {}
        self.node.traverse3(self.process_node_fast, self.ignore_node, self.process_node_end, count_info)
        self.c_v.check_for_empty()
        self.old_errors.extend(self.errors)
        desc = ''
        if self.node.xsd_element and self.node.xsd_element.parent:
            desc = self.node.xsd_element.parent.annotation
        return error_list(self.old_errors, desc)

    def process_node(self, node, count_info=None):
        node.verified = True
        el_index = 1
        if self.old_errors is not None and node.parent:
            el_index = node.parent.nodepos(node) + 1
        elif count_info is not None:
            ln = node.getlocalname()
            count_info[ln] = count_info.get(ln, 0) + 1
            el_index = count_info[ln]
        custom_required = not self.can_custom_ignore_node(node)
        self.c_v.init_node(node)
        if not self.can_ignore_node(node, custom_required):
            self.c_v.verify(node)
            node.ignored = False
            error = node_verifier(node, el_index).verify(self.custom_verify_proc,
                                               custom_required,
                                               self.c_v.choice_node)
            if error:
                self.errors.append(error)
        else:
            node.ignored = True
            self.c_v.ignore_node(node)
            return False
        return True

    def process_node_fast(self, node, count_info=None):
        node.verified = True
        custom_required = not self.can_custom_ignore_node(node)
        self.c_v.init_node(node)
        if not self.can_ignore_node(node, custom_required):
            self.c_v.verify(node)
            node.ignored = False
            error = node_verifier(node).verify(custom_verify_proc=self.custom_verify_proc,
                                               custom_required=custom_required,
                                               empty_of_node=self.c_v.choice_node,
                                               element_index_proc=self.get_node_index,
                                               count_info=count_info)
            if error:
                self.errors.append(error)
        else:
            node.ignored = True
            self.c_v.ignore_node(node)
            return False
        return True

    def process_node_end(self, node, count_info=None):
        self.c_v.verify_end(node)

    def ignore_node(self, node, params=None):
        node.ignored = True
        return True

    def get_node_index(self, node, count_info=None):
        """
        callback метод для получения индекса узла при проверке maxOccurs
        """
        el_index = 1
        if self.old_errors is not None and node.parent:
            el_index = node.parent.nodepos(node) + 1
        elif count_info is not None:
            ln = node.lname
            count_info[ln] = count_info.get(ln, 0) + 1
            el_index = count_info[ln]
        return el_index

    def can_custom_ignore_node(self, node):
        if not self.custom_ignore_node:
            return True
        else:
            return self.custom_ignore_node(node)

    def custom_node_is_optional(self, node):
        if not self.custom_optional:
            return False
        else:
            return self.custom_optional(node)

    def node_is_optional(self, node):
        return node.xsd_element.optional() or self.custom_node_is_optional(node)

    def can_ignore_node(self, node, custom_required=False):
        return node.xsd_element is None \
               or (not custom_required
                   and (self.node_is_optional(node) or node.has_choice_name())
                   and node.empty_total(self.can_custom_ignore_node))


class node_verifier(object):

    """ Класс для проверки элемента XML по схеме """

    def __init__(self, node, element_index=1):
        self.node = node
        # ToDo: Возможно, после переделки xmlnode использовать информацию из него
        self.element_index = element_index
        self.type_dict = None
        self.maxOccurs = None

    def verify(self, custom_verify_proc=None, custom_required=False, empty_of_node=None,
               element_index_proc=None, count_info=None):
        if empty_of_node and self.node.value:
            return self.return_error_record(u'Элемент должен быть пустой (заполнен %s)' % (empty_of_node.xsd_element.annotation))
        if custom_verify_proc:
            error_message = custom_verify_proc(self.node, custom_required)
            if error_message:
                return self.return_error_record(error_message, CUSTOM_ERROR)
        if self.node.xsd_element:
            self.type_dict = self.node.xsd_element.getbasetype()
            self.maxOccurs = self.node.xsd_element.get_maxOccurs()
            if self.maxOccurs is not None:
                if element_index_proc is not None:
                    self.element_index = element_index_proc(self.node, count_info)
                if self.maxOccurs < self.element_index:
                    return self.return_error_record(u'Нарушено ограничение количества элементов. Заполнено элементов: %d. Должно быть: %d' % (self.element_index, self.maxOccurs))
        elif self.node.base_type:
            self.type_dict = self.node.base_type
        if self.type_dict:
            t = restrict.get_basetype(self.type_dict)
            if t:
                att = getattr(self, 'verify_%s' % (t), None)
                if att and callable(att):
                    return att()
        return None

    def is_memo(self):
        """ повторяющиеся элементы типа string (не token) """
        return self.node.xsd_element \
               and self.node.xsd_element.cycle() \
               and not self.node.xsd_element.iscomplex() \
               and restrict.get_basetype(self.node.base_type) == 'string'

    def return_error_record(self, error_message, error_type = SCHEMA_ERROR):
        return (self.node, error_message, error_type)

    def compose_restrict_error(self, restriction, restriction_value, message = u''):
        return u'Нарушено ограничение (%s = %s). %s' % (restriction, restriction_value, message)

    def count_memo_nodes(self, memo_value, maxlength):
        # считает количество элементов, получающихся при разбиении мемо-поля
        # методом XMLEditor.set_node_value_splitmemo (xmledit.py), без самого разбиения.
        line_sep = '\r\n'
        white_chars = ' \t\v\f'
        start = 0
        node_count = 0
        if memo_value:
            while True:
                crlf_pos = memo_value.find(line_sep, start)
                finish = (len(memo_value) if crlf_pos == -1 else crlf_pos) - 1
                while start <= finish:
                    if memo_value[start] not in white_chars:
                        break
                    start += 1
                while finish >= start:
                    if memo_value[finish] not in white_chars:
                        break
                    finish -= 1
                # -(-a // b) = ceil(a,b)
                node_count -= ((start - finish - 1) // maxlength) if finish >= start else 0
                if crlf_pos == -1:
                    break
                start = crlf_pos + len(line_sep)
        return node_count


    def verify_string(self):
        value_to_verify = self.node.getviewvalue()
        if 'minLength' in self.type_dict:
            if len(value_to_verify) < int(self.type_dict['minLength']):
                return self.return_error_record(self.compose_restrict_error(u'Минимальное количество символов', self.type_dict['minLength']))
        l = self.type_dict.get('length', 0)
        if 'length' in self.type_dict:
            if (l and not value_to_verify) or (len(value_to_verify) != int(l)):
                return self.return_error_record('%s' % (self.compose_restrict_error(u'Количество символов', self.type_dict['length'])))
        l = self.type_dict.get('maxLength', 0)
        if self.is_memo() and self.maxOccurs:
            node_count = self.count_memo_nodes(value_to_verify, int(l) or MAX_MEMOSTR)
            if self.maxOccurs < node_count:
                return self.return_error_record(u'Нарушено ограничение количества элементов. Заполнено элементов: %d. Должно быть: %d' % (node_count, self.maxOccurs))
        # not self.is_memo - не проверяем мемо поля на длину поля
        if value_to_verify and l and len(value_to_verify) > int(l) and not self.is_memo():
            return self.return_error_record(self.compose_restrict_error(u'Максимальное количество символов', self.type_dict['maxLength'],
                                                                        u'Реальное количество символов = %s' % (len(value_to_verify),)))
        if 'pattern' in self.type_dict:
            if not re.match(r'^(%s)$' % (self.type_dict['pattern']), value_to_verify, re.UNICODE):
                return self.return_error_record(u'Значение не соответствует шаблону %s' % (self.type_dict['pattern']))
        if self.node.xsd_element.enumeration and (not value_to_verify or (value_to_verify not in self.node.xsd_element.enumeration)):
            return self.return_error_record(u'Значение элемента не входит в список возможных')
        return None

    def verify_token(self):
        r = self.verify_string()
        if not r:
            value_to_verify = self.node.getviewvalue()
            if re.search('\t', value_to_verify):
                return self.return_error_record(u'Значение не должно содержать символов табуляции')
            if re.findall('\r|\n', value_to_verify):
                return self.return_error_record(u'Значение не должно содержать символов конца строки')
            if re.search('(^\s)', value_to_verify):
                return self.return_error_record(u'Значение не должно пробелов в начале')
            if re.search('(\s$)', value_to_verify):
                return self.return_error_record(u'Значение не должно пробелов в конце')
            if re.search('(\s{2})', value_to_verify):
                return self.return_error_record(u'Значение может содержать только одиночные пробелы')
            return None
        else:
            return r

    def verify_integer(self):
        r = self.verify_decimal()
        if not r:
            value_to_verify = self.node.getviewvalue()
            if not re.match(r'^\-?(\d)+$', value_to_verify):
                return self.return_error_record(u'Значение должно быть целым числом')
            if 'minInclusive' in self.type_dict and (int(value_to_verify) < int(self.type_dict['minInclusive'])):
                return self.return_error_record(u'Значение должно быть не меньше %s' % self.type_dict['minInclusive'])
            return None
        else:
            return r

    def verify_date(self):
        value_to_verify = self.node.getviewvalue()
        if not is_date(value_to_verify):
            return self.return_error_record(u'Значение должно быть датой')
        return None

    def verify_dateTime(self):
        value_to_verify = self.node.getviewvalue()
        if not is_datetime(value_to_verify):
            return self.return_error_record(u'Значение должно содержать дату и время')
        return None

    def verify_gYearMonth (self):
        value_to_verify = self.node.getviewvalue()
        if not is_gYearMonth(value_to_verify):
            return self.return_error_record(u'Значение не соответствует типу ГГГГ-ММ')
        return None

    def verify_gYear(self):
        value_to_verify = self.node.getviewvalue()
        if not is_gYear(value_to_verify):
            return self.return_error_record(u'Значение не соответствует типу ГГГГ')
        return None

    def verify_time(self):
        value_to_verify = self.node.getviewvalue()
        if not is_time(value_to_verify):
            return self.return_error_record(u'Значение должно содержать время')
        return None

    def verify_decimal(self):
        value_to_verify = self.node.getviewvalue()
        if not re.match(r'^\-?(\d|\.)+$', value_to_verify):
            return self.return_error_record(u'Значение должно быть числом')
        totalDigits = int(self.type_dict.get('totalDigits', 0))
        if value_to_verify:
            if totalDigits:
                a = value_to_verify.split('.')
                Digits = len(str(abs(int(a[0])))) + (len(a) > 1 and len(a[1]))
                if Digits > totalDigits:
                    return self.return_error_record(u'Превышено допустимое количество значащих цифр: %d (указано %d)' % (totalDigits, Digits))
            if 'minInclusive' in self.type_dict and (float(value_to_verify) < float(self.type_dict['minInclusive'])):
                return self.return_error_record(u'Значение должно быть не меньше %s' % self.type_dict['minInclusive'])
            if 'maxInclusive' in self.type_dict and (float(value_to_verify) > float(self.type_dict['maxInclusive'])):
                return self.return_error_record(u'Значение должно быть не больше %s' % self.type_dict['maxInclusive'])
        return None

    def verify_boolean(self):
        value_to_verify = self.node.getviewvalue()
        if value_to_verify not in ['true', 'false', '1', '0']:
            return self.return_error_record(u'Значение должно быть либо Да (true, 1), либо Нет (false, 0)')
        return None


class error_list(object):
    """ Класс для обработки списка ошибок """
    def __init__(self, errors, document_description = ''):
        self.errors = errors
        self.document_description = document_description
        if isinstance(self.document_description, unicode):
            self.document_description = self.document_description.encode('cp1251')
        self.build_nodes()

    def build_nodes(self):
        self.nodes = [(error[0], error[2]) for error in self.errors]
        
    def get_count(self):
        return len(self.errors)

    def get_error_description(self, index):
        return self.errors[index][1]

    def get_error_type(self, index):
        return self.errors[index][2]

    def get_error_node(self, index):
        return self.errors[index][0]

    def get_node_description(self, index):
        node = self.get_error_node(index)
        if node.xsd_element:
            return node.xsd_element.annotation
        else:
            return u''

    def remove_node(self, node):
        if not node.ignored:
            self.errors = [e for e in self.errors if e[0] != node]
        return not node.ignored
    
    def remove_node_and_children(self, node):
        if (node is not None) and (self.get_count() > 0):
            node.traverse2(self.remove_node)
            self.build_nodes()



    def to_string(self):
        return u'\n'.join([u'%s\n%s\n%s\n' % (self.get_error_node(i).getname(), self.get_node_description(i), self.get_error_description(i)) for i in range(self.get_count())])

    def __str__(self):
        return self.to_string().encode('cp866')

    def is_node_customerror(self, node):
        return (node, CUSTOM_ERROR) in self.nodes

    def is_node_error(self, node):
        return (node, SCHEMA_ERROR) in self.nodes

    def is_node_anyerror(self, node):
        return self.is_node_customerror(node) or self.is_node_error(node) or self.is_node_parent_error(node)

    def is_node_required(self, node):
        return node and (len(node.items) == 0) and node.xsd_element and not node.xsd_element.optional()

    def is_node_deep_required(self, node, loopname = ''):
        """ Является ли обязательным узел или кто-нибудь из детей?
            Пользовательская обязательность не проверяется.
        """
        r = False
        if node:
            if loopname:
                # задано имя повторяющегося элемента
                # сам узел не проверяем, а проверяем только его детей с этим именем
                itemlist = node.getbyname(loopname)
                for item in itemlist:
                    r = self.is_node_deep_required(item)
                    if r:
                        # обязательный - можно выходить
                        break
            else:
                if node.xsd_element:
                    if node.xsd_element.optional():
                        if not node.is_empty():
                            # необязательный непустой, проверить детей
                            for item in node.items:
                                r = self.is_node_deep_required(item)
                                if r:
                                    # обязательный - можно выходить
                                    break
                    else:
                        # обязательный
                        r = True
        return r

    def is_node_deep_error(self, node, loopname = ''):
        """ есть ли ошибки в узле или у кого-нибудь из детей """
        r = False
        if node:
            if loopname:
                # задано имя повторяющегося элемента
                # сам узел не проверяем, а проверяем только его детей с этим именем
                itemlist = node.getbyname(loopname)
            else:
                # проверим сам узел
                r = self.is_node_error(node)
                # и проверять будем всех детей
                itemlist = node.items
            if not r:
                for item in itemlist:
                    r = self.is_node_deep_error(item)
                    if r:
                        # ошибка - можно выходить
                        break
        return r

    def is_node_parent_error(self, node):
        """
        есть ли ошибки у непосредственного родителя?
        возможно, когда нарушено ограничение maxOccurs
        """
        r = False
        if node:
            # проверим сам узел
            r = self.is_node_error(node.parent)
        return r

    def is_node_required_ok(self, node):
        return node and self.is_node_required(node) and not self.is_node_error(node)

    def is_node_required_to_show(self, node):
        return node and ((not node.ignored) or self.is_node_anyerror(node))

    def is_node_deep_required_to_show(self, node, loopname = ''):
        """ Надо ли показывать узел? Если задано имя повторяющегося элемента
            сам узел не проверяем, а проверяем только его детей с этим именем
        """
        r = False
        if node:
            if loopname:
                # задано имя повторяющегося элемента
                # сам узел не проверяем, а проверяем только его детей с этим именем
                itemlist = node.getbyname(loopname)
                for item in itemlist:
                    r = r or (not item.ignored) or self.is_node_anyerror(node)
                    if r:
                        # уже надо показывать - можно выходить
                        break
            else:
                # проверим сам узел
                r = (not node.ignored) or self.is_node_anyerror(node)
        return r


if __name__ == "__main__":

    pass
