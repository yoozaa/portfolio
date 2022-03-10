unit fsafunc;

interface

uses fsaintf;

function GetDocumentType(const Number: WideString): Integer;
function GetDocumentCheckType(const DocType: Integer): Integer;
function FormatRegDate(const Date: TDateTime): WideString;
function get_document_status(const istatus : Integer) : WideString;

implementation

uses JvJCLUtils, SysUtils;

// ���� N RU �-RU.��01.�.71855/21 - ���������� ������������
// ���� RU �-RU.��56.�.00954/21 - ����������

function GetDocumentType(const Number: WideString): Integer;
begin
  Result := FSA_UNKNOWN;
  if IsWild(number, '*�-*', True) then
    Result := FSA_RDS_DECLARATION
  else if IsWild(number, '*�-*', True) then
    Result := FSA_RSS_CERTIFICATE;
end;

function GetDocumentCheckType(const DocType: Integer): Integer;
begin
  case DocType of
    FSA_RDS_DECLARATION: Result := FSA_RDS_DECLARATION_CHECK;
    FSA_RSS_CERTIFICATE: Result := FSA_RSS_CERTIFICATE_CHECK;
    else                 Result := FSA_UNKNOWN;
  end;
end;

function FormatRegDate(const Date: TDateTime): WideString;
begin
  Result := FormatDateTime('dd.mm.yyyy', Date);
end;

function get_document_status(const istatus : Integer) : WideString;
begin
    case istatus of
        20: Result := '��������';
        13: Result := '���������';
        18: Result := '�����';
        06: Result := '���������';
        14: Result := '���������';
        15: Result := '�������������';
        19: Result := '�������� �������������';
        03: Result := '����������';
        16: Result := '������';
        01: Result := '��������';
        10: Result := '���������� ����������� � �����������';
        05: Result := '������ �����������';
        42: Result := '������� �������� ��������� �������';
        98: Result := '��������';
        99: Result := '������ �� ��������';
        100: Result := '�� ������';
    else
        Result := '����������� ������';
    end;
end;

end.
