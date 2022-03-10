unit tkshtml_busywindow;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, tks_busywindow, StdCtrls, ComCtrls, pylayout, htmlayout_h;


const

    WM_CREATELAYOUT = WM_USER + 123;

type

  Tfmhtmlbusywindow = class(Tfmbusywindow)
    procedure FormCloseQuery(Sender: TObject; var CanClose: Boolean);
  private
      FHtml : Variant;
      FLayout: TPyHTMLayout;
      function is_html_ok : boolean;
  protected
      procedure CreateWindowHandle(const Params: TCreateParams); override;
  public
      constructor CreateWithHtml(AOwner : TComponent; h_wnd : Integer; html : Variant); virtual;
      procedure WndProc(var Message: TMessage); override;
      destructor Destroy; override;
  public
      function setstatus(const status : WideString): HResult; override; stdcall;
      function settitle(const title : WideString): HResult; override; stdcall;
      function init_progress(const maxvalue : Integer): HResult; override; stdcall;
      function deinit_progress: HResult; override; stdcall;
      function step_progress: HResult; override; stdcall;
  public
      procedure doshowwindow; override;
  end;

implementation

{$R *.dfm}

constructor Tfmhtmlbusywindow.CreateWithHtml(AOwner : TComponent; h_wnd : Integer; html : Variant);
begin
    FHtml := html;
    Inherited CreatewithHandle(AOwner, h_wnd);
    FLayout := TPyHTMLayout.CreateWithObj(self, FHtml);
end;

destructor Tfmhtmlbusywindow.Destroy;
begin
    FLayout.Free;
    FHtml := Null;
    Inherited;
end;

procedure Tfmhtmlbusywindow.FormCloseQuery(Sender: TObject;
  var CanClose: Boolean);
begin
    inherited;
    FLayout.deinit_gui(self.modalresult);
end;

procedure Tfmhtmlbusywindow.CreateWindowHandle(const Params: TCreateParams);
begin
  with Params do
        WindowHandle := CreateWindowEx(
                   ExStyle or WS_EX_LAYERED,
                   WinClassName,
                   Caption,
                   Style or WS_CLIPCHILDREN,
                   X, Y, Width, Height,
                   wnd,
                   0,
                   WindowClass.hInstance,
                   Param);
end;

function Tfmhtmlbusywindow.setstatus(const status : WideString): HResult;
begin
    if is_html_ok then
        fhtml.setstatus(status);
end;

function Tfmhtmlbusywindow.settitle(const title : WideString): HResult;
begin
    if is_html_ok then
        fhtml.settitle(title);
end;

function Tfmhtmlbusywindow.init_progress(const maxvalue : Integer): HResult;
begin
    if is_html_ok then
        fhtml.init_progress(maxvalue);
end;

function Tfmhtmlbusywindow.deinit_progress: HResult;
begin
    if is_html_ok then
        fhtml.deinit_progress;
end;

function Tfmhtmlbusywindow.step_progress: HResult;
begin
    if is_html_ok then
        fhtml.step_progress;
end;

function Tfmhtmlbusywindow.is_html_ok: boolean;
begin
    Result := True;
end;

procedure Tfmhtmlbusywindow.doshowwindow;
begin
    FLayout.InitHandlers;
    FLayout.init_gui(nil);
    FLayout.LoadHtml;
end;

procedure Tfmhtmlbusywindow.WndProc(var Message: TMessage);
var
  bHandled: bool;
  lr : LRESULT;
begin
  // HTMLayout наверное как-то по-своему интерпретирует это сообщение
  // поэтому ну его нафик
  if Message.Msg = CM_CHILDKEY then Exit;
  lr := HTMLayoutProcND(handle, Message.Msg, Message.WParam, Message.LParam, @bHandled);
  if bHandled then
      Message.Result := lr
  else
      inherited;
end;

end.
