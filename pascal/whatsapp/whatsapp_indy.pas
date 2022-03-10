unit whatsapp_indy;

interface

uses ceflib, IdHTTP, classes, IdSSLOpenSSL;

procedure indy_request(const url : WideString; const method : string; postdata : ICefV8Value; callbacks : ICefV8Value; context : ICefV8Context);

implementation

uses whatsapp_value;

procedure indy_request(const url : WideString; const method : string; postdata : ICefV8Value; callbacks : ICefV8Value; context : ICefV8Context);
var
    data : TStrings;
    keys : TStrings;
    key : string;
    v : ICefv8Value;
    s : ustring;
    m : TMemoryStream;
    result : ICefv8Value;
    args: TCefv8ValueArray;

    IdHTTP1 : TIdHTTP;
    IdSSLIOHandlerSocketOpenSSL1 : TIdSSLIOHandlerSocketOpenSSL;

    i : Integer;

begin
    IdHTTP1 := TIdHTTP.Create(nil);
    try

        IdHTTP1.HTTPOptions := IdHTTP1.HTTPOptions + [hoNoProtocolErrorException];

        IdSSLIOHandlerSocketOpenSSL1 := TIdSSLIOHandlerSocketOpenSSL.Create(nil);

        try

            data := TStringList.Create;
            m := TMemoryStream.Create;
            try
                keys := TStringList.Create;
                try
                    postdata.GetKeys(keys);
                    for i := 0 to keys.count - 1 do begin
                        key := keys[i];
                        v := postdata.GetValueByKey(key);
                        s := valuetostring(v);
                        data.Values[key] := s;
                    end;
                finally
                    keys.Free;
                end;
                IdHTTP1.IOHandler := IdSSLIOHandlerSocketOpenSSL1;
                if method = 'POST' then begin
                    IdHTTP1.Request.ContentType := 'application/x-www-form-urlencoded';
                    IdHTTP1.Post(url, data, m);
                end else begin
                    data.Delimiter := '&';
                    IdHTTP1.Get(url + '&' + data.DelimitedText, m);
                end;
                if CallBacks <> nil then begin
                    result := TCefv8ValueRef.NewObject(nil);
                    result.SetValueByKey('code', TCefv8ValueRef.NewInt(IdHTTP1.ResponseCode), []);
                    result.SetValueByKey('status', TCefv8ValueRef.NewString(IdHTTP1.ResponseText), []);
                    if CallBacks.HasValueByKey('always') then begin
                         SetLength(args, 1);
                         args[0] := result;
                         CallBacks.GetValueByKey('always').ExecuteFunctionWithContext(context, nil, args);
                    end;
                end;
            finally
                data.Free;
                m.Free;
            end;

        finally
            IdSSLIOHandlerSocketOpenSSL1.Free;
        end;

    finally
        IdHTTP1.Free;
    end
end;

end.
