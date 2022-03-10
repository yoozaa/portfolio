unit tkshtml_data;

interface

uses
  SysUtils, Classes;

type
  Tdm = class(TDataModule)
    procedure DataModuleCreate(Sender: TObject);
  private
  public
    procedure StopServer(Sender : TObject);
  end;

var
  dm: Tdm;

implementation

{$R *.dfm}

uses tkscom, tks_event, tks_eventtypes, tks_busywindowintf, tkshtml_busywindow, varpyth, variants, pythonengine;

type

    THTMLBusyWindowFactory = class(TInterfacedObject, ITKSBusyWindowFactory, ITKSBusyWindowFactory2)
    private
        fhtmldoc : Variant;
    public
        // ITKSBusyWindowFactory
        function createwindow(const h_wnd: Integer): ITKSBusyWindow; stdcall;
        // ITKSBusyWindowFactory2
        function setdocumentobject(const htmldoc : Pointer) : HResult; stdcall;
    public
        procedure AfterConstruction; override;
        destructor Destroy; override;
    end;


function THTMLBusyWindowFactory.createwindow(const h_wnd: Integer): ITKSBusyWindow;
begin
    if not VarIsNull(fhtmldoc) then begin
        Result := TfmHtmlBusyWindow.CreatewithHtml(nil, h_wnd, fhtmldoc);
        fhtmldoc := Null;
    end else
        Result := TfmHtmlBusyWindow.CreatewithHtml(nil, h_wnd, import('gtd.html.busy').getbusydocument());
end;

function THTMLBusyWindowFactory.setdocumentobject(const htmldoc : Pointer) : HResult;
begin
    fhtmldoc := VarPythonCreate(PPyObject(htmldoc));
    Result := S_OK;
end;

destructor THTMLBusyWindowFactory.Destroy;
begin
    fhtmldoc := Null;
    Inherited;
end;

procedure THTMLBusyWindowFactory.AfterConstruction;
begin
    Inherited AfterConstruction;
    fhtmldoc := Null;
end;

procedure Tdm.DataModuleCreate(Sender: TObject);
begin
  if (tkscom.MainServer <> nil) then begin
     TTKSEvent.CreateEvent(EVENT_STOPSERVER, Self.StopServer);
     tkscom.MainServer.RegisterManager(THTMLBusyWindowFactory.Create());
  end;
end;

procedure Tdm.StopServer(Sender: TObject);
begin
    tkscom.MainServer := nil;
end;

end.
