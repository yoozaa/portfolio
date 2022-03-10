unit whatsapp_request_get;

interface

uses classes, uCEFUrlrequestClient, ucefinterfaces, uceftypes, uCEFv8Value, WideStrings, uCEFRequest, uCEFUrlRequest;

type

    TOnDataRequestDone = procedure (const code : Integer; const status : WideString; const data : WideString) of object;

    TWappDataRequestClient = class(TCefUrlRequestClientOwn)
    private
        FData : TMemoryStream;
        FRequestDone : TOnDataRequestDone;
    protected
        procedure OnRequestComplete(const request: ICefUrlRequest); override;
        procedure OnDownloadData(const request: ICefUrlRequest; data: Pointer; dataLength: NativeUInt); override;
    public
        constructor Create; override;
        destructor Destroy; override;
        constructor CreateWith(const RequestDone : TOnDataRequestDone);
    end;


function get_url_data(const url : WideString; const RequestDone : TOnDataRequestDone; const RequestContext : ICefRequestContext) : ICefUrlRequest;

implementation

function get_url_data(const url : WideString; const RequestDone : TOnDataRequestDone; const RequestContext : ICefRequestContext) : ICefUrlRequest;
var
    Request : ICefRequest;
    rstatus: TCefUrlRequestStatus;
begin
    Request := TCefRequestRef.New;
    Request.Url := url;
    Request.Method := 'GET';
    Result := TCefUrlRequestRef.New(Request, TWappDataRequestClient.CreateWith(RequestDone), nil);
    rstatus := Result.GetRequestStatus;
    if rstatus = UR_UNKNOWN then ;
end;

constructor TWappDataRequestClient.Create;
begin
    Inherited Create;
    FData := TMemoryStream.Create;
end;

destructor TWappDataRequestClient.Destroy;
begin
    FData.Free;
    Inherited;
end;

constructor TWappDataRequestClient.CreateWith(const RequestDone : TOnDataRequestDone);
begin
    Create;
    FRequestDone := RequestDone;
end;

procedure TWappDataRequestClient.OnDownloadData(const request: ICefUrlRequest; data: Pointer; dataLength: NativeUInt);
begin
    FData.Write(data, dataLength);
end;

procedure TWappDataRequestClient.OnRequestComplete(const request: ICefUrlRequest);
var
    list : TWideStringList;
begin
    if assigned(FRequestDone) then begin
        list := TWideStringList.Create;
        try
            FData.Position := 0;
            list.LoadFromStream(FData);
            FRequestDone(request.GetResponse.Status, request.GetResponse.StatusText, list.Text);
        finally
            list.Free;
        end;
    end;
end;

end.
