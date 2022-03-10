# -*- coding: cp1251 -*-

"""

    ���������������� - ���������� ��� ������������� � uwsgi

    ���������:
    
    document_template - ������ ������ ���������

    
    ��������,

    application, args = WebLawApp.init_weblaw_app(
        document_template='tks_ru_document.thtml'
    )

"""

from weblaw import DjangoWebLawApp

application, args = DjangoWebLawApp.init_weblaw_app(template_mode=True)

