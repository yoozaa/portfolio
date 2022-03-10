unit crypto_func;

//Не использовать CryptBinaryToString, отсутствующую в W2K.
//Флаг определяется в make.bat {.$define NOCRYPTBINARY}

interface

procedure init_func;

implementation

uses

   windows, SysUtils, PythonEngine, crypto_main,
   JwaWinCrypt, JwaWinError, WideStrUtils,
   classes
   {$IFDEF NOCRYPTBINARY}
   , jclmime, TksCryptDlg
   {$ELSE}
   , JwaCryptUIApi
   {$ENDIF}
   ;


const
   CP_SMARTCARD_PROV  = 'Crypto-Pro SmartCard CSP';
   CP_KC1_GR3410_94_PROV  = 'Crypto-Pro GOST R 34.10-94 KC1 CSP';
   CP_KC1_GR3410_2001_PROV  = 'Crypto-Pro GOST R 34.10-2001 KC1 CSP';
   CP_KC2_GR3410_94_PROV  = 'Crypto-Pro GOST R 34.10-94 KC2 CSP';
   CP_KC2_GR3410_2001_PROV  = 'Crypto-Pro GOST R 34.10-2001 KC2 CSP';
   PH_GR3410_94_PROV  = 'Phoenix-CS GOST R 34.10-94 Cryptographic Service Provider';
   PH_GR3410_2001_PROV  = 'Phoenix-CS GOST R 34.10-2001 Cryptographic Service Provider';

   ALG_SID_GR3411 = 30;
   // G28147 sub_ids
   ALG_SID_G28147 = 30;
   ALG_SID_GR3411_2012_256 = 33;
   ALG_SID_GR3411_2012_512 = 34;
   ALG_SID_PRODIVERS = 38;
   ALG_SID_RIC1DIVERS = 40;
   // Export Key sub_id
   ALG_SID_PRO_EXP = 31;
   ALG_SID_SIMPLE_EXP = 32;
   // Hash sub ids
   ALG_SID_GR3410 = 30;
   ALG_SID_G28147_MAC = 31;
   ALG_SID_TLS1_MASTER_HASH = 32;

   ALG_SID_DH_EX_SF = 30;
   ALG_SID_DH_EX_EPHEM = 31;
   ALG_SID_PRO_AGREEDKEY_DH = 33;
   ALG_SID_PRO_SIMMETRYKEY = 34;
   ALG_SID_GR3410EL = 35;
   ALG_SID_DH_EL_SF = 36;
   ALG_SID_DH_EL_EPHEM = 37;


// Типы провайдеров
   PROV_GOST_94_DH = 71;
   PROV_GOST_2001_DH = 75;   // создает ключи алгоритма ГОСТ Р 34.10-2001.
   PROV_GOST_2012_256 = 80;  // создает ключи алгоритма ГОСТ Р 34.10-2012 длины 256 бит (длина открытого ключа 512 бит).
   PROV_GOST_2012_512 = 81;  // создает ключи алгоритма ГОСТ Р 34.10-2012 длины 512 бит (длина открытого ключа 1024 бита).

// Идентификаторы алгоритмов хэширования
   CALG_GR3411 = ALG_CLASS_HASH or ALG_TYPE_ANY or ALG_SID_GR3411;                    // ГОСТ Р 34.11-94
   CALG_GR3411_2012_256 = ALG_CLASS_HASH or ALG_TYPE_ANY or ALG_SID_GR3411_2012_256;  // ГОСТ Р 34.11-2012, длина выхода 256 бит
   CALG_GR3411_2012_512 = ALG_CLASS_HASH or ALG_TYPE_ANY or ALG_SID_GR3411_2012_512;  // ГОСТ Р 34.11-2012, длина выхода 512 бит

// Объектные идентификаторы функций хеширования
    szOID_CP_GOST_R3411 = '1.2.643.2.2.9';             // Функция хэширования ГОСТ Р 34.11-94
    szOID_CP_GOST_R3411_12_256 = '1.2.643.7.1.1.2.2';  // Функция хэширования ГОСТ Р 34.11-2012, длина выхода 256 бит
    szOID_CP_GOST_R3411_12_512 = '1.2.643.7.1.1.2.3';  // Функция хэширования ГОСТ Р 34.11-2012, длина выхода 512 бит

// Объектные идентификаторы алгоритмов цифровой подписи
    szOID_CP_GOST_R3411_R3410 = '1.2.643.2.2.4';            // Алгоритм цифровой подписи ГОСТ Р 34.10-94
    szOID_CP_GOST_R3411_R3410EL = '1.2.643.2.2.3';          // Алгоритм цифровой подписи ГОСТ Р 34.10-2001
    szOID_CP_GOST_R3411_12_256_R3410 = '1.2.643.7.1.1.3.2'; // Алгоритм цифровой подписи ГОСТ Р 34.10-2012 для ключей длины 256 бит
    szOID_CP_GOST_R3411_12_512_R3410 = '1.2.643.7.1.1.3.3'; // Алгоритм цифровой подписи ГОСТ Р 34.10-2012 для ключей длины 512 бит


    LastErrorMessage : string = '';


function LastError(const s : string = '') : string;
var
   Msg: PChar;
   ErrNo: integer;
begin
   Result := '';
   ErrNo := GetLastError;
   Msg := AllocMem(4096);
   try
      FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM,
                    nil,
                    ErrNo,
                    0,
                    Msg,
                    4096,
                    nil);
      Result := s + #13#10 + LastErrorMessage + #13#10 + strpas(Msg);
   finally
      FreeMem(Msg);
   end;
end;


function ErrorDesc(err_code: integer): string;
var
    Msg: PChar;
begin
    Result := '';
    Msg := AllocMem(4096);
    try
        FormatMessage(
            FORMAT_MESSAGE_FROM_SYSTEM,
            nil,
            err_code,
            0,
            Msg,
            4096,
            nil);
        Result := TrimRight(strpas(Msg));
    finally
        FreeMem(Msg);
    end;
end;


// ---------- BASE64 TRANSLATION
//
// Фукнции преобразования бинарного представления в BASE64 и обратно
// Внимание! Используется CryptBinaryToString (функция отсутствует в W2K)
// или MimeEncode/MimeDecode из JclMime, если определен флаг NOCRYPTBINARY.
//

function crypto_binary_to_string(p : PBYTE; c : DWORD) : string;
{$IFNDEF NOCRYPTBINARY}
var
   pCert : PChar;
   cCert : DWORD;
{$ENDIF}
begin
   Result := '';
{$IFDEF NOCRYPTBINARY}
  SetLength(Result, MimeEncodedSize(c));
  MimeEncode(p^, c, Result[1]);
{$ELSE}
   if CryptBinaryToString(p, c, CRYPT_STRING_BASE64, nil, cCert) then begin
      pCert := AllocMem(cCert);
      try
         CryptBinaryToString(p, c, CRYPT_STRING_BASE64, pCert, cCert);
         Result := strpas(pCert);
      finally
         FreeMem(pCert);
      end;
   end;
{$ENDIF}
end;

function crypto_string_to_binary(str : PChar; var outlen : DWORD) : PBYTE;
{$IFDEF NOCRYPTBINARY}
var
  inlen: Cardinal;
{$ENDIF}
begin
   Result := nil;
{$IFDEF NOCRYPTBINARY}
   inlen := StrLen(str);
   outlen := MimeDecodedSize(inlen);
   Result := AllocMem(outlen);
   outlen := MimeDecode(str^, inlen, Result^);
{$ELSE}
   if CryptStringToBinary(str, 0, CRYPT_STRING_BASE64, nil, outlen, 0, nil) then begin
      Result := AllocMem(outlen);
      CryptStringToBinary(str, 0, CRYPT_STRING_BASE64, Result, outlen, 0, nil);
   end;
{$ENDIF}
end;

// ----------- END OF BASE64 TRANSLATION

// поиск сертификата по subject или по hash
function find_certificate(hStore : HCERTSTORE; pwcert : PWideChar; phash : PChar) : PCCERT_CONTEXT;
var
   pCertID : PCERT_ID;
begin
   Result := nil;
   if (phash <> nil) and (strlen(phash) > 0) then begin
      new(pCertID);
      try
         pCertID^.dwIdChoice := CERT_ID_SHA1_HASH;
         pCertID^.HashId.pbData := crypto_string_to_binary(phash, pCertID^.HashId.cbData);
         Result := CertFindCertificateInStore(hStore,
                                              X509_ASN_ENCODING or PKCS_7_ASN_ENCODING,
                                              0,
                                              CERT_FIND_CERT_ID,
                                              pCertID,
                                              nil);               
      finally
         dispose(pCertID)
      end;
   end else if wstrlen(pwcert) > 0 then
      Result := CertFindCertificateInStore(hStore,
                                           X509_ASN_ENCODING or PKCS_7_ASN_ENCODING,
                                           0,
                                           CERT_FIND_SUBJECT_STR,
                                           pwcert,
                                           nil)
   else
      Result := CertFindCertificateInStore(hStore,
                                           X509_ASN_ENCODING or PKCS_7_ASN_ENCODING,
                                           0,
                                           CERT_FIND_ANY,
                                           nil,
                                           nil);
   
end;

// получение имени сертификата
function get_certificate_name(pContext : PCCERT_CONTEXT; out certname : WideString): boolean;
var
   pszName : pChar;
   cbSize : Cardinal;
begin
    Result := False;
    cbSize := CertGetNameString(pContext,
                                CERT_NAME_SIMPLE_DISPLAY_TYPE,
                                0,
                                nil,
                                nil,
                                0);
    
    if cbSize > 0 then begin
       pszName := AllocMem(cbSize);
       try
          if CertGetNameString(pContext,
                               CERT_NAME_SIMPLE_DISPLAY_TYPE,
                               0,
                               nil,
                               pszName,
                               cbSize) > 0
          then begin
             certname := strpas(pszName);
             Result := True;
          end;
       finally
          FreeMem(pszName);
       end;
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

// выбор сертификата из хранилища MY
// возвращает имя или hash сертификата
function crypto_select_certificate( self, args : PPyObject ) : PPyObject; cdecl;
var
   hStore : HCERTSTORE;
   pContext : PCCERT_CONTEXT;
   outstr : WideString;
   hashret : Integer;
   wnd : HWND;
   {$IFDEF NOCRYPTBINARY}
   certselect: TCertSelectStruct;
   rc: bool;
   {$ENDIF NOCRYPTBINARY}
begin
   LastErrorMessage := '';
   outstr := EmptyStr;
   hashret := 0;
   wnd := 0;
   with GetPythonEngine do begin
      PyArg_ParseTuple( args, '|ii', @hashret, @wnd );
      hStore := CertOpenSystemStore(0, 'MY');
      if hStore <> nil then try
         {$IFDEF NOCRYPTBINARY}
            pContext := nil;
            ZeroMemory(@certselect, SizeOf(TCertSelectStruct));
            certselect.dwSize           := sizeof(TCertSelectStruct);
            certselect.hwndParent       := wnd;
            certselect.hInstance        := HInstance;
            certselect.pTemplateName    := nil;
            certselect.dwFlags          := 0;
            certselect.szTitle          := nil;
            certselect.cCertStore       := 1;
            certselect.arrayCertStore   := @hStore;
            certselect.szPurposeOid     := nil;
            certselect.cCertContext     := 1;
            certselect.arrayCertContext := @pContext;
            certselect.lCustData        := 0;
            certselect.pfnHook          := nil;
            certselect.pfnFilter        := nil;
            certselect.szHelpFileName   := nil;
            certselect.dwHelpId         := 0;
            certselect.hprov            := 0;
            rc := CertSelectCertificate(@certselect);
            if not rc then begin
              pContext := nil;
            end;
         {$ELSE}
            pContext := CryptUIDlgSelectCertificateFromStore(hStore, wnd,
                        nil, nil, CRYPTUI_SELECT_LOCATION_COLUMN, 0, nil);
         {$ENDIF NOCRYPTBINARY}
         if pContext <> nil then try
            if hashret = 0 then
               get_certificate_name(pContext, outstr)
            else
               outstr := get_certificate_hash(pContext);
         finally
            CertFreeCertificateContext(pContext);
         end;
      finally
         CertCloseStore(hStore, 0);
      end;
      Result := VariantAsPyObject(outstr);
      //Py_IncRef(Result);
   end;
end;

function crypto_get_certificate( self, args : PPyObject ) : PPyObject; cdecl;
var
   obj : PPyObject;
   hStore : HCERTSTORE;
   pContext : PCCERT_CONTEXT;
   s : WideString;
   phash : PChar;
   certstring : WideString;
begin
   LastErrorMessage := '';
   with GetPythonEngine do begin
      certstring := EmptyStr;
      phash := nil;
      PyArg_ParseTuple( args, 'O|s', @obj, @phash );
      s := PyObjectAsVariant(obj);
      pContext := nil;
      hStore := CertOpenSystemStore(0, 'MY');      
      if hStore <> nil then try
         pContext := find_certificate(hStore, PWideChar(s), phash);
         if pContext <> nil then try
            certstring := crypto_binary_to_string(pContext.pbCertEncoded, pContext.cbCertEncoded);
         finally
            CertFreeCertificateContext(pContext);
         end;
      finally
         CertCloseStore(hStore, 0);
      end;
      Result := VariantAsPyObject(certstring);
      //Py_IncRef(Result);
   end;
end;

const

//* OID for HASH */
  HP_OID = $000A;
  OID_HashTest = '1.2.643.2.2.30.0';
  OID_HashVerbaO = '1.2.643.2.2.30.1';	//* ГОСТ Р 34.11-94, параметры по умолчанию */
  OID_HashVar_1 = '1.2.643.2.2.30.2';
  OID_HashVar_2 = '1.2.643.2.2.30.3';
  OID_HashVar_3 = '1.2.643.2.2.30.4';
  OID_HashVar_Default = OID_HashVerbaO;

function crypto_get_digestvalue( self, args : PPyObject ) : PPyObject; cdecl;
var
   str : PChar;
   outstring : WideString;
   context: HCRYPTPROV;
   hash: HCRYPTHASH;
   data: PChar;
   hashSize, dwordSize: DWORD;
   gost_2012 : Integer;
   prov_type, hash_alg_id: Integer;
begin
   LastErrorMessage := '';
   with GetPythonEngine do
   begin
      outstring := EmptyStr;
      PyArg_ParseTuple( args, 's|i', @str, @gost_2012);
      if gost_2012 = 1 then begin
         prov_type := PROV_GOST_2012_256;
         hash_alg_id := CALG_GR3411_2012_256;
      end else begin
         prov_type := PROV_GOST_2001_DH;
         hash_alg_id := CALG_GR3411;
      end;

      if CryptAcquireContext(context, nil, nil, prov_type, CRYPT_VERIFYCONTEXT) then try
         CryptCreateHash(context, hash_alg_id, 0, 0, hash);
         try
            //CryptSetHashParam(hash, HP_OID, PBYTE(pChar(OID_HashVar_3)), 0);
            CryptHashData(hash, Pointer(str), strlen(str), 0);
            dwordSize := SizeOf(DWORD);
            CryptGetHashParam(hash, HP_HASHSIZE, @hashSize, dwordSize, 0);
            data := AllocMem(hashSize);
            try
               CryptGetHashParam(hash, HP_HASHVAL, Pointer(data), hashSize, 0);
               outstring := crypto_binary_to_string(Pointer(data), hashSize);
            finally
               FreeMem(data);
            end;
         finally
            CryptDestroyHash(hash);
         end;
      finally
         CryptReleaseContext(context, 0);
      end;
      Result := VariantAsPyObject(outstring);
      //Py_IncRef(Result);
   end;
end;


const
   PROV_RSA_AES = 24;
   CALG_SHA1    = $00008004; 
   CALG_SHA_256 = $0000800C;
   CALG_SHA_384 = $0000800D;
   CALG_SHA_512	= $0000800E;
   
function crypto_get_password_hash( self, args : PPyObject ) : PPyObject; cdecl;
var
   str : PChar;
   outstring : WideString;
   context: HCRYPTPROV;
   hash: HCRYPTHASH;
   data: PChar;
   hashSize, dwordSize: DWORD;
begin
   LastErrorMessage := '';
   with GetPythonEngine do
   begin
      outstring := EmptyStr;
      PyArg_ParseTuple( args, 's', @str );
      if CryptAcquireContext(context, nil, nil, PROV_RSA_AES, CRYPT_VERIFYCONTEXT) then try
         CryptCreateHash(context, CALG_SHA_256, 0, 0, hash);
         try
            CryptHashData(hash, Pointer(str), strlen(str), 0);
            dwordSize := SizeOf(DWORD);
            CryptGetHashParam(hash, HP_HASHSIZE, @hashSize, dwordSize, 0);
            data := AllocMem(hashSize);
            try
               CryptGetHashParam(hash, HP_HASHVAL, Pointer(data), hashSize, 0);
               outstring := crypto_binary_to_string(Pointer(data), hashSize);
            finally
               FreeMem(data);
            end;
         finally
            CryptDestroyHash(hash);
         end;
      finally
         CryptReleaseContext(context, 0);
      end;
      Result := VariantAsPyObject(outstring);
      //Py_IncRef(Result);
   end;
end;


function crypto_get_sign_message( self, args : PPyObject ) : PPyObject; cdecl;
var
   str : PChar;
   outstring : WideString;
   certname : WideString;
   containerName : string;
   context: HCRYPTPROV;
   hash: HCRYPTHASH;
   data: PBYTE;
   tmpBuf : PBYTE;
   signSize: DWORD;
   revert_buffer : Integer;
   obj : PPyObject;

   MessageArray : TByteArray;
   MessageSize : TDWordArray;
   MessageCert : TPCCertContextArray;

   SigParams : CRYPT_SIGN_MESSAGE_PARA;

   hStore : HCERTSTORE;
   pContext : PCCERT_CONTEXT;
   pHash : PChar;

   gost_2012 : Integer;
   hash_alg_oid: PAnsiChar;

   err_code: integer;
   err_desc: string;

begin
   LastErrorMessage := '';
   with GetPythonEngine do begin
      outstring := EmptyStr;
      err_code := 0;
      err_desc := EmptyStr;
      revert_buffer := 0;
      pHash := nil;
      PyArg_ParseTuple( args, 'sO|isi', @str, @obj, @revert_buffer, @pHash, @gost_2012);
      certname := PyObjectAsVariant(obj);
      hStore := CertOpenSystemStore(0, 'MY');
      if hStore <> nil then try
         pContext := find_certificate(hStore, PWideChar(certname), pHash);
         if pContext <> nil then try
            if gost_2012 = 1 then
                hash_alg_oid := szOID_CP_GOST_R3411_12_256
            else
                hash_alg_oid := szOID_CP_GOST_R3411;
            SetLength(MessageArray, 1);
            SetLength(MessageSize, 1);
            SetLength(MessageCert, 1);
            MessageArray[0] := Pointer(str);
            MessageSize[0] := strlen(str);
            FillChar(SigParams, SizeOf(CRYPT_SIGN_MESSAGE_PARA ), 0);
            SigParams.cbSize := SizeOF(CRYPT_SIGN_MESSAGE_PARA);
            SigParams.dwMsgEncodingType := X509_ASN_ENCODING or PKCS_7_ASN_ENCODING;
            SigParams.pSigningCert := pContext;
            SigParams.HashAlgorithm.pszObjId := hash_alg_oid;
            SigParams.cMsgCert := 0;
            if CryptSignMessage(@SigParams, True, 1, Pointer(MessageArray), Pointer(MessageSize), nil, signSize) then begin
               data := AllocMem(signSize);
               try
                  if CryptSignMessage(@SigParams, True, 1, Pointer(MessageArray), Pointer(MessageSize), data, signSize) then begin
                     outstring := crypto_binary_to_string(data, signSize);
                  end else begin
                     err_code := GetLastError();
                     err_desc := ErrorDesc(err_code);
                  end;
               finally
                  FreeMem(data);
               end;
            end else begin
               err_code := GetLastError();
               err_desc := ErrorDesc(err_code);
            end;
         finally
            CertFreeCertificateContext(pContext);
         end;
      finally
         CertCloseStore(hStore, 0);
      end;
      Result := PyTuple_New(3);
      PyTuple_SetItem(Result, 0, VariantAsPyObject(outstring));
      PyTuple_SetItem(Result, 1, PyLong_FromUnsignedLong(err_code));
      PyTuple_SetItem(Result, 2, VariantAsPyObject(err_desc));
   end;
end;

procedure RevertBytes(p : PBYTE; c : DWORD);
var
   i : Integer;
   b : Byte;
   f : PBYTE;
   l : PBYTE;
begin
  f := p;
  l := p;
  inc(l, c - 1);
  for i := 0 to (c div 2)-1 do
    begin
      b := f^;
      f^ := l^;
      l^ := b;
      inc(f);
      dec(l);
    end;
end;


// Не используется после перехода Раунда (МПС) на таможенные стандарты по формированию ЭП
function SignMessage(Data: PChar; CertHash: PChar): String;
var
  hContext       : HCRYPTPROV;
  pCertificate   : PCCERT_CONTEXT;
  hHash          : HCRYPTHASH;
  hStore         : HCERTSTORE;
  CallerFreeProv : BOOL;
  dwKeySpec      : DWORD;
  dwSize         : DWORD; 
  dwHashSize     : DWORD; 
  Hash           : PByte;
  Buf            : PByte;
  hKey           : HCRYPTKEY;
  pKey           : PByte;
begin
  hStore := CertOpenSystemStore(0, 'MY');
  if hStore <> nil then
    try
      pCertificate := find_certificate(hStore, nil, CertHash);
      if pCertificate <> nil then
        try
          if CryptAcquireContext(hContext, nil, nil, PROV_GOST_2001_DH, CRYPT_VERIFYCONTEXT) then
            try
              dwKeySpec := AT_SIGNATURE;
              if CryptAcquireCertificatePrivateKey(pCertificate, 0, nil, hContext, @dwKeySpec, nil) then
                try
                  if CryptCreateHash(hContext, CALG_GR3411, 0, 0, hHash) then
                    try
                      CryptHashData(hHash, Pointer(Data), StrLen(Data), 0);
                      if CryptSignHash(hHash, AT_KEYEXCHANGE, nil, 0, nil, @dwSize) then
                        begin
                          Buf := AllocMem(dwSize);
                          try
                            if CryptSignHash(hHash, AT_KEYEXCHANGE, nil, 0, Buf, @dwSize) then
                              begin
                                RevertBytes(Buf, dwSize);
                                Result := crypto_binary_to_string(Buf, dwSize);
                              end
                          finally
                            FreeMem(Buf);
                          end;
                        end
                    finally
                      CryptDestroyHash(hHash);
                    end
                finally
                end
            finally
              CryptReleaseContext(hContext, 0);
            end
        finally
          CertFreeCertificateContext(pCertificate);
        end
    finally
      CertCloseStore(hStore, 0);
    end;
end;

// Не используется после перехода Раунда (МПС) на таможенные стандарты по формированию ЭП
function crypto_get_sign_message_mps( self, args : PPyObject ) : PPyObject; cdecl;
var
   str : PChar;
   outstring : WideString;
   certname : WideString;
   revert_buffer : Integer;
   obj : PPyObject;
   pHash : PChar;
begin
   LastErrorMessage := '';
   with GetPythonEngine do
     begin
       outstring := EmptyStr;
       revert_buffer := 0;
       pHash := nil;
       PyArg_ParseTuple( args, 'sO|is', @str, @obj, @revert_buffer, @pHash );
       outstring := SignMessage(str, pHash);
       Result := VariantAsPyObject(outstring); 
     end;       
end;

function get_encoding() : DWORD;
begin
  //Result := X509_ASN_ENCODING or PKCS_7_ASN_ENCODING;
  //Result := PKCS_7_ASN_ENCODING;
  Result := X509_ASN_ENCODING;
end;

function MyGetSignerCertificateCallback(pvGetArg: Pointer;
                                        dwCertEncodingType: DWORD; pSignerId: PCERT_INFO;
                                        hMsgCertStore: HCERTSTORE): PCCERT_CONTEXT; stdcall;
begin
  Result := PCCERT_CONTEXT(pvGetArg);
end;

function crypto_verify_sign_message( self, args : PPyObject ) : PPyObject; cdecl;
var
   X509cert, sv : PChar;
   pX509cert, psv, tmpBuf : PBYTE;
   cX509cert, csv : DWORD;
   str : PChar;
   context: HCRYPTPROV;
   r : boolean;

   hPubKey : HCRYPTKEY;
   pContext, pppppp : PCCERT_CONTEXT;
   pKeyInfo: PCERT_PUBLIC_KEY_INFO;
   hash: HCRYPTHASH;

   verify_sign, gost_2012, prov_type : Integer;

   VerifyParams : CRYPT_VERIFY_MESSAGE_PARA;

   DecodeSize : DWORD;

   MessageArray: TCPByteArray;
   MessageSize: TCDWordArray;

   rr : LongInt;

begin
   LastErrorMessage := '';
   with GetPythonEngine do begin
      r := False;
      verify_sign := 1;
      PyArg_ParseTuple( args, 'sss|ii', @X509cert, @sv, @str, @verify_sign, @gost_2012);
      if verify_sign = 0 then
         r := True
      else begin
         pX509cert := crypto_string_to_binary(X509cert, cX509cert);
         if pX509cert <> nil then try
            if gost_2012 = 1 then
                prov_type := PROV_GOST_2012_256
            else
                prov_type := PROV_GOST_2001_DH;
            if CryptAcquireContext(context, nil, nil, prov_type, CRYPT_VERIFYCONTEXT) then try
               pContext := CertCreateCertificateContext(get_encoding, pX509cert, cX509cert);
               if pContext <> nil then begin
                  psv := crypto_string_to_binary(sv, csv);
                  if psv <> nil then try
                     ZeroMemory(@VerifyParams,SizeOf(CRYPT_VERIFY_MESSAGE_PARA));
                     VerifyParams.cbSize:= sizeof(CRYPT_VERIFY_MESSAGE_PARA);
                     VerifyParams.dwMsgAndCertEncodingType:= X509_ASN_ENCODING or PKCS_7_ASN_ENCODING;
                     VerifyParams.hCryptProv := context;
                     VerifyParams.pfnGetSignerCertificate:= @MyGetSignerCertificateCallback;
                     VerifyParams.pvGetArg := pContext;
                     SetLength(MessageArray, 1);
                     SetLength(MessageSize, 1);
                     MessageArray[0] := Pointer(str);
                     MessageSize[0] := strlen(str);
                     r := CryptVerifyDetachedMessageSignature(
                        @VerifyParams,
                        0,
                        psv,
                        csv,
                        1,
                        Pointer(MessageArray),
                        Pointer(MessageSize),
                        nil);
                  finally
                     FreeMem(psv);
                  end;
               end;
            finally
               CryptReleaseContext(context, 0);
            end;
         finally
            FreeMem(pX509cert);
         end;
      end;
      Result := VariantAsPyObject(r);
      //Py_IncRef(Result);
   end;
end;

function crypto_get_lasterror( self, args : PPyObject ) : PPyObject; cdecl;
begin
   with GetPythonEngine do begin
      Result := VariantAsPyObject(LastError());
      //Py_IncRef(Result);
   end;
end;

function crypto_show_certificate_info( self, args : PPyObject ) : PPyObject; cdecl;
const
  ViewCertTitle = 'Информация о сертификате отправителя';
var
   X509cert, sv : PChar;
   pX509cert, psv, tmpBuf : PBYTE;
   cX509cert, csv : DWORD;
   str : PChar;
   context: HCRYPTPROV;
   pContext : PCCERT_CONTEXT;
   wnd : HWND;
   gost_2012, prov_type: integer;
   {$IFDEF NOCRYPTBINARY}
   cryptview: TCryptUIViewCertificateStruct;
   PropertiesChanged: bool;
   {$ENDIF NOCRYPTBINARY}
begin
   LastErrorMessage := '';
   with GetPythonEngine do begin
      wnd := 0;
      PyArg_ParseTuple( args, 'si|i', @X509cert, @wnd, @gost_2012);
      pX509cert := crypto_string_to_binary(X509cert, cX509cert);
      if pX509cert <> nil then try
         if gost_2012 = 1 then
            prov_type := PROV_GOST_2012_256
         else
            prov_type := PROV_GOST_2001_DH;
         if CryptAcquireContext(context, nil, nil, prov_type, CRYPT_VERIFYCONTEXT) then try
            pContext := CertCreateCertificateContext(get_encoding, pX509cert, cX509cert);
            if pContext <> nil then try
               {$IFDEF NOCRYPTBINARY}
               ZeroMemory(@cryptview, SizeOf(TCryptUIViewCertificateStruct));
               cryptview.dwSize           := SizeOf(TCryptUIViewCertificateStruct);
               cryptview.hwndParent       := wnd;
               cryptview.dwFlags          := CRYPTUI_DISABLE_ADDTOSTORE;
               cryptview.szTitle          := ViewCertTitle;
               cryptview.pCertContext     := pContext;
               CryptUIDlgViewCertificate(@cryptview, PropertiesChanged);
               {$ELSE}
               CryptUIDlgViewContext(
                  CERT_STORE_CERTIFICATE_CONTEXT,
                  pContext,
                  wnd,
                  ViewCertTitle, // 'Информация о сертификате отправителя',
                  0,
                  nil
                                    );
               {$ENDIF NOCRYPTBINARY}
            finally
               CertFreeCertificateContext(pContext);
            end;
         finally
            CryptReleaseContext(context, 0);
         end;
      finally
         FreeMem(pX509cert);
      end;
      Result := ReturnNone;
   end;
end;

procedure StrToList(Str, Sep : string; List : Tstrings);
var
   index : Integer;
begin
   list.clear;
   if str <> emptystr then begin
      index := pos(sep, str);
      while index > 0 do begin
         list.add(copy(str, 1, index - 1));
         str := copy(str, index + length(sep), maxint);
         index := pos(sep, str);
      end;
      list.add(str);
   end;
end;


function extract_name_fields(pName : PCERT_NAME_BLOB) : TStrings;
var
   cIssuerName : DWORD;
   pIssuerName : PChar;   
begin
   Result := TStringList.Create;
   cIssuerName := 2048;
   pIssuerName := AllocMem(cIssuerName);
   try
      CertNameToStr(X509_ASN_ENCODING,
                    pName,
                    CERT_X500_NAME_STR,
                    pIssuerName,
                    cIssuerName
                   );
      StrToList(StrPas(pIssuerName), ', ', Result);
   finally
      FreeMem(pIssuerName);
   end;
end;

procedure append_to_dict(d : PPyObject; list : TStrings; const aname : string; const FreeList : boolean = True);
var
   i : Integer;
begin
   with GetPythonEngine do
   for i := 0 to pred(list.count) do
      PyDict_SetItemString(
         d,
         PChar(Format('%s_%s', [aname, List.Names[i]])),
         VariantAsPyObject(List.Values[List.Names[i]]));
   if FreeList then
      list.Free;
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

function crypto_get_certificate_info( self, args : PPyObject ) : PPyObject; cdecl;
var
   obj : PPyObject;
   pHash : PChar;
   wsCertName : WideString;
   hStore : HCERTSTORE;
   pContext : PCCERT_CONTEXT;
begin
   with GetPythonEngine do begin
      pHash := nil;
      wsCertName := '';
      obj := nil;
      PyArg_ParseTuple( args, '|Os', @obj, @pHash );
      if (obj <> nil) and (obj <> Py_None) then
         wsCertName := PyObjectAsVariant(obj);
      Result := PyDict_New();
      if (wsCertName = EmptyStr)
         and ((pHash = nil) or (strlen(pHash) = 0))
      then
         Exit;
      hStore := CertOpenSystemStore(0, 'MY');
      if hStore <> nil then try
         pContext := find_certificate(hStore, PWideChar(wsCertName), pHash);
         if pContext <> nil then try
            append_to_dict(Result, extract_name_fields(@pContext^.pCertInfo^.Issuer), 'ISSUER');
            append_to_dict(Result, extract_name_fields(@pContext^.pCertInfo^.Subject), 'SUBJECT');
            PyDict_SetItemString(
                      Result,
                      'NOTBEFORE',
                      VariantAsPyObject(FileTimeToDateTime(Windows._FILETIME(pContext^.pCertInfo^.NotBefore))));
            PyDict_SetItemString(
                      Result,
                      'NOTAFTER',
                      VariantAsPyObject(FileTimeToDateTime(Windows._FILETIME(pContext^.pCertInfo^.NotAfter))));
            PyDict_SetItemString(
                      Result,
                      'SERIAL',
                      PyString_FromStringAndSize(PChar(pContext^.pCertInfo^.SerialNumber.pbData), pContext^.pCertInfo^.SerialNumber.cbData));
            PyDict_SetItemString(
                      Result,
                      'SIGN_ALG',
                      PyString_FromString(pContext^.pCertInfo^.SignatureAlgorithm.pszObjId));
         finally
            CertFreeCertificateContext(pContext);
         end;
      finally
         CertCloseStore(hStore, 0);
      end;
   end;
end;

const
   CRYPT_ACQUIRE_SILENT_FLAG = $40;

// проверяет наличие доступного ключа для сертификата
function crypto_check_personal_key(self, args : PPyObject) : PPyObject; cdecl;
var
   obj : PPyObject;
   pHash : PChar;
   wsCertName : WideString;

   hStore : HCERTSTORE;
   pContext : PCCERT_CONTEXT;

   hProv : HCRYPTPROV;
   CallerFreeProv : BOOL;
   dwKeySpec : DWORD;
   r : boolean;
   
   use_gui : PPyObject;
   dwFlags : DWORD;

begin
   r := False;
   with GetPythonEngine do begin
      pHash := nil;
      wsCertName := '';
      obj := nil;
      use_gui := nil;
      PyArg_ParseTuple( args, 'Os|O', @obj, @pHash, @use_gui );
      if obj <> nil then
         wsCertName := PyObjectAsVariant(obj);
      
      dwFlags := 0;
      if (use_gui = nil) or (PyObject_IsTrue(use_gui) <> 1) then
         dwFlags := CRYPT_ACQUIRE_SILENT_FLAG;

      hStore := CertOpenSystemStore(0, 'MY');
      if hStore <> nil then try
         pContext := find_certificate(hStore, PWideChar(wsCertName), pHash);
         if pContext <> nil then try
            CallerFreeProv := False;
            try
               dwKeySpec := AT_SIGNATURE;
               r := CryptAcquireCertificatePrivateKey(
                                 pContext,
                                 dwFlags,
                                 nil,
                                 hProv,
                                 @dwKeySpec,
                                 @CallerFreeProv);
            finally
                if CallerFreeProv and (hProv <> 0) then
                   CryptReleaseContext(hProv, 0);
            end;
         finally
            CertFreeCertificateContext(pContext);
         end;
      finally
         CertCloseStore(hStore, 0);
      end;

      Result := VariantAsPyObject(r);

   end;
end;

function crypto_getlasterror(self, args : PPyObject) : PPyObject; cdecl;
begin
   with GetPythonEngine do begin
      Result := PyInt_FromLong(GetLastError())
   end;
end;


procedure init_func;
begin

   AddMethod(
      'get_certificate',
      crypto_get_certificate,
      'get_certificate(certname, certhash = '') -> string. ' +
         'Gets certificate CRYPT_STRING_BASE64 encoded for X509certificate node.' +
         'if certhash exists - searching by hash');

   AddMethod(
      'select_certificate',
      crypto_select_certificate,
      'select_certificate(hashreturn = 0) -> string. select certificate from MY store.' +
            'if hashreturn = 1 then returns sertificate sha1 hash else return subject name.');

   AddMethod(
      'get_digestvalue',
      crypto_get_digestvalue,
      'get_digestvalue(string, gost_2012:integer) -> string. Calculates value for DigestValue node');
      
   AddMethod(
      'get_password_hash',
      crypto_get_password_hash,
      'get_password_hash(string) -> string. Calculates password hash (SHA algorithm)');

   AddMethod(
      'get_sign_message',
      crypto_get_sign_message,
      'get_sign_message(str, certname, revert_buffer, pHash, gost_2012) -> string. Calculates digital sign for SignatureValue node');
      
   AddMethod(
      'get_sign_message_mps',
      crypto_get_sign_message_mps,
      'get_sign(string) -> string. Calculates digital sign for SignatureValue node');
      
   AddMethod(
      'verify_sign_message',
      crypto_verify_sign_message,
      'verify_sign_message(X509cert, SignatureValue, string, verify_sign=True, gost_2012=False) -> boolean. Verify digital sign.');
      
   AddMethod(
      'get_lasterror',
      crypto_get_lasterror,
      'get_lasterror()->error');

   AddMethod(
      'show_certificate_info',
      crypto_show_certificate_info,
      'show_certificate_info( X509cert, hwnd, gost_2012=False) -> None. shows certificate info.');

   AddMethod(
      'get_certificate_info',
      crypto_get_certificate_info,
      'get_certificate_info(certname, certhash = '') -> dict.' +
         'returns certificate info ISSUER CN and O, SUBJECT CN and O and NotBefore, NotAfter in delphi TDateTime format');
   AddMethod(
      'check_personal_key',
      crypto_check_personal_key,
      'check_personal_key(cert_name, cert_hash, use_gui = False) -> bool or None. check personal key existance.');
   
   AddMethod(
      'getlasterror',
      crypto_getlasterror,
      'getlasterror() -> Int. returns winapi last error code');
   
   

end;

initialization

finalization

end.

