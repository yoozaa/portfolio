unit tkshtml_host;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, tks_appwindow, ExtCtrls, JvGIF, TB2Dock, TB2Toolbar, DockPanel, modulesintf, tks_TLB;

const
   WM_MODALRESULT = WM_USER + 1;

type

  TfmHTMLHost = class(TfmAppWindow)
  private
    FKey : Variant;
    FSaveSection : AnsiString;
    FDefaultWidth : Integer;
    FDefaultHeight : Integer;
    procedure wmmodalresult(var msg : TMessage); message WM_MODALRESULT;
  protected
    function get_save_section() : string; override;
    function get_default_width : Integer; override;
    function get_default_height : Integer; override;
    procedure afterCreate(); override;
    procedure load_icon_from_file(const AFileName: AnsiString);
    procedure DoBeforeDockWindow(); override;
  public
    constructor CreateAsHost(key : Variant); override;
  end;

implementation

{$R *.dfm}

uses tks_windowtypes, pngimage;

constructor TfmHTMLHost.CreateAsHost(key : Variant);
begin
   FKey := key;
   try
      Create(Application);
      if not Sizable then begin
         ClientWidth := Integer(key.width);
         ClientHeight := Integer(key.height);
      end;
   finally
       FKey := Null;
   end;
end;

procedure TfmHTMLHost.afterCreate();
begin
   FSaveSection := Fkey.form_save_section;
   FDefaultWidth := Integer(Fkey.width);
   FDefaultHeight := Integer(Fkey.height);
   ShowStatusBar := boolean(Fkey.show_status_bar);
   BorderStyle := TFormBorderStyle(Integer(Fkey.border_style));
   WindowState := TWindowState(Integer(Fkey.window_state));
   load_icon_from_file(Fkey.file_icon);
end;

procedure TfmHTMLHost.load_icon_from_file(const AFileName: AnsiString);
const
  icon_size = 16;
var
  ext: AnsiString;
  png: TPNGObject;
  bmp: TBitmap;
  il: TImageList;
begin
  png := nil;
  if (AFileName <> '') and FileExists(AFileName) then begin
    ext := LowerCase(ExtractFileExt(AFileName));
    if ext = '.ico' then
      icon.LoadFromFile(AFileName)
    else if (ext = '.png') or (ext = '.bmp') then try
      bmp := TBitmap.Create;
      il := TImageList.Create(self);
      bmp.Transparent := True;

      if ext = '.png' then begin
        png := TPNGObject.create();
        png.loadFromFile(AFileName);
        bmp.Height := il.Height;
        bmp.Width := il.Width;
        bmp.Canvas.CopyRect(
          Rect(0, 0, bmp.Width, bmp.Height), png.Canvas,
          Rect(0, 0, png.Width, png.Height));
      end else begin
        bmp.LoadFromFile(AFileName);
      end;
      il.Height := bmp.Height;
      il.Width := bmp.Width;
      il.AddMasked(bmp, bmp.Canvas.Pixels[0,0]);

      il.GetIcon(0, icon);
    finally
      FreeAndNil(png);
      FreeAndNil(bmp);
      FreeAndNil(il);
    end;
  end else
      Icon.Handle := LoadIcon(GetModuleHandle(PChar(Application.ExeName)), 'MAINICON');
end;

function TfmHTMLHost.get_default_width : Integer;
begin
   Result := FDefaultWidth;
end;

function TfmHTMLHost.get_default_height : Integer;
begin
   Result := FDefaultHeight;
end;

function TfmHTMLHost.get_save_section() : string;
begin
   Result := FSaveSection;
end;

procedure TfmHTMLHost.wmmodalresult(var msg : TMessage);
begin
   self.modalresult := msg.WParam;
end;

procedure TfmHTMLHost.DoBeforeDockWindow();
begin
   MainMenu.Visible := False;
end;

end.
