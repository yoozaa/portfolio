unit whatsapp_pythonthread;

interface

uses classes, SysUtils, PythonEngine, windows, SyncObjs, WideStrings
     , uceftypes, uCEFInterfaces, uCEFTask, uCEFMiscFunctions, uCEFv8Value;

type

    IWAppJobInfo = interface
    ['{AB922EAD-9F52-49EB-AB32-32640C14D523}']
        function get_url : ustring;
        function get_method : ustring;
        function get_field_count : Integer;
        function get_field_name(const i : Integer) : AnsiString;
        function get_field_value(const i : Integer) : ustring;
    end;

    TWappJobInfo = class(TInterfacedObject, IWAppJobInfo)
    private
        FUrl : ustring;
        FMethod : ustring;
        FKeys : TStrings;
        FValues : TWideStrings;
    private
        procedure convert_value(value : ICefv8Value);
    public
        constructor CreateWith(value : ICefv8Value);
        destructor Destroy;
    public
        function get_url : ustring;
        function get_method : ustring;
        function get_field_count : Integer;
        function get_field_name(const i : Integer) : AnsiString;
        function get_field_value(const i : Integer) : ustring;
    end;

    IWappJob = interface
    ['{86C6B03C-782C-4E58-9F63-D64C376707FE}']
        function data : IWAppJobInfo;
        procedure run_callbacks(context : ICefv8Context; code : Integer; statustext : ustring);
    end;

    TWappJob = class(TInterfacedObject, IWappJob)
    private
        FData : IWAppJobInfo;
        FCallBack : ICefv8Value;
    public
        constructor CreateWith(data : IWAppJobInfo; callback : ICefv8Value);
        destructor Destroy; override;
    public
        function data : IWAppJobInfo;
        procedure run_callbacks(context : ICefv8Context; code : Integer; statustext : ustring);
    end;

    TWappPythonThread = class(TThread)
    private
        ListLock : TRTLCriticalSection;
        Jobs : TInterfaceList;
        FManager : Variant;
        FContext : ICefv8Context;
        FInterSleep : real;
        JobEvent : TEvent;
        procedure ClearList;
        procedure acquire;
        procedure release;
    protected
        procedure Execute; override;
        procedure DoJob;
        function ProcessJob(job : IWappJob) : boolean;
    public
        constructor CreateWith(CreateSuspended : boolean; Manager : Variant; context : ICefv8Context; const intersleep : real);
        destructor Destroy; override;
    public
        procedure AddJob(Job : IWappJob);
    end;

    TJobCallback = class(TCefTaskOwn)
    private
      FCode : Integer;
      FStatusText : ustring;
      FCallBack : ICefv8Value;
      FContext : ICefv8Context;
    protected
      procedure Execute; override;
    public
      constructor CreateWith(callback : ICefv8Value; context : ICefv8Context; code : Integer; statustext : ustring);
      destructor Destroy; override;
    end;

implementation

uses whatsapp_value, varpyth, variants;

constructor TWappJobInfo.CreateWith(value : ICefv8Value);
begin
    Inherited Create;
    FKeys := TStringList.Create;
    FValues := TWideStringList.Create;
    convert_value(value);
end;

destructor TWappJobInfo.Destroy;
begin
    FKeys.Free;
    FValues.Free;
    Inherited;
end;

procedure TWappJobInfo.convert_value(value : ICefv8Value);
var
    i : Integer;
    data : ICefv8Value;
begin
    FUrl := get_key_value(value, 'url');
    FMethod := get_key_value(value, 'type');
    if value.HasValueByKey('data') then begin
        data := value.GetValueByKey('data');
        data.GetKeys(FKeys);
        for i := 0 to FKeys.Count - 1 do
            FValues.Add(get_key_value(data, FKeys[i]));
    end;
end;

function TWappJobInfo.get_url : ustring;
begin
    Result := FUrl;
end;

function TWappJobInfo.get_method : ustring;
begin
    Result := FMethod;
end;

function TWappJobInfo.get_field_count : Integer;
begin
    Result := FKeys.Count;
end;

function TWappJobInfo.get_field_name(const i : Integer) : AnsiString;
begin
    Result := FKeys[i];
end;

function TWappJobInfo.get_field_value(const i : Integer) : ustring;
begin
    Result := FValues[i];
end;

constructor TWappPythonThread.CreateWith(CreateSuspended : boolean; Manager : Variant; context : ICefv8Context; const intersleep : real);
begin
    Inherited Create(CreateSuspended);
    InitializeCriticalSection(ListLock);
    Jobs := TInterfaceList.Create;
    FManager := Manager;
    FContext := context;
    FInterSleep := interSleep;
    JobEvent := TEvent.Create(nil, true, false, 'jobs.event');
end;

destructor TWappPythonThread.Destroy;
begin
    Jobs.Free;
    JobEvent.Free;
    FManager := Null;
    FContext := nil;
    DeleteCriticalSection(ListLock);
    Inherited;
end;

procedure TWappPythonThread.acquire;
begin
    EnterCriticalSection(ListLock);
end;

procedure TWappPythonThread.release;
begin
    LeaveCriticalSection(ListLock);
end;

procedure TWappPythonThread.ClearList;
var
    i : Integer;
begin
    acquire;
    for i := 0 to Jobs.Count - 1 do
        Jobs[i] := nil;
    release;
end;

procedure TWappPythonThread.Execute;
begin
    while not Self.Terminated do begin
        acquire;
        if Jobs.Count > 0 then begin
            release;
            DoJob;
            // Задержка для того, чтобы время приема различалось на сервере на 1 секунду
            if (FInterSleep > 0) and (Jobs.Count > 0) then
                JobEvent.WaitFor(trunc(FInterSleep * 1000));
        end else begin
            JobEvent.ResetEvent;
            release;
            JobEvent.WaitFor(1000);
        end;
    end;
end;

procedure TWappPythonThread.DoJob;
var
    job : IWAppJob;
    r : boolean;
begin
    r := True;
    acquire;
    try
        Jobs[0].QueryInterface(IWAppJob, job);
    finally
        release;
    end;
    r := ProcessJob(job);
    acquire;
    try
        if r then
            Jobs.Delete(0)
        else
            JobEvent.ResetEvent;
    finally
        release;
    end;
    if not r then
        JobEvent.WaitFor(500);
end;

function TWappPythonThread.ProcessJob(job : IWappJob) : boolean;
const
    CODE_CONNECTION_ERROR = 602;
    CODE_OK_MIN = 200;
    CODE_OK_MAX = 300;
var
    r : Variant;
    gstate : PyGILState_STATE;
    data : PPyObject;
    i : Integer;
    code : Integer;
    p : PPyObject;
begin
    Result := True;
    gstate := GetPythonEngine.PyGILState_Ensure();
    try
        with GetPythonEngine do begin
             data := PyDict_New;
             for i := 0 to job.data.get_field_count() - 1 do begin
                 p := PyUnicode_FromWideString(job.data.get_field_value(i));
                 PyDict_SetItemString(data, PAnsiChar(job.data.get_field_name(i)), p);
                 Py_DECREF(p);
             end;
        end;
        r := fmanager.ajax_post(
            VarPythonCreate(GetCurrentThreadID()),
            VarPythonCreate(job.data.get_url),
            VarPythonCreate(job.data.get_method),
            VarPythonCreate(VarPythonCreate(data))
        );
        code := r.getitem(0);
        Result := ((code >= CODE_OK_MIN) and (code < CODE_OK_MAX)) or ((code >= 400) and (code < 500));
        job.run_callbacks(fcontext, code, r.getitem(1));
    finally
        GetPythonEngine.PyGILState_Release(gstate);
    end;
end;


procedure TWappPythonThread.AddJob(Job : IWappJob);
begin
    acquire;
    try
        Jobs.add(job);
    finally
        release;
    end;
end;


constructor TWappJob.CreateWith(data : IWAppJobInfo; callback : ICefv8Value);
begin
    Inherited Create;
    FData := data;
    FCallBack := callback;
end;

destructor TWappJob.Destroy;
begin
    FData := nil;
    FCallBack := nil;
    Inherited;
end;

function TWappJob.data : IWAppJobInfo;
begin
    Result := FData;
end;

procedure TWappJob.run_callbacks(context : ICefv8Context; code : Integer; statustext : ustring);
var
    func : ICefv8Value;
    args: TCefv8ValueArray;
begin
    if FCallback <> nil then
        CefPostTask(TID_RENDERER, TJobCallback.CreateWith(FCallBack, context, code, statustext));
end;

{TJobCallback}

procedure TJobCallback.Execute;
var
    func : ICefv8Value;
    args: TCefv8ValueArray;
    arg : ICefv8Value;
    l : TStrings;
begin
    if FCallback <> nil then begin
        fcontext.Enter;
        if FCallBack.HasValueByKey('always') then begin
            func := FCallBack.GetValueByKey('always');
            arg := TCefv8ValueRef.NewObject(nil, nil);
            arg.SetValueByKey('code', TCefv8ValueRef.NewInt(fcode), 0);
            arg.SetValueByKey('status', TCefv8ValueRef.NewString(fstatustext), 0);
            SetLength(args, 1);
            args[0] := arg;
            func.ExecuteFunctionWithContext(fcontext, nil, args);
        end;
        fcontext.Exit;
    end;
end;

constructor TJobCallback.CreateWith(callback : ICefv8Value; context : ICefv8Context; code : Integer; statustext : ustring);
begin
    Inherited Create;
    fcallback := callback;
    fcontext := context;
    fcode := code;
    fstatustext := statustext;
end;

destructor TJobCallback.Destroy;
begin
    fcallback := nil;
    fcontext := nil;
    inherited;
end;

end.
