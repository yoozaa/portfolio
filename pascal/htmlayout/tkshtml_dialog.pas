unit tkshtml_dialog;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, htmlmessages, pyhtmldialog, htmlayout_h, udform, tks_TLB;

type
  TfmHTMLDialog = class(TDForm)
    procedure FormActivate(Sender: TObject);
    procedure FormCloseQuery(Sender: TObject; var CanClose: Boolean);
    procedure FormCreate(Sender: TObject);
  private
     FSaveName: String;
     FHtml : Variant;
     Fwm: ITKSWindowManager;
     FLayout: TPyHTMLDialog;
     FSaveForm : boolean;
     function get_layout() : TPyHTMLDialog;
  protected
     function GetSection: String; override;
     procedure WndProc(var Message: TMessage); override;
     procedure CreateWindowHandle(const Params: TCreateParams); override;
     procedure DestroyWindowHandle; override;
     procedure CreateParams(var Params: TCreateParams); override;
     function DoHelp() : boolean; override;
     function get_help_params(var hh_filename : WideString;
                 var hh_command : Integer; var hh_data : LongInt) : boolean; virtual;
  public
     constructor CreateWithHtml(AOwner : TComponent; html : Variant; const wm : ITKSWindowManager = nil); virtual;
     destructor Destroy; override;
     procedure CreateHTMLayout;
     procedure DestroyHTMLayout;
  public
     procedure WMGetMinMaxInfo(var msg: TWMGetMinMaxInfo); message WM_GETMINMAXINFO;
     procedure wmmodalresult(var msg : TMessage); message WM_MODALRESULT;
     procedure wmdocumentreload(var msg : TMessage); message WM_DOCUMENTRELOAD;
     procedure wmdocumentclose(var msg : TMessage); message WM_DOCUMENTCLOSE;
     procedure WMSetFocus(var Msg: TWMSetFocus); message WM_SETFOCUS;
     function refreshdatahandler(const event_name : string; const event_data : Variant) : boolean;
     procedure SaveForm(const Section: String); override;
     procedure RestoreForm(const Section: String); override;
  end;

function showhtmldialog(html : Variant; const wm : ITKSWindowManager = nil) : TModalresult;

implementation

{$R *.dfm}

const
   FORM_TRANSPARENT_COLOR = clAqua;

function showhtmldialog(html : Variant; const wm : ITKSWindowManager = nil) : TModalResult;
begin
   with TfmHTMLDialog.CreateWithHtml(Application, html, wm) do try
       Result := showmodal;
   finally
       Free;
   end;
end;

procedure TfmHTMLDialog.SaveForm(const Section: String);
begin
    if FSaveForm then
        inherited;
end;

procedure TfmHTMLDialog.RestoreForm(const Section: String);
begin
    if FSaveForm then
        inherited;
end;

function TfmHTMLDialog.DoHelp() : boolean;
var
   iHelp : ITKSHelp;
   hh_filename : WideString;
   hh_command : Integer;
   hh_data : LongInt;
begin
  Result := False;
  if (Fwm <> nil) and
     (Fwm.QueryInterface(ITKSHelp, iHelp) = S_OK)
  then
     Result :=
         get_help_params(hh_filename, hh_command, hh_data) and
         (iHelp.setHelpFile(hh_filename) = S_OK) and
         (iHelp.ShowHelp(hh_command, hh_data, Self.Handle) = S_OK)
end;

function TfmHTMLDialog.get_help_params(var hh_filename : WideString;
             var hh_command : Integer; var hh_data : LongInt) : boolean;
begin
   Result := True;
   hh_filename := '';
   hh_command := HH_HELP_CONTEXT;
   hh_data := FHtml.helpcontext;
end;


constructor TfmHTMLDialog.CreateWithHtml(AOwner : TComponent; html : Variant;
        const wm : ITKSWindowManager = nil);
begin
    FHtml := html;
    Fwm := wm;
    FSaveName := string(FHtml.form_save_section);
    FSaveForm := boolean(FHtml.save_form);
    Inherited Create(AOwner);
    BorderStyle := bsNone;
    ClientWidth := html.width;
    ClientHeight := html.height;
    Constraints.MinWidth := html.min_width();
    Constraints.MinHeight := html.min_height();
end;

destructor TfmHTMLDialog.Destroy;
begin
   DestroyHTMLayout;
   FHtml := Null;
   Inherited;
end;

function TfmHTMLDialog.GetSection: String;
begin
  Result := FSaveName;
end;

procedure TfmHTMLDialog.CreateParams(var Params: TCreateParams);
begin
  inherited CreateParams(Params);
  Params.style := Params.style or WS_CLIPCHILDREN;
end;

procedure TfmHTMLDialog.wmmodalresult(var msg : TMessage);
begin
   self.modalresult := msg.WParam;
end;

procedure TfmHTMLDialog.wmdocumentreload(var msg : TMessage);
begin
end;

procedure TfmHTMLDialog.wmdocumentclose(var msg : TMessage);
begin
   self.close();
end;

procedure TfmHTMLDialog.WMSetFocus(var Msg: TWMSetFocus);
begin
   if FLayout = nil then
      Exit;
   if TMessage(Msg).lParam = 1 then
      FLayout.renew_focus
end;

function TfmHTMLDialog.refreshdatahandler(const event_name : string; const event_data : Variant) : boolean;
begin
   Result := True;
   if event_name = 'height' then
      clientheight := integer(event_data)
   else if event_name = 'width' then
      clientwidth := integer(event_data)
   else
      result := False;
end;

function TfmHTMLDialog.get_layout() : TPyHTMLDialog;
begin
   Result := TPyHTMLDialog.CreateWithObj(self, FHtml);
end;

procedure TfmHTMLDialog.CreateWindowHandle(const Params: TCreateParams);
var
    dwExStyle: DWORD;
begin
  with Params do begin
     dwExStyle := Params.ExStyle;        
     if fhtml.layered then 
        dwExStyle := dwExStyle or WS_EX_LAYERED;
     WindowHandle := CreateWindowEx(dwExStyle, WinClassName, Caption, Style,
        X, Y, Width, Height, WndParent, 0, WindowClass.hInstance, Param);
  end;
end;

procedure TfmHTMLDialog.DestroyWindowHandle;
begin
  Inherited;
end;

procedure TfmHTMLDialog.FormActivate(Sender: TObject);
begin
   CreateHTMLayout;
end;

procedure TfmHTMLDialog.FormCloseQuery(Sender: TObject;
  var CanClose: Boolean);
begin
    CanClose := True;
    if FLayout <> nil then
       FLayout.deinit_gui(self.modalresult);
end;

procedure TfmHTMLDialog.FormCreate(Sender: TObject);
begin
  position := TPosition(Integer(FHtml.position));
  inherited;
end;

procedure TfmHTMLDialog.CreateHTMLayout;
begin
  DestroyHTMLayout;
  FLayout := get_layout();
  with FLayout do begin
     OnRefresh := refreshdatahandler;
     InitHandlers;
     init_gui(nil);
     LoadHtml;
  end;
end;

procedure TfmHTMLDialog.DestroyHTMLayout;
begin
  if FLayout <> nil then
     FreeAndNil(FLayout);
end;

function GetWindowState(Wnd : DWORD) : DWORD;
var
  WP : TWindowPlacement;
begin
  WP.Length := SizeOf(TWINDOWPLACEMENT);
  if GetWindowPlacement(Wnd, @WP) then
    Result := WP.showCmd
  else
    Result := 0;
end;

procedure TfmHTMLDialog.WndProc(var Message: TMessage);
var
   bHandled: bool;
   lr : LRESULT;
   pmmi : PMinMaxInfo;
   rc : TRect;
begin
    lr := HTMLayoutProcND(handle, Message.Msg, Message.WParam, Message.LParam, @bHandled);
    if bHandled then begin
       Message.Result := lr;
       Exit;
    end;
    case Message.msg of
    WM_NCHITTEST:
        if FLayout <> nil then 
          if GetWindowState(Handle) <> SW_SHOWMAXIMIZED then
            begin
              Message.result := FLayout.hit_test(TWMNCHitTest(Message).XPos, TWMNCHitTest(Message).YPos);
              Exit;
            end;
    WM_NCCALCSIZE,
    WM_NCPAINT: begin
          Message.result := 0; // we have no non-client areas.
          Exit;
       end;
    WM_NCACTIVATE: begin
          if message.wParam = 0 then
             Message.result := 1
          else
             Message.result := 0; // we have no non-client areas.
          Exit;
        end;
    {
    WM_GETMINMAXINFO: begin
          lr := DefWindowProcW(self.handle, message.msg, message.wParam, message.lParam);
          pmmi := PMINMAXINFO(message.lParam);
          pmmi.ptMinTrackSize.x := HTMLayoutGetMinWidth(self.handle);
          GetWindowRect(self.handle, rc);
          pmmi.ptMinTrackSize.y := HTMLayoutGetMinHeight(self.handle, rc.right - rc.left);
          Message.Result := lr;
          Exit;
       end;
    }
    end;
    inherited;
end;

procedure TfmHTMLDialog.WMGetMinMaxInfo(var msg: TWMGetMinMaxInfo);
var
  Rect: TRect;
begin
  msg.MinMaxInfo.ptMinTrackSize.x := HTMLayoutGetMinWidth(self.handle);
  GetWindowRect(self.handle, Rect);
  msg.MinMaxInfo.ptMinTrackSize.y := HTMLayoutGetMinHeight(self.handle, Rect.right - Rect.left);

  SystemParametersInfo(SPI_GETWORKAREA, 0, @Rect, 0);
  msg.MinMaxInfo.ptMaxPosition.X := Rect.Left;
  msg.MinMaxInfo.ptMaxPosition.Y := Rect.Top;
  msg.MinMaxInfo.ptMaxSize.X := Rect.Right;
  msg.MinMaxInfo.ptMaxSize.Y := Rect.Bottom;
end;


end.
