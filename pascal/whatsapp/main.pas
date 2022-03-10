unit main;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, StdCtrls, Buttons, ActnList, Menus, ComCtrls,
  ExtCtrls, XPMan, Registry, ShellApi, SyncObjs, udform, whatsapp_clicker
  , pythonengine, tks_process, bigini, whatsapp_pythonthread, widestrutils,
  uCEFWindowParent, uCEFChromium, ucefinterfaces, uceftypes, uCEFRenderProcessHandler, uceftask, uCEFv8Value,
  uCEFChromiumCore, uCEFWinControl;


const
     CM_LOADDEFAULT = WM_USER + 1;
     CM_LOADSCRIPT = WM_USER + 2;
     CM_PASTE = WM_USER + 3;
     CM_IPADDR = WM_USER + 4;

const
  CEFBROWSER_CREATED          = WM_APP + $100;
  CEFBROWSER_CHILDDESTROYED   = WM_APP + $101;
  CEFBROWSER_DESTROY          = WM_APP + $102;

type

  TMainForm = class(TDForm)
    crm: TChromium;
    ActionList: TActionList;
    actReload: TAction;
    MainMenu: TMainMenu;
    est1: TMenuItem;
    actExecuteJS: TAction;
    Exit1: TMenuItem;
    actDom: TAction;
    SaveDialog: TSaveDialog;
    actDevTool: TAction;
    DevelopperTools1: TMenuItem;
    actDoc: TAction;
    actGroup: TAction;
    actFileScheme: TAction;
    actPrint: TAction;
    Splitter: TSplitter;
    Clicker1: TMenuItem;
    StartItem: TMenuItem;
    StopItem: TMenuItem;
    N5: TMenuItem;
    reload1: TMenuItem;
    Reload21: TMenuItem;
    N6: TMenuItem;
    N7: TMenuItem;
    JsTimer: TTimer;
    Sendselected1: TMenuItem;
    ChromeWindow: TCEFWindowParent;
    DevToolsWindow: TCEFWindowParent;
    ReloadTimer: TTimer;
    procedure FormCreate(Sender: TObject);
    procedure Exit1Click(Sender: TObject);
    procedure crmLoadEnd(Sender: TObject; const browser: ICefBrowser;
      const frame: ICefFrame; httpStatusCode: Integer);
    procedure crmLoadStart(Sender: TObject; const browser: ICefBrowser;
      const frame: ICefFrame);
    procedure crmTitleChange(Sender: TObject; const browser: ICefBrowser;
      const title: ustring);
    procedure actDevToolExecute(Sender: TObject);
    procedure FormCloseQuery(Sender: TObject; var CanClose: Boolean);
    procedure crmBeforeDownload(Sender: TObject; const browser: ICefBrowser;
      const downloadItem: ICefDownloadItem; const suggestedName: ustring;
      const callback: ICefBeforeDownloadCallback);

    procedure actPrintExecute(Sender: TObject);
    procedure crmBeforeContextMenu(Sender: TObject; const browser: ICefBrowser;
      const frame: ICefFrame; const params: ICefContextMenuParams;
      const model: ICefMenuModel);
    procedure crmContextMenuCommand(Sender: TObject; const browser: ICefBrowser;
      const frame: ICefFrame; const params: ICefContextMenuParams;
      commandId: Integer; eventFlags: TCefEventFlags; out Result: Boolean);
    procedure crmCertificateError(Sender: TObject; const browser: ICefBrowser;
      certError: Integer; const requestUrl: ustring; const sslInfo: ICefSslInfo;
      const callback: ICefRequestCallback; out Result: Boolean);
    procedure crmFavIconUrlChange(Sender: TObject;
      const browser: ICefBrowser; const iconUrls: TStrings);
    procedure StartItemClick(Sender: TObject);
    procedure StopItemClick(Sender: TObject);
    procedure reload1Click(Sender: TObject);
    procedure reload2Click(Sender: TObject);
    procedure crmAfterCreated(Sender: TObject; const browser: ICefBrowser);
    procedure aboutblank1Click(Sender: TObject);
    procedure N7Click(Sender: TObject);
    procedure JsTimerTimer(Sender: TObject);
    procedure crmJsdialog(Sender: TObject; const browser: ICefBrowser;
      const originUrl: ustring; dialogType: TCefJsDialogType;
      const messageText, defaultPromptText: ustring;
      callback: ICefJsDialogCallback; out suppressMessage,
      Result: Boolean);
    procedure crmBeforeUnloadDialog(Sender: TObject;
      const browser: ICefBrowser; const messageText: ustring;
      isReload: Boolean; const callback: ICefJsDialogCallback;
      out Result: Boolean);
    procedure ShowHIDItem1Click(Sender: TObject);
    procedure Sendselected1Click(Sender: TObject);
    procedure crmLoadingStateChange(Sender: TObject;
      const browser: ICefBrowser; isLoading, canGoBack,
      canGoForward: Boolean);
    procedure crmLoadError(Sender: TObject; const browser: ICefBrowser;
      const frame: ICefFrame; errorCode: Integer; const errorText,
      failedUrl: ustring);
    procedure FormShow(Sender: TObject);
    procedure crmBeforeClose(Sender: TObject; const browser: ICefBrowser);
    procedure FormKeyDown(Sender: TObject; var Key: Word;
      Shift: TShiftState);
    procedure ReloadTimerTimer(Sender: TObject);
    procedure crmClose(Sender: TObject; const browser: ICefBrowser;
      var aAction: TCefCloseBrowserAction);
    procedure crmFileDialog(Sender: TObject; const browser: ICefBrowser;
      mode: Cardinal; const title, defaultFilePath: ustring;
      const acceptFilters: TStrings; selectedAcceptFilter: Integer;
      const callback: ICefFileDialogCallback; out Result: Boolean);
  private
    { D�clarations priv�es }
    FLoading: Boolean;
    fmanager : Variant;
    IClicker : IWAppClicker;
    FRunning : boolean;
    pythread : TWappPythonThread;
    Fopenfilename : WideString;
    FCanClose : boolean;
    FClosing  : boolean;
    fUrlRequest: ICefUrlRequest;
    rstatus: TCefUrlRequestStatus;
    FErrorCount : Integer;
    function IsMain(const b: ICefBrowser; const f: ICefFrame = nil): Boolean;
    function GetRunning : boolean;
    procedure SetRunning(value : boolean);
    procedure EnterMainThread;
    procedure LeaveMainThread;
    procedure cmloaddefault(var msg : TMessage); message CM_LOADDEFAULT;
    procedure SyncMessage(var mes : TMessage); message WM_SYNC_MESSAGE;
    procedure cmloadscript(var msg : TMessage); message CM_LOADSCRIPT;
    procedure cmpaste(var msg : TMessage); message CM_PASTE;
    procedure process_sync_message(const vid : Integer);
    procedure BrowserDestroyMsg(var aMessage : TMessage); message CEFBROWSER_DESTROY;
  public
    procedure AfterInitPython(Sender : TObject);
    procedure InitPythonThread;
    procedure DeinitPythonThread;
    procedure AddJob(data : IWAppJobInfo; cb : ICefv8Value);
    function read_gateway(const filename : string; const defvalue: string): string;
    function read_intersleep(const filename : string; const defvalue: real): real;
    function read_helpdesk(const filename : string; const defvalue: string): string;
    procedure read_settings(const filename : string);
    procedure read_AuthCredentials(const filename : string);
    procedure CloseWindow;
    procedure DeinitStuff;
  public
    property manager : Variant read fmanager;
    property running : boolean read FRunning write SetRunning;
  end;

  TCustomRenderProcessHandler = class //(TCefRenderProcessHandlerOwn)
  public
    class procedure OnWebKitInitialized; // override;
    class procedure OnContextCreated(const browser: ICefBrowser;
      const frame: ICefFrame; const context: ICefv8Context); // override;
    class procedure OnContextReleased(const browser: ICefBrowser;
      const frame: ICefFrame; const context: ICefv8Context); // override;
  end;

  TInitPyThreadTask = class(TCefTaskOwn)
  protected
    procedure Execute; override;
  end;

  TDeInitPyThreadTask = class(TCefTaskOwn)
  protected
    procedure Execute; override;
  end;

  TAddJobTask = class(TCefTaskOwn)
  private
    FData : IWappJobInfo;
    FCallBack : ICefv8Value;
  protected
    procedure Execute; override;
  public
    constructor CreateWith(data : IWappJobInfo; callback : ICefv8Value);
    destructor Destroy; override;
  end;

var
  MainForm: TMainForm;
  hwindow : HWND = 0;
  gcontext : ICefV8Context = nil;
  stopping : boolean = False;
  OwnThreadState: PPyThreadState = nil;
  w : ICefv8Value = nil;

implementation

uses whatsapp_user, widestrings, whatsapp_value, varpyth,
  pyDecl, whatsapp_tools, whatsapp_request, whatsapp_crypto, whatsapp_code,
  strutils, ucefapplication, uCEFv8Handler, uCEFMiscFunctions, uCEFBrowserProcessHandler
  , uCEFConstants, whatsapp_request_get;

const

  CUSTOMMENUCOMMAND_INSPECTELEMENT = 7241221;
  USER_JS_FILENAME = 'js\whatsapp-web.user.js';
  USER_JS_JQUERY = 'js\jquery.min.js';
  GLOBAL_JS_SETTINGS = 'js\settings.js';
  DEBUG_JS_FILENAME = 'js\vlad.js';
  W_PASSWORD = 'vlad';


{$R *.dfm}
{$I whatsapp-web.user.inc}

function startprocess(const paramvalue : string = 'AUTO'): boolean;
var
    i : Integer;
begin
    Result := False;
    for i := 1 to ParamCount do
        if AnsiUpperCase(ParamStr(i)) = paramvalue then begin
            Result := True;
            Exit;
        end;
end;

function ep() : WideString;
begin
    Result := WideFormat('w("%s")', [W_PASSWORD]);
end;

procedure TMainForm.aboutblank1Click(Sender: TObject);
begin
  inherited;
  crm.LoadURL('about:blank');
end;

procedure TMainForm.actDevToolExecute(Sender: TObject);
begin
  if actDevTool.Checked then
  begin
      DevToolsWindow.Visible := True;
      Splitter.Visible := True;
      crm.ShowDevTools(Point(0, 0), DevToolsWindow);
  end else
  begin
    crm.CloseDevTools(DevToolsWindow);
    Splitter.Visible := False;
    DevToolsWindow.Visible := False;
  end;
end;

procedure TMainForm.actPrintExecute(Sender: TObject);
begin
  crm.Browser.Host.Print;
end;

function TMainForm.IsMain(const b: ICefBrowser; const f: ICefFrame): Boolean;
begin
  Result := (b <> nil) and (b.Identifier = crm.BrowserId) and ((f = nil) or (f.IsMain));
end;

procedure TMainForm.JsTimerTimer(Sender: TObject);
var
   e, cmd : WideString;
begin
  inherited;
  e := ep();
  cmd := WideFormat('if (!%s)%s', [e, '{alert(''$%$|initscript'')};']);
  crm.Browser.MainFrame.ExecuteJavaScript(cmd, '', 0);
  jsTimer.Interval := 1000 * 60 * 10;
end;

procedure TMainForm.N7Click(Sender: TObject);
var
    cmd : WideString;
begin
  inherited;
  cmd := WideFormat('%s.sendNewMessages();', [ep()]);
  crm.Browser.mainframe.ExecuteJavaScript(cmd, '', 0);
end;

procedure TMainForm.reload1Click(Sender: TObject);
begin
  inherited;
  crm.Browser.Reload;
end;

procedure TMainForm.reload2Click(Sender: TObject);
begin
  inherited;
  // if fmanager <> Null then begin
  //   showmessage(fmanager);
  //   crm.Browser.mainframe.ExecuteJavaScript('alert("dddddd222");', '', 0);
  // end;
  // crm.Browser.mainframe.ExecuteJavaScript('alert("dddddd111");', '', 0);
end;

procedure TMainForm.ReloadTimerTimer(Sender: TObject);
begin
  inherited;
  PostMessage(Handle, CM_LOADDEFAULT, 0, 0);
  ReloadTimer.Enabled := False;
end;

procedure TMainForm.crmAfterCreated(Sender: TObject;
  const browser: ICefBrowser);
const
    washear : boolean = False;
begin
    Inherited;
    if not washear then begin
        washear := True;
        SendMessage(Handle, CM_IPADDR, 0, Integer(PAnsiChar('N/A')));
        PostMessage(ChromeWindow.Handle, WM_SIZE, 0, 0);
        PostMessage(Handle, CM_LOADDEFAULT, 0, 0);
    end;
end;

procedure TMainForm.crmBeforeClose(Sender: TObject;
  const browser: ICefBrowser);
begin
    inherited;
    //CloseWindow;
end;

procedure TMainForm.DeinitStuff;
begin
    fUrlRequest := nil;
    JsTimer.Enabled := False;
    try
        running := False;
    except
    end;
    DeinitPythonThread;
    EnterMainThread;
    fmanager := Null;
end;

procedure TMainForm.CloseWindow;
begin
    FCanClose := True;
    PostMessage(Handle, WM_CLOSE, 0, 0);
end;

procedure TMainForm.crmBeforeContextMenu(Sender: TObject;
  const browser: ICefBrowser; const frame: ICefFrame;
  const params: ICefContextMenuParams; const model: ICefMenuModel);
begin
  model.AddItem(CUSTOMMENUCOMMAND_INSPECTELEMENT, 'Inspect Element');
end;

procedure TMainForm.crmBeforeDownload(Sender: TObject;
  const browser: ICefBrowser; const downloadItem: ICefDownloadItem;
  const suggestedName: ustring; const callback: ICefBeforeDownloadCallback);
var
   filename: WideString;
   save_filename: WideString;
begin
  filename := WideStringReplace(suggestedName, '"', '''', []);
  browser.MainFrame.ExecuteJavaScript(WideFormat(WideFormat('%s.documentinfo%s', [ep(), '.set_current_url("%s", "%s")']), [downloadItem.geturl(), filename]), '', 0);
  save_filename := ExtractFilePath(ParamStr(0)) + 'users\' + WAPP_USERNAME + '\wa_storage\' + suggestedName;
  callback.Cont(save_filename, False);
end;

procedure TMainForm.crmBeforeUnloadDialog(Sender: TObject;
  const browser: ICefBrowser; const messageText: ustring;
  isReload: Boolean; const callback: ICefJsDialogCallback;
  out Result: Boolean);
begin
  inherited;
  Result := True;
  callback.Cont(True, '');
end;

procedure TMainForm.crmCertificateError(Sender: TObject;
  const browser: ICefBrowser; certError: Integer; const requestUrl: ustring;
  const sslInfo: ICefSslInfo; const callback: ICefRequestCallback;
  out Result: Boolean);
begin
  callback.Cont(True);
  Result := True;
end;

procedure TMainForm.crmClose(Sender: TObject; const browser: ICefBrowser;
  var aAction: TCefCloseBrowserAction);
begin
  inherited;
  PostMessage(Handle, CEFBROWSER_DESTROY, 0, 0);
  aAction := cbaDelay;
end;

procedure TMainForm.crmContextMenuCommand(Sender: TObject;
  const browser: ICefBrowser; const frame: ICefFrame;
  const params: ICefContextMenuParams; commandId: Integer;
  eventFlags: TCefEventFlags; out Result: Boolean);
var
  mousePoint: TCefPoint;
begin
  Result := False;
  if (commandId = CUSTOMMENUCOMMAND_INSPECTELEMENT) then
  begin
    mousePoint.x := params.XCoord;
    mousePoint.y := params.YCoord;
    Splitter.Visible := True;
    DevToolsWindow.Visible := True;
    actDevTool.Checked := True;
    crm.CloseDevTools(DevToolsWindow);
    application.ProcessMessages;
    crm.ShowDevTools(Point(0, 0), DevToolsWindow);
    Result := True;
  end;
end;

procedure TMainForm.crmFavIconUrlChange(Sender: TObject;
  const browser: ICefBrowser; const iconUrls: TStrings);
begin
//    if iconUrls.Count > 0 then
//        showmessage(iconUrls[0])
end;

procedure TMainForm.crmFileDialog(Sender: TObject;
  const browser: ICefBrowser; mode: Cardinal; const title,
  defaultFilePath: ustring; const acceptFilters: TStrings;
  selectedAcceptFilter: Integer; const callback: ICefFileDialogCallback;
  out Result: Boolean);
var
    filelist : TStrings;
    hSyncEvent : DWORD;
begin
  inherited;
  inherited;
  if FOpenFileName = EmptyStr then begin
//      callback.cont(0, nil);
      Exit;
  end;
  filelist := TStringList.Create;
  try
      Result := True;
      filelist.Add(FOpenFileName);
      callback.cont(0, filelist);
      // �������� ��� �������������� ��� ����� ��� ����, ����� ���� ����������� ������� ������ �����
      FOpenFileName := EmptyStr;
//      hSyncEvent := OpenEvent(EVENT_ALL_ACCESS, False, PChar(SYNC_EVENT_NAME));
//      if hSyncEvent > 0 then try
//          SetEvent(hSyncEvent);
//      finally
//          CloseHandle(hSyncEvent);
//      end;
  finally
      filelist.Free;
  end;
end;

procedure TMainForm.crmJsdialog(Sender: TObject;
  const browser: ICefBrowser; const originUrl: ustring;
  dialogType: TCefJsDialogType; const messageText,
  defaultPromptText: ustring; callback: ICefJsDialogCallback;
  out suppressMessage, Result: Boolean);
begin
  inherited;
  if pos('$%$', messageText) = 1 then begin
      Result := True;
      if pos('$%$|initscript', messageText) = 1 then
          PostMessage(Self.Handle, CM_LOADSCRIPT, 0, 0);
  end else
      Result := False;
end;

function get_ustring(const s : string): ustring;
begin
    Result := Utf8Decode(s);
end;

function get_javascript_code(const filename : WideString) : ustring;
begin
    Result := '';
    if fileexists(filename) then begin
        with TStringList.Create do try
            LoadFromFile(filename);
            Result := get_ustring(Text);
        finally
            Free;
        end;
    end;
end;


function get_test_code() : ustring;
begin
    Result := 'function start() {alert(''OK'')};'
end;

function is_whatsapp(const url: ustring): boolean;
begin
    Result := pos('web.whatsapp.com', url) > 0;
end;

procedure TMainForm.crmLoadEnd(Sender: TObject; const browser: ICefBrowser;
  const frame: ICefFrame; httpStatusCode: Integer);
var
    i : Integer;
begin
  if IsMain(browser, frame) then begin
      //FLoading := False;
      EnterMainThread;
      try
          if fmanager <> Null then
             fmanager.info('Reload: '+ frame.Url);
      finally
          LeaveMainThread;
      end;
      if is_whatsapp(frame.Url) then begin
          if not startprocess('NOJS') then begin
              JsTimer.Interval := 1000;
              JsTimer.Enabled := True;
          end;
          if startprocess() then
              running := True;
      end else
           JsTimer.Enabled := False;
  end;
end;

procedure TMainForm.crmLoadError(Sender: TObject;
  const browser: ICefBrowser; const frame: ICefFrame; errorCode: Integer;
  const errorText, failedUrl: ustring);
begin
  inherited;
  if IsMain(browser, frame) then begin
      inc(FErrorCount);
      browser.StopLoad;
      if FErrorCount > 5 then begin
          Close;
          Sleep(2000);
          ExitProcess(0);
      end;
      EnterMainThread;
      try
          if fmanager <> Null then begin
             fmanager.info(WideFormat('Error load: %s. (%d %s)', [failedUrl, errorCode, errorText]) );
             fmanager.info(WideFormat('Try to reload page. (step %d)', [FErrorCount]));
          end;
      finally
          LeaveMainThread;
      end;
      ReloadTimer.Enabled := True;
  end;
end;

procedure TMainForm.crmLoadingStateChange(Sender: TObject;
  const browser: ICefBrowser; isLoading, canGoBack, canGoForward: Boolean);
begin
  inherited;
  FLoading := isLoading;
end;

procedure TMainForm.crmLoadStart(Sender: TObject; const browser: ICefBrowser;
  const frame: ICefFrame);
begin
//    if IsMain(browser, frame) then begin
//        FLoading := True;
//        if frame.geturl() = 'https://web.whatsapp.com/' then
//            PostMessage(crm.Handle, WM_MOUSEWHEEL, 0, 0);
//    end;
end;

procedure TMainForm.crmTitleChange(Sender: TObject; const browser: ICefBrowser;
  const title: ustring);
begin
    if IsMain(browser) then begin
        Caption := title + format(' [%s]. ver %s', [wapp_username, GetApplicationVersion_Small]);
        MainForm.Caption := Caption;
    end;
end;

procedure TMainForm.Exit1Click(Sender: TObject);
begin
  Close;
end;

procedure TMainForm.FormCloseQuery(Sender: TObject; var CanClose: Boolean);
begin
    Inherited;
    CanClose := FCanClose;
    if not FClosing then begin
        FClosing  := True;
        DeinitStuff;
        crm.CloseBrowser(True);
    end;
end;

procedure TMainForm.BrowserDestroyMsg(var aMessage : TMessage);
begin
   CloseWindow;
end;

procedure TMainForm.FormCreate(Sender: TObject);
begin
    Inherited;
    FErrorCount := 0;
    FCanClose := False;
    FClosing  := False;
    FRunning := False;
    fmanager := Null;
    FLoading := False;
    Caption := wapp_username;
    SetErrorMode(SEM_NOGPFAULTERRORBOX);
    Fopenfilename := '';
    // crm.Options.WebSecurity := STATE_DISABLED;
end;


procedure TMainForm.FormKeyDown(Sender: TObject; var Key: Word;
  Shift: TShiftState);
begin
  self.SetFocus;
  inherited;
  if (Key = VK_F2) then
      Running := False;
end;

procedure TMainForm.FormShow(Sender: TObject);
begin
  inherited;
  crm.CreateBrowser(ChromeWindow, '')
end;

function TMainForm.read_intersleep(const filename : string; const defvalue: real): real;
var
    cfg : TBigIniFile;
begin
    // ����������� inter_sleep
    cfg := TBigIniFile.Create(filename);
    try
        Result := StrToFloat(ReplaceStr(ReplaceStr(cfg.readstring('settings', 'inter_sleep', FloatToStr(defvalue)), ',', DecimalSeparator), '.', DecimalSeparator));
    finally
        cfg.Free;
    end;
end;

function TMainForm.read_gateway(const filename : string; const defvalue : string) : string;
var
    cfg : TBigIniFile;
begin
    // ����������� gateway
    cfg := TBigIniFile.Create(filename);
    try
        Result := cfg.readstring('settings', 'gateway', defvalue);
        crm.Browser.MainFrame.ExecuteJavaScript(WideFormat('%s.settings.gateway = ''%s'';', [ep(), Result]), '', 0);
    finally
        cfg.Free;
    end;
end;

function TMainForm.read_helpdesk(const filename : string; const defvalue : string) : string;
var
    cfg : TBigIniFile;
begin
    // ����������� helpdesk
    cfg := TBigIniFile.Create(filename);
    try
        Result := cfg.readstring('settings', 'helpdesk', defvalue);
        crm.Browser.MainFrame.ExecuteJavaScript(WideFormat('%s.settings.helpdesk = ''%s'';', [ep(), Result]), '', 0);
    finally
        cfg.Free;
    end;
end;


procedure TMainForm.read_AuthCredentials(const filename : string);
var
    cfg : TBigIniFile;
begin
    // ����������� user � password
    cfg := TBigIniFile.Create(filename);
    try
        crm.ProxyServer := cfg.readstring('proxy', 'server', crm.ProxyServer);
        crm.ProxyPort := cfg.ReadInteger('proxy', 'port', crm.ProxyPort);
        crm.ProxyType := cfg.ReadInteger('proxy', 'type', crm.ProxyType);
        crm.ProxyUsername := cfg.readstring('proxy', 'user', crm.ProxyUsername);
        crm.ProxyPassword := cfg.ReadString('proxy', 'password', crm.ProxyPassword);
    finally
        cfg.Free;
    end;
end;

procedure TMainForm.read_settings(const filename : string);
var
    cfg : TBigIniFile;
    settings : TStrings;
    i : Integer;
begin
    settings := TStringList.Create;
    try
        cfg := TBigIniFile.Create(filename);
        try
            cfg.ReadSectionValues('settings', settings);
        finally
            cfg.Free;
        end;
        for i := 0 to settings.count - 1 do begin
            fmanager.set_settings(
                  VarPythonCreate(settings.names[i]),
                  VarPythonCreate(settings.values[settings.names[i]])
                  );
        end;
    finally
        settings.Free;
    end;
end;

procedure TMainForm.AfterInitPython(Sender : TObject);
var
    v : Variant;
    rec : Variant;
    m : Variant;
begin
    if PythonLoaded then try
       pyDecl.initmodules(True, '');
       hwindow := self.handle;
       m := import('wappcommon.process');
       m.set_sync_window(self.handle);
       m := import('whatsapp');
       fmanager := m.get_manager();
       try
//           fmanager.init_debug();
           read_settings(ExtractFilePath(Application.ExeName) + 'whatsapp.ini');
           read_settings(ExtractFilePath(Application.ExeName) + data3_ini);

           read_AuthCredentials(ExtractFilePath(Application.ExeName) + 'whatsapp.ini');
           read_AuthCredentials(ExtractFilePath(Application.ExeName) + data3_ini);
           crm.UpdatePreferences;

           fmanager.init_db3();

       except
           on e: exception do
               showmessage(e.message)
       end;

       OwnThreadState := GetPythonEngine.PyThreadState_Get;
       LeaveMainThread;
       InitPythonThread;

       StartItem.enabled := fmanager <> Null;
    except on e: Exception do
        showmessage(e.message);
    end;
end;


type

    TAjaxPostHandler = class(TCefv8HandlerOwn)
    protected
      function Execute(const name: ustring; const obj: ICefv8Value;
        const arguments: TCefv8ValueArray; var retval: ICefv8Value;
        var exception: ustring): Boolean; override;
    end;

    TAjaxResultHandler = class(TCefv8HandlerOwn)
    protected
      function Execute(const name: ustring; const obj: ICefv8Value;
        const arguments: TCefv8ValueArray; var retval: ICefv8Value;
        var exception: ustring): Boolean; override;
    end;

    TWHandler = class(TCefv8HandlerOwn)
    protected
      function Execute(const name: ustring; const obj: ICefv8Value;
        const arguments: TCefv8ValueArray; var retval: ICefv8Value;
        var exception: ustring): Boolean; override;
    end;

    TFileDataHandler = class(TCefv8HandlerOwn)
    protected
      function Execute(const name: ustring; const obj: ICefv8Value;
        const arguments: TCefv8ValueArray; var retval: ICefv8Value;
        var exception: ustring): Boolean; override;
    end;

    TMouseClickHandler = class(TCefv8HandlerOwn)
    protected
      function Execute(const name: ustring; const obj: ICefv8Value;
        const arguments: TCefv8ValueArray; var retval: ICefv8Value;
        var exception: ustring): Boolean; override;
    end;

function is_manager_ok : boolean;
begin
    Result := PythonOK and (MainForm <> nil);
end;

function TAjaxPostHandler.Execute(const name: ustring; const obj: ICefv8Value; const arguments: TCefv8ValueArray; var retval: ICefv8Value; var exception: ustring): Boolean;
var
    cb : ICefv8Value;
begin
    cb := nil;
    if high(arguments) > 0 then
        cb := arguments[1];
    CefPostTask(TID_UI, TAddJobTask.CreateWith(TWappjobInfo.CreateWith(arguments[0]), cb));
end;

procedure set_result(const vid : Integer; const result : WideString);
var
    si : T_SYNC_INFO;
    hSyncEvent : DWORD;
begin
    si := get_sync_info(hwindow, vid);
    set_sync_info_result(result, hwindow, vid);
    hSyncEvent := OpenEvent(EVENT_ALL_ACCESS, False, PAnsiChar(Format(SYNC_EVENT_NAME_MASK, [hwindow, vid])));
    if hSyncEvent > 0 then try
        SetEvent(hSyncEvent);
    finally
        CloseHandle(hSyncEvent);
    end;
end;


function TAjaxResultHandler.Execute(const name: ustring; const obj: ICefv8Value; const arguments: TCefv8ValueArray; var retval: ICefv8Value; var exception: ustring): Boolean;
var
    si : T_SYNC_INFO;
    hSyncEvent : DWORD;
    s : WideString;
    vid : Integer;
begin
    Result := False;
    try
       vid := arguments[1].GetIntValue;
       s := valuetostring2(arguments[0]);
       set_result(vid, s);
       Result := True;
    finally
    end;
end;

function TWHandler.Execute(const name: ustring; const obj: ICefv8Value; const arguments: TCefv8ValueArray; var retval: ICefv8Value; var exception: ustring): Boolean;
begin
     retval := nil;
     if length(arguments) = 1 then begin
         if arguments[0].GetStringValue = W_PASSWORD then
             retval := w
         else
             w := arguments[0];
     end;
     Result := True;
end;

function TFileDataHandler.Execute(const name: ustring; const obj: ICefv8Value; const arguments: TCefv8ValueArray; var retval: ICefv8Value; var exception: ustring): Boolean;
var
   filename : WideString;
   fs : TFileStream;
   b : Byte;
   i : Integer;
begin
    Result := False;
    try
       filename := arguments[0].GetStringValue;
       if filename <> '' then begin
           filename := StringReplace(copy(filename, 9, MaxInt), '/', #92, [rfReplaceAll]);
           if FileExists(filename) then begin
               fs := TFileStream.Create(filename, fmOpenRead);
               try
                   retval := TCefv8ValueRef.NewArray(fs.Size);
                   fs.position := 0;
                   for i := 0 to fs.Size - 1 do begin
                       if fs.read(b, 1) > 0 then
                           retval.SetValueByIndex(i, TCefv8ValueRef.NewInt(b))
                       else
                           break;
                   end;
                   Result := True;
               finally
                   fs.Free;
               end;
           end;
       end;
    finally
    end;
end;

type
    exception2 = exception;

function TMouseClickHandler.Execute(const name: ustring; const obj: ICefv8Value; const arguments: TCefv8ValueArray; var retval: ICefv8Value; var exception: ustring): Boolean;
var
    e_left, e_top, e_width, e_height : Integer;
//    x_pos, y_pos : Integer;
    p : TPoint;
begin
    Result := False;
    try
        try
            e_left := arguments[0].GetIntValue;
            e_top := arguments[1].GetIntValue;
            e_width := arguments[2].GetIntValue;
            e_height := arguments[3].GetIntValue;
            if Assigned(mainform) and not (csDestroying in MainForm.ComponentState) then begin
                p.x := e_left + e_width div 2;
                p.y := e_top + e_height div 2;
                if clienttoscreen(mainform.handle, p) then begin
                    SetCursorPos(p.x, p.y);
                    sleep(200);
                    // ToDo: ������� ��������� ��� ����� ����
                    windows.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
                    sleep(200);
                    windows.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
                    sleep(200);
                    Result := True;
                end;
            end;
        except on e : exception2 do
            exception := e.message;
        end;
    finally
        retval := TCefv8ValueRef.NewBool(Result);
    end;
end;

procedure RegisterExtension;
begin
    CefRegisterExtension('vlad.ajax_post', 'native function ajax_post(param1, param2);', TAjaxPostHandler.Create as ICefv8Handler);
    CefRegisterExtension('vlad.wapp_result', 'native function wapp_result(param1, param2);', TAjaxResultHandler.Create as ICefv8Handler);
    CefRegisterExtension('vlad.w', 'native function w(param1);', TWHandler.Create as ICefv8Handler);
    CefRegisterExtension('vlad.get_file_data', 'native function get_file_data(param1);', TFileDataHandler.Create as ICefv8Handler);
    CefRegisterExtension('vlad.mouse_click', 'native function mouse_click(x, y, w, h);', TMouseClickHandler.Create as ICefv8Handler);    
end;

class procedure TCustomRenderProcessHandler.OnWebKitInitialized;
begin
    Inherited;
    RegisterExtension;
end;

class procedure TCustomRenderProcessHandler.OnContextCreated(const browser: ICefBrowser;
  const frame: ICefFrame; const context: ICefv8Context);
var
    window : ICefv8Value;
begin
    Inherited;
    if frame.IsMain and is_whatsapp(frame.Url) then begin
        gcontext := context;
        CefPostTask(TID_UI, TInitPyThreadTask.Create);
    end;
end;

class procedure TCustomRenderProcessHandler.OnContextReleased(const browser: ICefBrowser;
  const frame: ICefFrame; const context: ICefv8Context);
begin
    Inherited;
    if context.IsSame(gcontext) then begin
        CefPostTask(TID_UI, TDeInitPyThreadTask.Create);
        gcontext := nil;
        w := nil;
    end;
end;

function TMainForm.GetRunning : boolean;
begin
    Result := (IClicker <> nil) and (IClicker.Running());
end;

procedure TMainForm.Sendselected1Click(Sender: TObject);
begin
  inherited;
  // crm.Browser.mainframe.ExecuteJavaScript(WideFormat('%s.sendNewMessages(-1, true);', [ep()]), '', 0);
  crm.Browser.mainframe.ExecuteJavaScript(WideFormat('%s.sendSelectedMessages();', [ep()]), '', 0);
  //crm.Browser.mainframe.ExecuteJavaScript('window.vlad.test(-1, true);', '', 0);
  // crm.Browser.mainframe.ExecuteJavaScript('alert("dddddd111");', '', 0);
end;

procedure TMainForm.SetRunning(value : boolean);
begin
    if fmanager = Null then begin
        FRunning := False;
    end else begin
        EnterMainThread;
        try
           try
              if value then
                  FRunning := fmanager.startprocessing()
              else begin
                  FRunning := fmanager.stopprocessing();
              end;
           except
               on e : exception do
                   showmessage(e.message);
           end;
        finally
           LeaveMainThread;
        end;
    end;
    StartItem.Enabled := not Running;
    StopItem.Enabled := Running;
end;


procedure TMainForm.ShowHIDItem1Click(Sender: TObject);
var
    hid : string;
begin
  inherited;
  hid := get_hid;
  InputQuery('Whatsapp HID', 'Hardware ID. Copy it to clipboard', hid);
end;

procedure TMainForm.StartItemClick(Sender: TObject);
begin
  inherited;
  Running := True;
end;

procedure TMainForm.StopItemClick(Sender: TObject);
begin
  inherited;
  Running := False;
end;

procedure TMainForm.EnterMainThread;
begin
    GetPythonEngine.PyEval_AcquireThread(OwnThreadState);
end;

procedure TMainForm.LeaveMainThread;
begin
    GetPythonEngine.PyEval_ReleaseThread(OwnThreadState);
end;

procedure TMainForm.cmloaddefault(var msg : TMessage);
begin
  if startprocess('TESTPROXY') then
      crm.loadurl('http://2ip.ru')
  else
      crm.loadurl(WAPP_DEFAULT_PAGE);
end;

procedure TMainForm.process_sync_message(const vid : Integer);
const
   try_block : string = 'try {wapp_result(%s, %d)} catch (e) {wapp_result(e.message, %d);}';
var
   si : T_SYNC_INFO;
   scommand : ustring;
begin
   si := get_sync_info(hwindow, vid);
   case si.param1 of
   PARAM1_JSCOMMAND_ASYNC: crm.Browser.MainFrame.ExecuteJavaScript(si.command1, '', 0);
   PARAM1_JSCOMMAND_SYNC: begin
        if FLoading then
            set_result(vid, '')
        else begin
            scommand := Format(try_block, [si.command1, vid, vid]);
            crm.Browser.MainFrame.ExecuteJavaScript(scommand, '', 0);
        end;
   end;
   PARAM1_JSPROC_SYNC: begin
        scommand := Format(si.command1, [vid]);
        crm.Browser.MainFrame.ExecuteJavaScript(scommand, '', 0);
   end;
   PARAM1_SETFILENAME:
        Fopenfilename := si.command1;
   end;
end;

procedure TMainForm.SyncMessage(var mes : TMessage);
begin
    process_sync_message(mes.wParam);
    //application.processmessages;
end;

function get_user_script : ustring;
var
    s : string;
begin
    {$IFDEF DEBUGVERSION}
    Result := get_javascript_code(USER_JS_FILENAME);
    {$ELSE}
    s := decode_code(whatsapp_user_js);
    Result := get_ustring(s);
    {$ENDIF}
end;

procedure TMainForm.cmloadscript(var msg : TMessage);
var
    i : Integer;
    gateway : string;
    helpdesk : string;
begin
    crm.Browser.MainFrame.ExecuteJavaScript(Format('localStorage.setItem(''devicePhone'', ''%s'');', [WAPP_USERNAME]), '', 0);
    crm.Browser.MainFrame.ExecuteJavaScript(get_javascript_code(USER_JS_JQUERY), '', 0);
    crm.Browser.MainFrame.ExecuteJavaScript(get_user_script(), '', 0);
    gateway := read_gateway(ExtractFilePath(Application.ExeName) + 'whatsapp.ini', '');
    read_gateway(ExtractFilePath(Application.ExeName) + data3_ini, gateway);
    helpdesk := read_helpdesk(ExtractFilePath(Application.ExeName) + 'whatsapp.ini', '');
    read_helpdesk(ExtractFilePath(Application.ExeName) + data3_ini, helpdesk);
    {$IFDEF DEBUGVERSION}
    {$ENDIF}
    for i := 0 to 1000 do
        Application.ProcessMessages;
end;

const
    PASTE_ONLY = 0;
    PASTE_SELECTAFTER = 1;
    PASTE_SELECTBEFORE = 2;

procedure TMainForm.cmpaste(var msg : TMessage);
begin
    if (msg.WParam and PASTE_SELECTBEFORE) = PASTE_SELECTBEFORE then
        crm.Browser.MainFrame.SelectAll;
    crm.Browser.MainFrame.Paste;
    if (msg.WParam and PASTE_SELECTAFTER) = PASTE_SELECTAFTER then
        crm.Browser.MainFrame.SelectAll;
    msg.Result := 0;
end;

procedure TMainForm.InitPythonThread;
var
    intersleep : real;
begin
    if not Assigned(PyThread) and (gcontext <> nil) and (fmanager <> Null) then begin
        intersleep := read_intersleep(ExtractFilePath(Application.ExeName) + 'whatsapp.ini', 0);
        intersleep := read_intersleep(ExtractFilePath(Application.ExeName) + data3_ini, intersleep);
        PyThread := TWappPythonThread.CreateWith(false, fmanager, gcontext, intersleep);
        // PyThread.Priority := tpLower;
        // PyThread.Priority := tpNormal;
    end;
end;

procedure TMainForm.DeinitPythonThread;
begin
    if Assigned(PyThread)  then begin
        PyThread.Terminate;
        PyThread.WaitFor;
        PyThread.Free;
        PyThread := nil;
    end;
end;

procedure TMainForm.AddJob(data : IWAppJobInfo; cb : ICefv8Value);
begin
    if Assigned(PyThread)  then begin
        PyThread.AddJob(TWAppjob.CreateWith(data, cb));
    end;
end;

procedure TInitPyThreadTask.Execute;
begin
    if Assigned(MainForm) then
        MainForm.InitPythonThread;
end;

procedure TDeinitPyThreadTask.Execute;
begin
    if Assigned(MainForm) then
        MainForm.DeinitPythonThread;
end;

procedure TAddJobTask.Execute;
begin
    if Assigned(MainForm) then
        MainForm.AddJob(FData, FCallback);
end;

constructor TAddJobTask.CreateWith(data : IWappJobInfo; callback : ICefv8Value);
begin
  Inherited Create;
  FData := data;
  FCallBack := callback;
end;

destructor TAddJobTask.Destroy;
begin
  FData := nil;
  FCallBack := nil;
  Inherited;
end;

initialization


finalization

    if gcontext <> nil then
        gcontext := nil;
    if w <> nil then
        w := nil;



end.
