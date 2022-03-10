unit fsaintf;

{

     Интерфейс работы с поиском на странице деклараций соотвествия / сертификатов

     ToDo:
     1. Сделать продолжение поиска
     2. Обработка ошибки 500 (и других ошибок)
     3. Реализация поиска путем подмены Post запроса
     4. Убрать отправку WM_QUIT родительскому окну.

}


interface

uses tks_TLB, c4d_intf;

const

    CLASS_FSA_MANAGER : TGUID = '{1AE69067-D0DA-4BDF-B542-E1F07F5FD2BF}';

    FSA_STATUS_UNKNOWN = 0;
    FSA_STATUS_LOADING = 1;
    FSA_STATUS_READY = 2;
    FSA_STATUS_SEARCH = 3;
    FSA_STATUS_DONE = 4;
    FSA_STATUS_UNAVAILABLE = 5;

    FSA_UNKNOWN = -1;
    FSA_RDS_DECLARATION = 1;
    FSA_RSS_CERTIFICATE = 2;
    FSA_DEFAULT = FSA_RDS_DECLARATION;
    FSA_RDS_DECLARATION_CHECK = 3;
    FSA_RSS_CERTIFICATE_CHECK = 4;
    FSA_ANY = 99;

    FSA_CHECK_LOW = FSA_RDS_DECLARATION_CHECK;
    FSA_CHECK_HIGH = FSA_RSS_CERTIFICATE_CHECK;

    FSA_SEARCH_ALL = 0;
    FSA_SEARCH_BY_ONE = 1;

    FSA_RDS_URL = 'https://pub.fsa.gov.ru/rds/declaration';
    FSA_RDS_GET = 'https://pub.fsa.gov.ru/api/v1/rds/common/declarations/get';
    // ToDo: Переделать. Сделать собственную схему или еще что.
    // тут http - для того, чтобы работал fetch
    // плюс домен, чтобы CORS не ругался.
    // А так это просто уникальная ссылка по которой возвращается ранее полученный json
    FSA_RDS_CCSGET = 'https://pub.fsa.gov.ru/rds/declaration/ccsget';

    FSA_RSS_URL = 'https://pub.fsa.gov.ru/rss/certificate';
    FSA_RSS_GET = 'https://pub.fsa.gov.ru/api/v1/rss/common/certificates/get';
    FSA_RSS_CCSGET = 'https://pub.fsa.gov.ru/rss/certificate/ccsget';

type

    IFSADone = interface;
    IFSAWindow = interface;
    IFSACheckManager = interface;

    IFSAManager = interface
    ['{308BF71C-956E-41D4-AE97-659CD8CDF5E5}']
        function getWindow(const windowtype : Integer; out iwindow : ITKSWindow) : HResult; stdcall;
        function getWindowType(out windowtype : Integer): HResult; stdcall;
        function getUrl(const windowtype : Integer; out url : WideString): HResult; stdcall;
        function select(const windowtype : Integer; out json : WideString): HResult; stdcall;

        // формат поля data - json массив []
        // каждый элемент массива - словарь {}
        // обязательные элементы:
        // searchid - уникальный идентификатор поисковой информации (строка). Например, guid
        // служит для соотнесения результатов поиска с исходной инфомацией.
        // number - номер декларации соответствия (строка).
        // regdate - дата декларации соответствия (трока). формат dd.mm.yyyy

        // mode - режим работы поиска -
        // FSA_SEARCH_ALL - все ищется, а потом вызывается done.processing_result
        // FSA_SEARCH_BY_ONE - в процессе поиска для каждого номера вызывается done.processing_result

        function check(const windowtype : Integer;
                       const data : WideString;
                       const mode : Integer;
                       const done : IFSADone;
                       var ifsa : IFSAWindow
                       ): HResult; stdcall;

        // менеджер проверки. Добавляются документы, потом проверяются скопом.
        function get_check_manager(out manager : IFSACheckManager) : HResult; stdcall;
    end;

    IFSACheckManager = interface
    ['{34F14E4A-6B90-4598-A548-197B63E076C5}']
        function append_data(const windowtype : Integer; const data : WideString) : HResult; stdcall;
        function check(const mode : Integer; const done : IFSADone) : HResult; stdcall;
    end;

    IFSADone = interface
    ['{3136A2C0-4916-4A24-B419-BDDF4619FF82}']
        // json - результат поиска
        // формат {searchid1: {информация, переданная сервером},
        //         searchid2: {информация, переданная сервером},
        //        }
        procedure processing_result(const json : WideString; const has_more : boolean); stdcall;
        function status_changed(const json : WideString; const istatus : Integer; const sstatus : WideString; window : ITKSCEFWindow) : HResult; stdcall;
    end;


    // Объект, представляющий из себя "контейнер" для браузера
    // В момент уничтожения контейнера уничтожается окно поиска
    // На данный момент существует проблема, когда при уничтожении окна браузера
    // родительскому окну передается WM_QUIT

    IFSAWindow = interface
    ['{8D4DBE2B-3280-4CF6-AFFE-985DDE404044}']
        procedure get_window(out iwindow : ITKSWindow); stdcall;
        // пока окно расчитано только на один поиск.
        // планируется реализация повторного поиска
        procedure continue_search(const data : WideString); stdcall;
    end;

    IFSAData = interface
    ['{84454C30-3CDE-4DEB-93AD-9B7C6862B6FC}']
        function get_window_type() : Integer; stdcall;
        function get_data() : WideString; stdcall;
    end;


implementation

end.
