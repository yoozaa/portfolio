unit whatsapp_clicker;

interface

uses Windows, AsyncCalls, Variants;

type

    IWAppClicker = interface
    ['{2D9FB54E-551B-47EA-A93B-CAACF3B9EA01}']
        function start() : HResult; stdcall;
        function stop() : HResult; stdcall;
        function Running : boolean; stdcall;
    end;

    TWAppClicker = class(TInterfacedObject, IWAppClicker)
    private
        FTerminated : boolean;
        IClickCall : IAsyncCall;
        FManager : Variant;
        procedure DoClick(sender : TObject);
        procedure setTerminated(value : boolean);
        function getTerminated(): boolean;
    public
        constructor CreateWithManager(Manager : Variant);
        destructor Destroy; override;
    public
        // IWAppClicker
        function start() : HResult; stdcall;
        function stop() : HResult; stdcall;
        function Running : boolean; stdcall;
    public
        property Terminated: boolean read getTerminated write setTerminated;
    end;

implementation

uses VarPyth;

var
    TermProperty : TRTLCriticalSection;

constructor TWAppClicker.CreateWithManager(Manager : Variant);
begin
    Inherited Create;
    FManager := Manager;
end;

destructor TWAppClicker.Destroy;
begin
    FManager := Null;
    Inherited Destroy;
end;

function TWAppClicker.start() : HResult;
begin
    Result := E_FAIL;
    if IClickCall = nil then begin
        IClickCall := AsyncCall(DoClick, nil);
        IClickCall.ForceDifferentThread;
    end;
end;

function TWAppClicker.stop() : HResult;
begin
    Result := E_FAIL;
    if IClickCall <> nil then begin
        Terminated := True;
        IClickCall.Sync;
        IClickCall := nil;
    end;
end;

function TWAppClicker.Running : boolean;
begin
    Result := IClickCall <> nil;
end;

procedure TWAppClicker.setTerminated(value : boolean);
begin
    EnterCriticalSection(TermProperty);
    try
        FTerminated := value;
    finally
        LeaveCriticalSection(TermProperty);
    end;
end;

function TWAppClicker.getTerminated(): boolean;
begin
    Result := True;
    EnterCriticalSection(TermProperty);
    try
        Result := FTerminated;
    finally
        LeaveCriticalSection(TermProperty);
    end;
end;

procedure TWAppClicker.DoClick(sender : TObject);
var
    i, r : Integer;
begin
    while not Terminated do begin
        Sleep(3000);
    end;
end;

initialization

     InitializeCriticalSectionAndSpinCount(TermProperty, 128);

finalization

     DeleteCriticalSection(TermProperty);

end.
