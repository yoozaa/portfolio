unit fsafunc;

interface

uses fsaintf;

function GetDocumentType(const Number: WideString): Integer;
function GetDocumentCheckType(const DocType: Integer): Integer;
function FormatRegDate(const Date: TDateTime): WideString;
function get_document_status(const istatus : Integer) : WideString;

implementation

uses JvJCLUtils, SysUtils;

// ЕАЭС N RU Д-RU.РА01.В.71855/21 - декларация соответствия
// ЕАЭС RU С-RU.АЖ56.В.00954/21 - сертификат

function GetDocumentType(const Number: WideString): Integer;
begin
  Result := FSA_UNKNOWN;
  if IsWild(number, '*Д-*', True) then
    Result := FSA_RDS_DECLARATION
  else if IsWild(number, '*С-*', True) then
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
        20: Result := 'Черновик';
        13: Result := 'Отправлен';
        18: Result := 'Удалён';
        06: Result := 'Действует';
        14: Result := 'Прекращён';
        15: Result := 'Приостановлен';
        19: Result := 'Частично приостановлен';
        03: Result := 'Возобновлён';
        16: Result := 'Продлён';
        01: Result := 'Архивный';
        10: Result := 'Направлено уведомление о прекращении';
        05: Result := 'Выдано предписание';
        42: Result := 'Ожидает проверки оператора реестра';
        98: Result := 'Проверка';
        99: Result := 'Сервер не доступен';
        100: Result := 'Не найден';
    else
        Result := 'Неизвестный статус';
    end;
end;

end.
