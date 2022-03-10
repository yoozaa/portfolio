unit fsaintf;

{

     ��������� ������ � ������� �� �������� ���������� ����������� / ������������

     ToDo:
     1. ������� ����������� ������
     2. ��������� ������ 500 (� ������ ������)
     3. ���������� ������ ����� ������� Post �������
     4. ������ �������� WM_QUIT ������������� ����.

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
    // ToDo: ����������. ������� ����������� ����� ��� ��� ���.
    // ��� http - ��� ����, ����� ������� fetch
    // ���� �����, ����� CORS �� �������.
    // � ��� ��� ������ ���������� ������ �� ������� ������������ ����� ���������� json
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

        // ������ ���� data - json ������ []
        // ������ ������� ������� - ������� {}
        // ������������ ��������:
        // searchid - ���������� ������������� ��������� ���������� (������). ��������, guid
        // ������ ��� ����������� ����������� ������ � �������� ����������.
        // number - ����� ���������� ������������ (������).
        // regdate - ���� ���������� ������������ (�����). ������ dd.mm.yyyy

        // mode - ����� ������ ������ -
        // FSA_SEARCH_ALL - ��� ������, � ����� ���������� done.processing_result
        // FSA_SEARCH_BY_ONE - � �������� ������ ��� ������� ������ ���������� done.processing_result

        function check(const windowtype : Integer;
                       const data : WideString;
                       const mode : Integer;
                       const done : IFSADone;
                       var ifsa : IFSAWindow
                       ): HResult; stdcall;

        // �������� ��������. ����������� ���������, ����� ����������� ������.
        function get_check_manager(out manager : IFSACheckManager) : HResult; stdcall;
    end;

    IFSACheckManager = interface
    ['{34F14E4A-6B90-4598-A548-197B63E076C5}']
        function append_data(const windowtype : Integer; const data : WideString) : HResult; stdcall;
        function check(const mode : Integer; const done : IFSADone) : HResult; stdcall;
    end;

    IFSADone = interface
    ['{3136A2C0-4916-4A24-B419-BDDF4619FF82}']
        // json - ��������� ������
        // ������ {searchid1: {����������, ���������� ��������},
        //         searchid2: {����������, ���������� ��������},
        //        }
        procedure processing_result(const json : WideString; const has_more : boolean); stdcall;
        function status_changed(const json : WideString; const istatus : Integer; const sstatus : WideString; window : ITKSCEFWindow) : HResult; stdcall;
    end;


    // ������, �������������� �� ���� "���������" ��� ��������
    // � ������ ����������� ���������� ������������ ���� ������
    // �� ������ ������ ���������� ��������, ����� ��� ����������� ���� ��������
    // ������������� ���� ���������� WM_QUIT

    IFSAWindow = interface
    ['{8D4DBE2B-3280-4CF6-AFFE-985DDE404044}']
        procedure get_window(out iwindow : ITKSWindow); stdcall;
        // ���� ���� ��������� ������ �� ���� �����.
        // ����������� ���������� ���������� ������
        procedure continue_search(const data : WideString); stdcall;
    end;

    IFSAData = interface
    ['{84454C30-3CDE-4DEB-93AD-9B7C6862B6FC}']
        function get_window_type() : Integer; stdcall;
        function get_data() : WideString; stdcall;
    end;


implementation

end.
