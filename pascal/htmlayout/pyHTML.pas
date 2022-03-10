unit pyHTML;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, tks_window, tks_pydocument, ExtCtrls, TB2Item,
  TB2Dock, TB2Toolbar, modulesintf, tks_TLB, pylayout, PythonEngine, tks_panels
  , htmlmessages, dockpanel, tkshtml_intf;


type

  TfmHTMLView = class(TfmPyDocument, ITKSKeyProcessor, IPyHtmlAction)
    HTMLEditItem: TTBItem;
    procedure HTMLEditItemClick(Sender: TObject);
  private
    FLayout : TPyHTMLControl;
    FEditorPanel : TDockPanel;
    procedure wmmodalresult(var msg : TMessage); message WM_MODALRESULT;
    procedure wmdocumentreload(var msg : TMessage); message WM_DOCUMENTRELOAD;
    procedure wmdocumentclose(var msg : TMessage); message WM_DOCUMENTCLOSE;
    procedure WMSetFocus(var Msg: TWMSetFocus); message WM_SETFOCUS;
    procedure WMDropFiles(var Msg: TWMDropFiles); message WM_DROPFILES;
    function refreshdatahandler(const event_name : string; const event_data : Variant) : boolean;
    procedure create_editor_panel;
    procedure DockDetail(IWND : ITKSWindow; wm : ITKSWindowManager);
    function DockQueryInterface(DockPanel : TDockPanel; const IID: TGUID; out Obj): HResult;
  protected
    procedure DoSetDockManager(wm : ITKSWindowManager); override;
    function DoEmulateMsg(var Msg : TWMKey) : Integer; override;
    function get_help_params(var hh_filename : WideString;
                 var hh_command : Integer; var hh_data : LongInt) : boolean; override;
  public
    procedure DoCloseWindow; override;
    constructor CreateWithManager(html : Variant; wm : ITKSWindowManager; APriorWindow : ITKSWindow = nil);
    destructor Destroy; override;
    function DoWindowChanging(wm : ITKSWindowManager; iWindow : ITKSWindow) : HResult; override; stdcall;
    // ITKSKeyProcessor
    function ProcessKey(const Shift : Integer; var Key : Word) : HResult; stdcall;
  public
    function DoPrint(Sender : IUnknown) : HResult; override; stdcall;
    function can_document_print : boolean; override;
  public
    // IPyHtmlAction
    function DoPyHtmlAction(const cmd : Integer; const param : PPyObject) : HResult;
  end;

implementation

{$R *.dfm}

uses VarPyth, tks_documentwindow, ShellAPI;

constructor TfmHTMLView.CreateWithManager(html : Variant; wm : ITKSWindowManager; APriorWindow : ITKSWindow = nil);
begin
   Inherited Create(nil, wm);
   Caption := html.title;
   FLayout := TPyHTMLControl.CreateWithObj(self, html);
   FLayout.Parent := self;
   FLayout.Align := alClient;
   TPyHTMLayout(FLayout.Layout).OnRefresh := refreshdatahandler;
   PriorWindow := APriorWindow;
end;

function TfmHTMLView.get_help_params(var hh_filename : WideString;
             var hh_command : Integer; var hh_data : LongInt) : boolean;
begin
   Result := Inherited get_help_params(hh_filename, hh_command, hh_data);
   hh_data := FLayout.helpcontext;
end;

procedure TfmHTMLView.HTMLEditItemClick(Sender: TObject);
begin
  inherited;
  create_editor_panel;
end;

procedure TfmHTMLView.create_editor_panel;
begin
   if FEditorPanel = nil then begin
      FEditorPanel := TdockPanel.Create(nil);
      FEditorPanel.Visible := True;
      FEditorPanel.Parent := self;
      FEditorPanel.Height := 300;
      FEditorPanel.Align := alBottom;
      FEditorPanel.Color := clBlue;
      FEditorPanel.OnDockWindow := DockDetail;
      FEditorPanel.OnQueryInterface := DockQueryInterface;
      FEditorPanel.DockWindow(TPyHTMLayout(FLayout.Layout).get_editor_window());
      with TSplitter.Create(self) do begin
           Align := alBottom;
           Parent := self;
      end;
   end;
end;

procedure TfmHTMLView.DockDetail(IWND : ITKSWindow; wm : ITKSWindowManager);
var
   iDockable : ITKSDockable;
begin
   if IWND <> nil then
      if IWND.QueryInterface(ITKSDockable, iDockable) = S_OK then
         iDockable.setDockManager(wm);
end;

function TfmHTMLView.DockQueryInterface(DockPanel : TDockPanel; const IID: TGUID; out Obj): HResult;
begin
    if (IsEqualGUID(IID, ITKSMainMenu) or IsEqualGUID(IID, ITKSToolbar)) and (WindowManager <> nil) then
       Result := WindowManager.QueryInterface(IID, Obj)
    else
        Result := E_FAIL;
end;

procedure TfmHTMLView.DoSetDockManager(wm : ITKSWindowManager);
begin
   Inherited;
   if wm <> nil then begin
      FLayout.Layout.InitHandlers;
      TPyHTMLayout(FLayout.Layout).init_gui(wm);
      TPyHTMLayout(FLayout.Layout).LoadHtml;
      if TPyHTMLayout(FLayout.Layout).can_drop_files then
         DragAcceptFiles(self.Handle, True);
      {$IFDEF DEVEL}
      MainMenuRootItem.Visible := True;
      {$ENDIF}
      HTMLEditItem.Enabled := TPyHTMLayout(FLayout.Layout).editor_enabled();
      {$IFNDEF DEVEL}
      HTMLEditItem.Visible := HTMLEditItem.Enabled;
      {$ENDIF}
   end;
end;

destructor TfmHTMLView.Destroy;
begin
   try
      if FLayout <> nil then begin
         if TPyHTMLayout(FLayout.Layout).can_drop_files then
            DragAcceptFiles(self.Handle, False);
         FLayout.Free;
         FLayout := nil;
      end;
      Inherited;
   except
   end;
end;

function TfmHTMLView.DoEmulateMsg(var Msg : TWMKey) : Integer;
begin
    Result := Inherited DoEmulateMsg(Msg);
    if Result = 0 then
       Result := FLayout.DoKeyMsg(Msg);
end;

procedure TfmHTMLView.DoCloseWindow;
begin
   Inherited;
   if FEditorPanel <> nil then begin
      FEditorPanel.Free;
      FEditorPanel := nil;
   end;
   TPyHTMLayout(FLayout.Layout).deinit_gui(self.modalresult);
end;

procedure TfmHTMLView.wmmodalresult(var msg : TMessage);
var
  iHandle : ITKSHandle;
begin
   self.modalresult := msg.WParam;
   if WindowManager.QueryInterface(ITKSHandle, iHandle) = S_OK then
      PostMessage(iHandle.getHandle(), msg.Msg, msg.WParam, msg.LParam);
end;

procedure TfmHTMLView.wmdocumentreload(var msg : TMessage);
begin
end;

function TfmHTMLView.DoWindowChanging(wm : ITKSWindowManager; iWindow : ITKSWindow) : HResult;
begin
    if FLayout.Layout.can_close() then begin
        if (TPyHTMLayout(FLayout.Layout).WindowManager <> nil) then
           TPyHTMLayout(FLayout.Layout).WindowManager.DockWindow(nil);
        Result := Inherited DoWindowChanging(wm, iWindow);
    end else
        Result := E_FAIL;
end;

function TfmHTMLView.DoPrint(Sender : IUnknown) : HResult;
begin
    Result := TPyHTMLayout(FLayout.Layout).do_print;
end;

function TfmHTMLView.can_document_print : boolean;
begin
    Result := TPyHTMLayout(FLayout.Layout).can_document_print;
end;

procedure TfmHTMLView.wmdocumentclose(var msg : TMessage);
begin
    try
    WindowManager.DockWindow(nil);
    except end;
end;

procedure TfmHTMLView.WMSetFocus(var Msg: TWMSetFocus);
begin
   if TMessage(Msg).lParam = 1 then
      TPyHTMLayout(FLayout.Layout).renew_focus;
end;

procedure TfmHTMLView.WMDropFiles(var Msg: TWMDropFiles);
var
  FilesCount, I: Integer;
  FileName: array[0..MAX_PATH] of WideChar;
  FileNames : TStrings;
begin
  FilesCount := DragQueryFileW(Msg.Drop, MAXDWORD, nil, 0);
  FileNames := TStringList.Create;
  try
    for I := 0 to FilesCount - 1 do begin
      if (DragQueryFileW(Msg.Drop, I, @FileName, SizeOf(FileName)) > 0) then begin
          FileNames.Add(FileName);
       end;
    end;
    TPyHTMLayout(FLayout.Layout).drop_files(FileNames);
    DragFinish(Msg.Drop);
    Msg.Result := 0;
  finally
    FileNames.Free;
  end;
end;

function TfmHTMLView.refreshdatahandler(const event_name : string; const event_data : Variant) : boolean;
var
   iPanel : IStatusPanel;
begin
   result := True;
   if WindowManager = nil then begin
      Result := False;
      Exit;
   end;
   if event_name = 'height' then begin
      if WindowManager.QueryInterface(IStatusPanel, iPanel) = S_OK then
         iPanel.setHeight(integer(event_data))
   end else if event_name = 'width' then begin
      if WindowManager.QueryInterface(IStatusPanel, iPanel) = S_OK then
         iPanel.setWidth(integer(event_data))
   end else
      result := False;
end;

function TfmHTMLView.ProcessKey(const Shift : Integer; var Key : Word) : HResult;
var
   ikey : ITKSKeyProcessor;
begin
    Result := E_FAIL;
    // переделать. передать в layout местный windowmanager
    if WindowManager <> nil then
       if WindowManager.QueryInterface(ITKSKeyProcessor, ikey) = S_OK then
          Result := ikey.ProcessKey(Shift, key);
end;

function TfmHTMLView.DoPyHtmlAction(const cmd : Integer; const param : PPyObject) : HResult;
begin
   TPyHTMLayout(FLayout.Layout).dohtmlaction(cmd, param)
end;

end.

