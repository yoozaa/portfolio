unit whatsapp_request;

interface

uses classes, uCEFUrlrequestClient, ucefinterfaces, uceftypes, uCEFv8Value;

type

    TWappUrlRequestClient = class(TCefUrlRequestClientOwn)
    private
        FCallbacks : ICefv8Value;
        fcontext : ICefV8Context;
    protected
        procedure OnRequestComplete(const request: ICefUrlRequest); override;
    public
        constructor CreateWithContext(context : ICefV8Context; Callbacks : ICefv8Value);
    end;


function create_post_request(const url : ustring; const postdata : ICefv8Value) : ICefRequest;

implementation

uses whatsapp_value, uCEFPostDataElement, uCEFRequest, uCEFStringMultimap, uCEFPostData;

function CreateField(const AValue: AnsiString): ICefPostDataElement;
begin
  Result := TCefPostDataElementRef.New;
  Result.SetToBytes(Length(AValue), PAnsiChar(AValue));
end;

function create_post_request(const url : ustring; const postdata : ICefv8Value) : ICefRequest;
var
    Header: ICefStringMultimap;
    i : Integer;
    keys : TStrings;
    key : string;
    v : ICefv8Value;
    s : ustring;
begin
    Result := TCefRequestRef.New;
    Result.Url := url;
    Result.Method := 'POST';
    // WUR_FLAG_NONE
    Result.Flags := 0;

    Header := TCefStringMultimapOwn.Create;
    Result.GetHeaderMap(Header);
    Header.Append('Content-Type', 'application/x-www-form-urlencoded');
    Result.SetHeaderMap(Header);

    Result.PostData := TCefPostDataRef.New;
    keys := TStringList.Create;
    try
        postdata.GetKeys(keys);
        for i := 0 to keys.count - 1 do begin
            key := keys[i];
            v := postdata.GetValueByKey(key);
            s := valuetostring(v);
            if i = 0 then
                Result.PostData.AddElement(CreateField(key + '=' + s))
            else
                Result.PostData.AddElement(CreateField('&' + key + '=' + s))
        end;
    finally
        keys.Free;
    end;

end;

constructor TWappUrlRequestClient.CreateWithContext(context : ICefV8Context; Callbacks : ICefv8Value);
begin
    Inherited Create;
    fcontext := context;
    fCallbacks := Callbacks;
end;

procedure TWappUrlRequestClient.OnRequestComplete(const request: ICefUrlRequest);
var
    result : ICefv8Value;
    args: TCefv8ValueArray;
begin
    if FCallBacks <> nil then begin
        result := TCefv8ValueRef.NewObject(nil, nil);
        result.SetValueByKey('status', TCefv8ValueRef.NewString(request.GetResponse.StatusText), 0);
        if FCallBacks.HasValueByKey('always') then begin
             SetLength(args, 1);
             args[0] := result;
             FCallBacks.GetValueByKey('always').ExecuteFunctionWithContext(fcontext, nil, args);
        end;
    end;
end;

end.
