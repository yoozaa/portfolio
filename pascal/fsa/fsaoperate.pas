unit fsaoperate;

interface

uses c4d_intf, tks_javascript, uCEFInterfaces, WideStrings, c4d_resourcehandler, classes, uCEFTypes, ActiveX, fsaintf;

type

    TFSACallback = class(TInterfacedObject, ITKSCEFCallback, ITKSCEFCallback2, ITKSCEFRequest)
    private
        FScriptList : TWideStrings;
        FMemoryStream : TMemoryStream;
        FLoading : boolean;
        FDone : IFSADone;
        Fdata : WideString;
        Fmode : Integer;
        FSelectMode : boolean;
    private
        procedure ServiceUnavailable(window : ITKSCEFWindow);
    protected
        function QueryInterface(const IID: TGUID; out Obj): HResult; stdcall;
        function get_data() : WideString; virtual;
    public
        // ITKSCEFCallback
        procedure OnDialog(const window : ITKSCEFWindow; const browser: ICefBrowser; const originUrl: WideString;
                           const dialogType: Integer; const messageText,  defaultPromptText: WideString;
                           const callback: ICefJsDialogCallback;  out suppressMessage, Result: Boolean); virtual; stdcall;
        procedure OnLoadEnd(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame; httpStatusCode: Integer); virtual; stdcall;
        procedure OnLoadError(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame; errorCode: Integer; const errorText, failedUrl: WideString); virtual; stdcall;
        function get_id : Integer; virtual; stdcall;
        procedure OnProcessMessageReceived(const window : ITKSCEFWindow;
                           const browser: ICefBrowser; sourceProcess: Integer;
                           const message: ICefProcessMessage; out Result: Boolean); virtual; stdcall;
        // ITLSCEFCallback2
        procedure OnGetResourceHandler(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame;
                           const request: ICefRequest; out Result: ICefResourceHandler); virtual; stdcall;
        // ITKSCEFRequestDone
        procedure RequestPrepare(const window : ITKSCEFWindow; const browser: ICefBrowser;
          const frame: ICefFrame; const request: ICefRequest); virtual; stdcall;
        procedure RequestDone(const window : ITKSCEFWindow; const browser: ICefBrowser;
          const frame: ICefFrame; const request: ICefRequest;
          const response: ICefResponse; const Data : IStream); virtual; stdcall;
    public
        constructor CreateWith(const done : IFSADone = nil); virtual;
        constructor CreateWithData(const done : IFSADone; const data  : WideString; const mode : Integer); virtual;
        destructor Destroy; override;
    public
        procedure AfterPageLoad(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame); virtual;
        procedure DoAddScripts(const root : WideString; const List : TWideStrings); virtual;
        function GetResourceURL : WideString; virtual;
        function GetDataURL(const request: ICefRequest) : WideString; virtual;
        procedure DoReady(const window : ITKSCEFWindow;
                   const browser: ICefBrowser); virtual;
    end;

    TRDSCallback = class(TFSACallback)
    public
        procedure DoAddScripts(const root : WideString; const List : TWideStrings); override;
        function GetResourceURL : WideString; override;
        function GetDataURL(const request: ICefRequest) : WideString; override;
    end;

    TRSSCallback = class(TFSACallback)
    public
        procedure DoAddScripts(const root : WideString; const List : TWideStrings); override;
        function GetResourceURL : WideString; override;
        function GetDataURL(const request: ICefRequest) : WideString; override;
    end;

    TRDSCheckCallback = class(TRDSCallback)
    public
        constructor CreateWith(const done : IFSADone = nil); override;
    public
        procedure DoReady(const window : ITKSCEFWindow;
                   const browser: ICefBrowser); override;
    end;

    TRSSCheckCallback = class(TRSSCallback)
    public
        constructor CreateWith(const done : IFSADone = nil); override;
    public
        procedure DoReady(const window : ITKSCEFWindow;
                   const browser: ICefBrowser); override;
    end;

implementation

uses SysUtils, Forms, c4d_xmlrequest, AxCtrls, uCEFv8Value, uCEFv8Context, Variants, c4d_consts, tkscom, tks_TLB, windows;

{ TFSACallback }

constructor TFSACallback.CreateWith(const done : IFSADone = nil);
var
   p : WideString;
begin
    Inherited;
    FScriptList := TWideStringList.Create;
    FMemoryStream := TMemoryStream.Create;
    FLoading := False;
    FDone := done;
    FData := '';
    FMode := 0;
    FSelectMode := True;
    p := ExtractFilePath(Application.Exename);
    DoAddScripts(p, FScriptList);
end;

constructor TFSACallback.CreateWithData(const done : IFSADone; const data  : WideString; const mode : Integer);
begin
    CreateWith(done);
    FData := Data;
    FMode := mode;
end;

destructor TFSACallback.Destroy;
begin
    FMemoryStream.Free;
    FScriptList.Free;
    FDone := nil;
    Inherited;
end;

procedure TFSACallback.AfterPageLoad(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame);
var
    i : Integer;
    script : string;
    filename : WideString;
begin
    for i := 0 to pred(FScriptList.Count) do begin
        filename := FScriptList.Strings[i];
        if FileExists(filename) then begin
            script := get_javascript_code(filename);
            frame.ExecuteJavaScript(script, '', 0);
        end;
    end;
end;

procedure TFSACallback.OnDialog(const window : ITKSCEFWindow; const browser: ICefBrowser; const originUrl: WideString;
                   const dialogType: Integer; const messageText,  defaultPromptText: WideString;
                   const callback: ICefJsDialogCallback;  out suppressMessage, Result: Boolean);
begin
    Result := False;
end;

function TFSACallback.get_data() : WideString;
begin
    result := fdata;
end;

procedure TFSACallback.OnLoadEnd(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame; httpStatusCode: Integer);
begin
    // Загрузить тут скрипты.
    if frame.Url <> 'about:blank' then begin
        if httpStatusCode = 200 then begin
            AfterPageLoad(window, browser, frame);
        end;
    end;
end;

procedure TFSACallback.OnLoadError(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame; errorCode: Integer; const errorText, failedUrl: WideString);
begin
    if FSelectMode then begin
        if (errorCode = 502) then
             ServiceUnavailable(window);
    end;
end;

function TFSACallback.get_id : Integer;
begin
    Result := 0;
end;

procedure TFSACallback.OnProcessMessageReceived(const window : ITKSCEFWindow;
                   const browser: ICefBrowser; sourceProcess: Integer;
                   const message: ICefProcessMessage; out Result: Boolean);
begin
    Result := True;
    if (message.Name = 'tks_fsa_done') and (FDone <> nil) then
        FDone.processing_result(message.ArgumentList.GetString(0), message.ArgumentList.GetBool(1))
    else if (message.Name = 'tks_fsa_ready') then
        DoReady(window, browser)
    else if (message.Name = 'tks_fsa_status') and (FDone <> nil) then
        FDone.status_changed(get_data(), message.ArgumentList.GetInt(0), message.ArgumentList.GetString(1), window)
    else
        Result := False;
end;

procedure TFSACallback.OnGetResourceHandler(const window : ITKSCEFWindow; const browser: ICefBrowser; const frame: ICefFrame;
                   const request: ICefRequest; out Result: ICefResourceHandler);
var
    r_url : WideString;
    data_url : WideString;
begin
    r_url := GetResourceURL;
    data_url := GetDataURL(request);
    if request.ResourceType = RT_XHR then begin
         if (r_url <> '') and (request.Url = r_url) then
              Result := TXmlHttpHandler.Create(browser, frame, 'XhrIntrcept', request, window, self)
         else if (data_url <> '') and (request.Url = data_url) then
              Result := TTKSCEFResourceHandler.Create(browser, frame, 'ccsdata', request, FMemoryStream, 'application/json');
    end;
end;

procedure TFSACallback.RequestPrepare(const window : ITKSCEFWindow; const browser: ICefBrowser;
  const frame: ICefFrame; const request: ICefRequest);
{
var
    IPostList: IInterfaceList;
    IPostElement: ICefPostDataElement;
    count : Integer;
    sBufStr: AnsiString;
    uBufLen,uSize: Cardinal;

    List : TStringList;

    icef3 : ITKSCEFWindow3;
    res, errorname, errormessage : WideString;
}
begin
    // modify request data hear.
    // ToDo: переписать
//    count := request.PostData.GetCount;
//    if count > 0 then begin
//        // Берем первый элемент (он у нас всего один)
//        IPostList := request.PostData.GetElements(1);
//        IPostElement := IPostList.Items[0] as ICefPostDataElement;
//        uSize := IPostElement.GetBytesCount;
//        SetString(sBufStr, nil, uSize);
//        uBufLen := IPostElement.GetBytes(uSize, Pointer(sBufStr));
//        List := TStringList.Create;
//        try
//            // ToDo: сделать модификацию PostData
//            // Вызывать тут javascript functions нельзя.
//            // Невозможно получить результат
//
//
////            if supports(window, ITKSCEFWindow3, icef3) then begin
////                if icef3.executeWithParams('tks_modify_request', VarArrayOf(['url', sBufStr]), res, errorname, errormessage) = S_OK then
////                    sBufStr := res;
////            end;
//            List.Text := sBufStr;
//            List.SaveToFile('d:\post.txt');
//        finally
//            List.Free;
//        end;
//    end;
end;

procedure TFSACallback.RequestDone( const window : ITKSCEFWindow;
  const browser: ICefBrowser;
  const frame: ICefFrame; const request: ICefRequest;
  const response: ICefResponse; const Data : IStream);
begin
    FLoading := False;
    FMemoryStream.LoadFromStream(TOleStream.Create(data));
    frame.ExecuteJavaScript(get_fire_event_script('ccs_data_fetch', GetDataURL(request)), '', 0);
end;

procedure TFSACallback.DoAddScripts(const root : WideString; const List : TWideStrings);
begin
    List.Add(WideFormat('%s\js\%s', [root, 'jquery-3.6.0.min.js']));
    List.Add(WideFormat('%s\js\%s', [root, 'bililiteRange.js']));
    List.Add(WideFormat('%s\js\%s', [root, 'jquery.sendkeys.js']));
    List.Add(WideFormat('%s\js\fsa\%s', [root, 'version.js']));
end;

function TFSACallback.GetResourceURL : WideString;
begin
    Result := '';
end;

function TFSACallback.GetDataURL(const request: ICefRequest) : WideString;
begin
    Result := '';
end;

procedure TFSACallback.DoReady(const window : ITKSCEFWindow;
                   const browser: ICefBrowser);
begin
    // nothing;
end;

function TFSACallback.QueryInterface(const IID: TGUID; out Obj): HResult;
begin
    if IsEqualGUID(IID, ITKSCEFConsole) and (FDone <> nil) then
        Result := FDone.QueryInterface(IID, Obj)
    else
        Result := Inherited QueryInterface(IID, Obj);
end;

procedure TFSACallback.ServiceUnavailable(window : ITKSCEFWindow);
var
   iresult : ITKSCEFResult;
begin
    (MainServer as ITKSDialogs).warning('Сервис недоступен');
    if supports(window, ITKSCEFResult, iresult) then
        iresult.set_result(idCancel, '[]');
end;

{ TRDSCallback }
procedure TRDSCallback.DoAddScripts(const root : WideString; const List : TWideStrings);
begin
    Inherited DoAddScripts(root, List);
    List.Add(WideFormat('%s\js\fsa\%s', [root, 'fsa.js']));
end;

function TRDSCallback.GetResourceURL : WideString;
begin
    Result := FSA_RDS_GET;
end;

function TRDSCallback.GetDataURL(const request: ICefRequest) : WideString;
begin
    Result := FSA_RDS_CCSGET;
end;


{ TRDSCheckCallback }

constructor TRDSCheckCallback.CreateWith(const done : IFSADone = nil);
begin
    Inherited CreateWith(done);
    FSelectMode := False;
end;

procedure TRDSCheckCallback.DoReady(const window : ITKSCEFWindow;
                   const browser: ICefBrowser);
var
    icef3 : ITKSCEFWindow3;
    res, errorname, errormessage : WideString;
begin
    if supports(window, ITKSCEFWindow3, icef3) then begin
        if FData <> '' then begin
            icef3.executeWithParams('tks_search_fsa_json', FData, False, res, ErrorName, ErrorMessage);
            // ToDo: сделать сообщение для возобновления поиска!!!
            FData := '';
        end;
    end;
end;

{ TRSSCallback }

procedure TRSSCallback.DoAddScripts(const root : WideString; const List : TWideStrings);
begin
    Inherited DoAddScripts(root, List);
    List.Add(WideFormat('%s\js\fsa\%s', [root, 'fsa.js']));
end;

function TRSSCallback.GetResourceURL : WideString;
begin
    Result := FSA_RSS_GET;
end;

function TRSSCallback.GetDataURL(const request: ICefRequest) : WideString;
begin
    Result := FSA_RSS_CCSGET;
end;

{ TRSSCheckCallback }

constructor TRSSCheckCallback.CreateWith(const done : IFSADone = nil);
begin
    Inherited CreateWith(done);
    FSelectMode := False;
end;

procedure TRSSCheckCallback.DoReady(const window : ITKSCEFWindow;
                   const browser: ICefBrowser);
var
    icef3 : ITKSCEFWindow3;
    res, errorname, errormessage : WideString;
begin
    if supports(window, ITKSCEFWindow3, icef3) then begin
        icef3.executeWithParams('tks_search_fsa_json', FData, False, res, ErrorName, ErrorMessage);
        // ToDo: сделать сообщение для возобновления поиска!!!
        FData := '';
    end;
end;


end.
