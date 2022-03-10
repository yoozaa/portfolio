unit fsaimpl;

interface

uses fsaintf, tkscom, tks_TLB, windows, c4d_intf, classes;

type

    TFSAManager = class(TTKSModule, IFSAManager, IFSADone)
    private
    private
        function create_callback(const windowtype : Integer) : ITKSCEFCallback;
        function create_callback_withData(const windowtype : Integer; const done : IFSADone; const data : WideString; const mode : Integer): ITKSCEFCallback;
    public
        procedure Initialize; override;
        function  InitModule : HResult; override; stdcall;
        destructor Destroy; override;
    public
        // IFSAManager
        function getWindow(const windowtype : Integer; out iwindow : ITKSWindow) : HResult; stdcall;
        function getWindowType(out windowtype : Integer): HResult; stdcall;
        function getUrl(const windowtype : Integer; out url : WideString): HResult; stdcall;
        function select(const windowtype : Integer; out json : WideString): HResult; stdcall;
        function check(const windowtype : Integer; const data : WideString; const mode : Integer; const done : IFSADone; var ifsa : IFSAWindow): HResult; stdcall;
        function get_check_manager(out manager : IFSACheckManager) : HResult; stdcall;
        // IFSADone
        procedure processing_result(const json : WideString; const has_more : boolean); stdcall;
        function status_changed(const json : WideString; const istatus : Integer; const sstatus : WideString; window : ITKSCEFWindow) : HResult; stdcall;
    end;

    TFSAWindow = class(TInterfacedObject, IFSAWindow)
    private
        FWindow : ITKSWindow;
    public
        // IFSAWindow
        procedure get_window(out iwindow : ITKSWindow); stdcall;
        procedure continue_search(const data : WideString); stdcall;
    public
        constructor CreateWith(const iwindow : ITKSWindow);
        destructor Destroy; override;
    end;

    TFSAData = class(TInterfacedObject, IFSAData)
    private
        fwindowtype : Integer;
        fdata : WideString;
    public
        constructor CreateWith(const windowtype : Integer; const data : WideString);
    public
        // IFSAData
        function get_window_type() : Integer; stdcall;
        function get_data() : WideString; stdcall;
    end;

    TFSACheckManager = class(TInterfacedObject, IFSACheckManager)
    private
        Fmanager : IFSAManager;
        FWindows : array [FSA_CHECK_LOW .. FSA_CHECK_HIGH] of IFSAWindow;
        FDatas : array [FSA_CHECK_LOW .. FSA_CHECK_HIGH] of TInterfaceList;
    public
        constructor CreateWith(const manager : IFSAManager);
        destructor Destroy; override;
    public
        // IFSACheckManager
        function append_data(const windowtype : Integer; const data : WideString) : HResult; stdcall;
        function check(const mode : Integer; const done : IFSADone) : HResult; stdcall;
    end;

implementation

uses tks_td_header, sysutils, ComServ, ComObj, fsaoperate;

{ TFSAData }

constructor TFSAData.CreateWith(const windowtype : Integer; const data : WideString);
begin
    Inherited Create;
    fwindowtype := windowtype;
    fdata := data;
end;

function TFSAData.get_window_type() : Integer;
begin
    Result := fwindowtype;
end;

function TFSAData.get_data() : WideString;
begin
    Result := fdata;
end;

{ TFSACheckManager }

constructor TFSACheckManager.CreateWith(const manager : IFSAManager);
var
    i : Integer;
begin
    Inherited Create;
    Fmanager := manager;
    for i := Low(FDatas) to High(FDatas) do
        FDatas[i] := TInterfaceList.Create;
    for i := Low(FWindows) to High(FWindows) do
        FWindows[i] := nil;
end;

destructor TFSACheckManager.Destroy;
var
    i : Integer;
begin
    FManager := nil;
    for i := Low(FDatas) to High(FDatas) do
        FDatas[i].Free;
    for i := Low(FWindows) to High(FWindows) do
        FWindows[i] := nil;
    Inherited Destroy;
end;

function TFSACheckManager.append_data(const windowtype : Integer; const data : WideString) : HResult;
begin
    FDatas[windowtype].Add(TFSAData.CreateWith(windowtype, data));
    Result := S_OK;
end;

function TFSACheckManager.check(const mode : Integer; const done : IFSADone) : HResult;
var
    i, j : Integer;
    idata : IFSAData;
begin
    for i := Low(FDatas) to High(FDatas) do
        for j := 0 to FDatas[i].Count - 1 do begin
            FDatas[i][j].QueryInterface(IFSAData, idata);
            FManager.check(idata.get_window_type, idata.get_data, FSA_SEARCH_ALL, done, FWindows[i]);
            break;
        end;
    Result := S_OK;
end;

{ TFSAWindow }

constructor TFSAWindow.CreateWith(const iwindow : ITKSWindow);
begin
    Inherited Create;
    FWindow := iwindow;
end;

destructor TFSAWindow.Destroy;
begin
    if (FWindow <> nil) then
        FWindow.CloseWindow;
    FWindow := nil;
    Inherited;
end;

procedure TFSAWindow.get_window(out iwindow : ITKSWindow);
begin
    iwindow := FWindow;
end;

procedure TFSAWindow.continue_search(const data : WideString);
begin
    // not yet implemented
end;

{ TFSAManager }

procedure TFSAManager.Initialize;
begin
    Inherited Initialize;
    ModuleName := 'Работа с реестрами СГР и ДС';
    Events := Events or EVT_STOPSERVER
        or EVT_CLOSETABLES
        or EVT_STOPPROCESSING
        or EVT_STARTPROCESSING
        or EVT_ACTIVETABLES
        or EVT_OPENTABLES
        or EVT_PYTHONINIT
        ;
end;

function TFSAManager.InitModule : HResult;
begin
    Result := inherited InitModule;
end;

destructor TFSAManager.Destroy;
begin
    Inherited;
end;

function TFSAManager.getWindow(const windowtype : Integer; out iwindow : ITKSWindow) : HResult;
var
   icef : ITKSCEFManager3;
   url : WideString;
begin
   Result := E_FAIL;
   if supports(MainServer, ITKSCEFManager3, icef) then begin
       if getUrl(windowtype, url) = S_OK then begin
           Result := icef.getincognitowindow(url, iwindow, create_callback(windowtype));
       end;
   end;
end;

function TFSAManager.getWindowType(out windowtype : Integer): HResult;
var
    IManager: ITaskDialogManager;
    iDialog : ITKSTaskDialog;
begin
    windowtype := FSA_DEFAULT;
    Result := S_OK;
    Exit;
    if Supports(MainServer, ITaskDialogManager, IManager) then begin
        if iManager.GetDialog(iDialog) = S_OK then begin
//            iDialog.SetDefaultButton(dwDefault);
//            iDialog.SetParent(dwParent);
//            if iDialog.Execute(dwType, wsMsg, dwButtons, dwDescripton) = S_OK then
                Result := iDialog.ModalResult;
        end;
    end;
end;

function TFSAManager.getUrl(const windowtype : Integer; out url : WideString): HResult;
begin
    Result := S_OK;
    case windowtype of
    FSA_RDS_DECLARATION, FSA_RDS_DECLARATION_CHECK:
        url := FSA_RDS_URL;
    FSA_RSS_CERTIFICATE, FSA_RSS_CERTIFICATE_CHECK:
        url := FSA_RSS_URL;
    else
         url := '';
         Result := E_FAIL;
    end;
end;

function TFSAManager.create_callback(const windowtype : Integer) : ITKSCEFCallback;
begin
    case windowtype of
    FSA_RDS_DECLARATION:
        Result := TRDSCallback.CreateWith(self);
    FSA_RSS_CERTIFICATE:
        Result := TRSSCallback.CreateWith(self);
    else
        Result := nil;
    end;
end;

function TFSAManager.create_callback_withData(const windowtype : Integer; const done : IFSADone; const data : WideString; const mode : Integer): ITKSCEFCallback;
begin
    case windowtype of
    FSA_RDS_DECLARATION_CHECK:
        Result := TRDSCheckCallback.CreateWithData(done, data, mode);
    FSA_RSS_CERTIFICATE_CHECK:
        Result := TRSSCheckCallback.CreateWithData(done, data, mode);
    else
        Result := nil;
    end;
end;

function TFSAManager.select(const windowtype : Integer; out json : WideString): HResult;
var
    url : WideString;
    icef : ITKSCEFManager2;
    r : Integer;
    savesection : WideString;
begin
    Result := E_FAIL;
    json := '';
    if supports(MainServer, ITKSCEFManager2, icef) then begin
        savesection := WideFormat('FSAWindow_%d', [windowtype]);
        if getUrl(windowtype, url) = S_OK then begin
            icef.showdialog(url, r, json, True, savesection, create_callback(windowtype));
            if r = idOK then
               Result := S_OK;
        end;
    end;
end;

function TFSAManager.check(const windowtype : Integer; const data : WideString; const mode : Integer; const done : IFSADone; var ifsa : IFSAWindow): HResult; stdcall;
var
    icef : ITKSCEFManager3;
    iwindow : ITKSWindow;
    url : WideString;
begin
    Result := E_FAIL;
    iwindow := nil;
    if supports(MainServer, ITKSCEFManager3, icef) then begin
        if getUrl(windowtype, url) = S_OK then begin
            icef.getincognitowindow(url, iwindow, create_callback_withData(windowtype, done, data, mode));
            ifsa := TFSAWindow.CreateWith(iwindow);
            Result := S_OK;
        end;
    end;
end;

function TFSAManager.get_check_manager(out manager : IFSACheckManager) : HResult;
begin
    manager := TFSACheckManager.CreateWith(self);
    Result := S_OK;
end;

procedure TFSAManager.processing_result(const json : WideString; const has_more : boolean);
begin
    // nothing
end;

function TFSAManager.status_changed(const json : WideString; const istatus : Integer; const sstatus : WideString; window : ITKSCEFWindow) : HResult;
var
   iresult : ITKSCEFResult;
begin
    if istatus = FSA_STATUS_UNAVAILABLE then begin
        (Server as ITKSDialogs).warning('Сервис недоступен');
        if supports(window, ITKSCEFResult, iresult) then
            iresult.set_result(idCancel, '[]');
    end;
    Result := S_OK;
end;


initialization

    TComObjectFactory.Create(ComServer, TFSAManager, CLASS_FSA_MANAGER, 'TFSAManager', 'TFSAManager', ciInternal, tmApartment);

end.
