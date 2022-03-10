# -*- coding: cp1251 -*-

"""

    Законодательство - приложение для использования с uwsgi

    Параметры:
    
    document_template - шаблон текста документа

    
    Например,

    application, args = WebLawApp.init_weblaw_app(
        document_template='tks_ru_document.thtml'
    )

"""

from weblaw import DjangoWebLawApp

application, args = DjangoWebLawApp.init_weblaw_app(template_mode=True)

