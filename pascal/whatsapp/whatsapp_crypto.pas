unit whatsapp_crypto;

interface

uses windows;

function get_hid : AnsiString;
function check_cert(const filename, phone : WideString; out error_message : WideString): boolean;

function crypto_binary_to_string(p : PBYTE; c : DWORD) : string;
function crypto_string_to_binary(str : PChar; var outlen : DWORD) : PBYTE;

implementation

uses WMIhwid, JwaWinCrypt, JwaWinError, WideStrUtils, classes, Sysutils
     , jclmime, MyStrUtils;

const 
    issuer_hash='jaNOwbd9pQRqi';

function get_hid : AnsiString;
var
    HWID : THardwareId;
begin
    Result := '';
    HWID := THardwareId.Create(True);
    try
        Result := HWID.HardwareIdMd5;
    finally
        HWID.Free;
    end;
end;

function extract_name(pName : PCERT_NAME_BLOB) : string;
var
   cIssuerName : DWORD;
   pIssuerName : PChar;
begin
    Result := '';
    cIssuerName := 2048;
    pIssuerName := AllocMem(cIssuerName);
    try
        CertNameToStr(X509_ASN_ENCODING,
                      pName,
                      CERT_X500_NAME_STR,
                      pIssuerName,
                      cIssuerName
                     );
        Result := StrPas(pIssuerName);
    finally
        FreeMem(pIssuerName);
    end;
end;

function FileTimeToDateTime( FileTime : TFileTime ) : TDateTime;
var
  SystemTime : TSystemTime;
  ModifiedTime : TFileTime;
begin
  FileTimeToLocalFileTime( FileTime, ModifiedTime );
  FileTimeToSystemTime( ModifiedTime, SystemTime );
  Result := SystemTimeToDateTime( SystemTime );
end;

function open_cert_store(out hStore: HCERTSTORE) : boolean;
begin
    hStore := CertOpenSystemStore(0, 'ROOT');
    Result := hStore <> nil;
end;

function readstring(const filename : string): string;
var
    fs : TFileStream;
    i : Integer;
begin
    fs := TFileStream.Create(filename, fmOpenRead);
    try
        with TStringList.Create do try
            LoadFromStream(fs);
            if Count > 1 then begin
                Delete(Count - 1);
                Delete(0);
            end;
            Result := '';
            for i := 0 to Count - 1 do
                Result := Result + Strings[i]
        finally
            Free;
        end;
    finally
        fs.Free;
    end;    
end;

function crypto_string_to_binary(str : PChar; var outlen : DWORD) : PBYTE;
var
    inlen: Cardinal;
begin
    Result := nil;
    inlen := StrLen(str);
    outlen := MimeDecodedSize(inlen);
    Result := AllocMem(outlen);
    outlen := MimeDecode(str^, inlen, Result^);
end;

function crypto_binary_to_string(p : PBYTE; c : DWORD) : string;
begin
    Result := '';
    SetLength(Result, MimeEncodedSize(c));
    MimeEncode(p^, c, Result[1]);
end;

function file_to_context(const filename : string; out pCert: PCCERT_CONTEXT) : boolean;
var
    certtext : string;
    pX509cert : PBYTE;
    cX509cert : DWORD;
begin
    Result := False;
    try
        certtext := readstring(filename);
        pX509cert := crypto_string_to_binary(PAnsiChar(certtext), cX509cert);
        try
            pCert := CertCreateCertificateContext(X509_ASN_ENCODING, pX509cert, cX509cert);
        finally
            FreeMem(pX509cert);
        end;
        Result := pCert <> nil;
        Result := True;
    except
        Result := False
    end;
end;

// получение SHA1 hash
// возвращает hash закодированный по BASE64
function get_certificate_hash(pContext : PCCERT_CONTEXT) : string;
var
   pvData : Pointer;
   cbData : DWORD;
begin
   Result := EmptyStr;
   if CertGetCertificateContextProperty(pContext, CERT_SHA1_HASH_PROP_ID, nil, cbData) then begin
      pvData := AllocMem(cbData);
      try
         if CertGetCertificateContextProperty(pContext, CERT_SHA1_HASH_PROP_ID, pvData, cbData) then begin
            Result := crypto_binary_to_string(pvData, cbData);
         end;
      finally
         FreeMem(pvData);
      end;
   end;
end;

function get_issuer_hash() : string;
begin
    Result := '2DCKhVW7Xauc30';
    if Result[Length(Result)] <> '=' then 
        Result := Result + '='
end;

function check_cert_context(const pCert: PCCERT_CONTEXT; out error_message : WideString) : boolean;
var
    hStore: HCERTSTORE;
    dwFlags: DWORD;
    pIssuer: PCCERT_CONTEXT;
begin
    if open_cert_store(hStore) then begin
        dwFlags := CERT_STORE_REVOCATION_FLAG or
            CERT_STORE_SIGNATURE_FLAG or
            CERT_STORE_TIME_VALIDITY_FLAG;
        try
            pIssuer := CertGetIssuerCertificateFromStore(
                hStore, pCert, nil, dwFlags);
            if pIssuer <> nil then try
                if get_certificate_hash(pIssuer) <> (issuer_hash + get_issuer_hash()) then begin
                    error_message := 'Неверный корневой сертификат';
                    Result := False;
                    Exit;
                end;
                if (dwFlags and CERT_STORE_SIGNATURE_FLAG) = CERT_STORE_SIGNATURE_FLAG then begin
                    error_message := 'Неверная ЭЦП сертификата';
                    Result := False;
                    Exit;
                end;
                if (dwFlags and CERT_STORE_TIME_VALIDITY_FLAG) = CERT_STORE_TIME_VALIDITY_FLAG then begin
                    error_message := 'Период действия сертификата окончился или еще не начался';
                    Result := False;
                    Exit;
                end;
                Result := True;
            finally
                CertFreeCertificateContext(pIssuer);
                pIssuer := nil;
            end;
        except
            on E : Exception do begin
                Result := False;
                error_message := e.message;
            end;
        end;
        
        CertCloseStore(hStore, 0);
        hStore := nil;
    end;
end;

function extract_fieldname(fieldname, fieldvalue : string) : string;
var
    l : TStrings;
begin
    Result := '';
    l := TStringList.Create;
    try
        StrToList(fieldvalue, ', ', l);
        Result := l.Values[fieldname]
    finally
        l.Free;
    end;
end;

function check_cert(const filename, phone : WideString; out error_message : WideString): boolean;
var
    pCert: PCCERT_CONTEXT;
    hid : string;
    hphone : string;
    phones : TStrings;
begin
    Result := False;
    if file_to_context(filename, pCert) then try
        Result := check_cert_context(pCert, error_message);
        if Result then begin
            hid := extract_fieldname('O', extract_name(@pCert^.pCertInfo^.Subject));
            Result := hid = get_hid();
            if not Result then
                error_message := 'Сертификат выдан на другой hardware id.'
            else if phone <> EmptyStr then begin
                hphone := extract_fieldname('E', extract_name(@pCert^.pCertInfo^.Subject));
                if hphone <> EmptyStr then begin
                    phones := TStringList.Create;
                    try
                        StrToList(hphone, ', ', phones);
                        Result := phones.indexof(phone) <> -1;
                        if not Result then
                            error_message := WideFormat('Программа не может обрабатывать указанный номер телефона. %s', [phone]);
                    finally
                        phones.Free;
                    end;
                end;
            end;
        end
    finally
        CertFreeCertificateContext(pCert);
        pCert := nil;
    end else
        error_message := WideFormat('Не найден файл сертификата привязки %s', [filename]);
end;

end.
