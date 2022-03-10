unit tks_server;

interface

uses
    SysUtils, classes, tks_TLB, windows, tks_eventtypes, comobj, tks_serverintf, widestrings, modulesintf;

type

    TDLLInfo = record
       FileName : String;
       hDLL     : THandle;
       Autoload_Enabled : boolean;
       Autoloaded : boolean;
       InList : boolean;
    end;

    PDLLInfo = ^TDLLInfo;

    TLoadMode = (lmFileNameFirst, lmFileNameLast);

    TAppServer = class(TInterfacedObject, ITKSServer, ITKSServer2, ITKSSafeLoadModule, ITKSConfig)
    private
        FModuleList : TInterfaceList;
        FDLLGUIDs : TStringList;
        FGUIDS : TStrings;
        FManagers : TInterfaceList;
        FHandle : LongInt;
        FEvents : TStrings;
        FIConfig : ITKSConfig;
        FAutoLoad : boolean;
        FLoadFromFile : Boolean;
        FModulesDir : string;
        {$IFDEF INTERNALMODULES}
        FObjectNames : TStrings;
        FObjectRefs : TInterfaceList;
        {$ENDIF}
        procedure GetCLSIDsFromDLL(FileName : String);
        procedure GetAvailableModules(Path : String);
        procedure UnloadDLLs;
        procedure AutoLoadModules;
        function InternalLoadModules(List : TWideStringList; const mode : TLoadMode) : HResult;
        function CreateComObjectFromInfo(MID : TGUID; Info : PDLLinfo; out module : IUnknown) : boolean;
        function CreateInternalObject(MID : TGUID; out obj : IUnknown): boolean;
        function ExecuteEventList(const EventName: WideString; List : TInterfaceList; res : HResult) : HResult;
    public
        function  LoadModules: HResult; stdcall;
        function  UnloadModules: HResult; stdcall;
        function  Get_ModuleCount: Integer; stdcall;
        function  Get_Module(index: Integer): IUnknown; stdcall;
        function  CompCode: WideString; stdcall;
        function  LoadModule(MID: TGUID): ITKSModule; stdcall;
        procedure  LoadModuleX(MID: TGUID;
                               var Result : ITKSModule;
                               const AllowAutoLoad : boolean = True;
                               const Load2 : boolean = False;
                               const LoadParam : LongInt = 0;
                               const shwmsg : boolean = True);
        function  Get_ApplicationHandle(out Value: Integer): HResult; stdcall;
        function  Set_ApplicationHandle(Value: Integer): HResult; stdcall;
        function  StartServer(Load: Integer): HResult; stdcall;
        function  StopServer: HResult; stdcall;
        function  RegisterManager(const Manager: IUnknown): HResult; stdcall;
        function  RegisterEvent(const EventName: WideString; const IAction: ITKSAction): HResult; stdcall;
        function  ExecuteEvent(const EventName: WideString): HResult; stdcall;
        // ITKSServer2
        function LoadModuleParam(MID: TGUID; LoadParam : LongInt) : ITKSModule; stdcall;
        function CreateComObjectFromFile(MID : TGUID) : IUnknown;
        // ITKSSafeLoadModule
        function SafeLoadModule(MID: TGUID) : ITKSModule; stdcall;
    public
        constructor CreateWithConfig(IConfig : ITKSConfig; const AllowAutoLoad : boolean = True; const LoadFromFile : boolean = False; const modulesdir:string = '');
        destructor Destroy; override;
        function QueryInterface(const IID: TGUID; out Obj): HResult; stdcall;
    public
        property config : ITKSConfig read FIConfig implements ITKSConfig;
    end;

implementation

uses
    compcode, tks_event, dialogs, ActiveX
    {$IFDEF INTERNALMODULES}
    , comserv
    {$ENDIF}
    // Поддержка автозагрузки
    , tks_autoloadintf
    , tks_module_names
;


function TAppServer.CreateComObjectFromInfo(MID : TGUID; Info : PDLLinfo; out module : IUnknown) : boolean;
const
  IID_Factory : TGUID = '{00000001-0000-0000-C000-000000000046}';
type
  TDllGetClassObject = function(const CLSID, IID: TGUID; var Obj): HResult; stdcall;
var
  DllGetClassObject : TDllGetClassObject;
  ClassFactory      : IClassFactory;
begin
    Result := False;
    if Info^.hDLL = 0 then
      Info^.hDLL := LoadLibrary(PChar(Info^.FileName));

    if Info^.hDLL <> 0 then
      try
          @DllGetClassObject := GetProcAddress(Info^.hDLL, 'DllGetClassObject');
          if Addr(DllGetClassObject) = nil then Exit;
          if DllGetClassObject(MID, IID_Factory, ClassFactory) <> S_OK then Exit;
          ClassFactory.CreateInstance(nil, IUnknown, module);
          ClassFactory := nil;
          Result := module <> nil;
      finally
          if module = nil then
              raise Exception.CreateFmt('Класс %s не найден в библиотеке %s', [GUIDToString(MID), Info^.FileName]);
      end;
end;

function TAppServer.CreateComObjectFromFile(MID : TGUID) : IUnknown;
var
  Indx              : Integer;
  Info              : PDLLInfo;
begin
  Result := nil;

  {$IFDEF INTERNALMODULES}
  Indx := FObjectNames.IndexOf(GUIDToString(MID));
  if Indx <> -1 then begin
    FObjectRefs[Indx].QueryInterface(IUnknown, Result);
    Exit;
  end;
  {$ENDIF}


  Indx := FDLLGUIDs.IndexOf(GUIDToString(MID));

  if Indx <> -1 then
    begin
      Info := PDLLInfo(FDLLGUIDs.Objects[Indx]);
      CreateComObjectFromInfo(MID, Info, Result);
    end
  else if not CreateInternalObject(MID, Result) then
    raise ENoModuleForCLSID.CreateFmt('Класс %s не найден в списке модулей', [GUIDToString(MID)]);
  {$IFDEF INTERNALMODULES}
  if Result <> nil then begin
       FObjectNames.Add(GUIDToString(MID));
       FObjectRefs.Add(Result);
  end;
  {$ENDIF}
end;

function TAppServer.CreateInternalObject(MID : TGUID; out obj : IUnknown): boolean;
var
    factory : TComObjectFactory;
    ClassFactory : IClassFactory;
begin
    Result := False;
    Obj := nil;
    {$IFDEF INTERNALMODULES}
    factory := ComClassManager.GetFactoryFromClassID(MID);
    if factory <> nil then begin
        if factory.GetInterface(IClassFactory, ClassFactory) then begin
            ClassFactory.CreateInstance(nil, IUnknown, obj);
            Result := True;
        end;
    end;
    {$ENDIF}
end;

constructor TAppServer.CreateWithConfig(IConfig : ITKSConfig; const AllowAutoLoad : boolean = True; const LoadFromFile : boolean = False; const modulesdir:string = '');
begin
    Inherited Create;
    FIConfig := IConfig;
    FModuleList := TInterfaceList.Create;
    FDLLGUIDs := TStringList.Create;
    FGUIDS := TStringList.Create;
    FManagers := TInterfaceList.Create;
    FEvents := TStringList.Create;
    FAutoLoad := AllowAutoLoad;
    FLoadFromFile := LoadFromFile;
    FModulesDir := ModulesDir;
    {$IFDEF INTERNALMODULES}
    FObjectNames := TStringList.Create;
    FObjectRefs := TInterfaceList.Create;
    {$ENDIF}
    if FModulesDir = emptyStr then
        FModulesDir := ExtractFileDir(ParamStr(0)) + '\modules\';
    if FLoadFromFile then
        GetAvailableModules(FModulesDir);
end;

destructor TAppServer.Destroy;
var
   i : Integer;
begin

    {$IFDEF INTERNALMODULES}
    FObjectRefs.Free;
    FObjectNames.Free;
    {$ENDIF}

    for i := 0 to FEvents.Count - 1 do
        FEvents.Objects[i].Free;
    FEvents.Free;
    FIConfig := nil;
    FModuleList.Free;

    UnloadDLls;

    FDLLGUIDs.Free;
    FGUIDS.Free;
    FManagers.Free;
    Inherited;
end;

procedure TAppServer.GetCLSIDsFromDLL(FileName : String);
type
  TGetModuleCLSIDs = function(CLSID : PGUID; var Count : Integer): HResult; stdcall;
var
  hDLL            : THandle;
  GetModuleCLSIDs : TGetModuleCLSIDs;
  ModuleCLSID     : array[0..$20] of TGUID;
  Info            : PDLLInfo;
  Count           : Integer;
  i               : Integer;
begin
  hDLL := LoadLibrary(PChar(FileName));
  try
    @GetModuleCLSIDs := GetProcAddress(hDLL, 'GetModuleCLSIDs');
    if Addr(GetModuleCLSIDs) = nil then Exit;
    GetModuleCLSIDs(@ModuleCLSID[0], Count);

    New(Info);
    Info^.FileName := FileName;
    Info^.hDLL := 0;
    Info^.Autoload_Enabled := False;
    Info^.Autoloaded := False;
    Info^.InList := False;

    for i := 0 to Count - 1 do begin
        if IsEqualGUID(ModuleCLSID[i], CLASS_AUTOLOAD_MANAGER) then
            Info^.Autoload_Enabled := True
        else begin
            FDLLGUIDs.AddObject(GUIDToString(ModuleCLSID[i]), Pointer(Info));
            Info^.InList := True;
        end;
    end;
    // Если мы не добавили информацию в список, то это означает, что в DLL нет других модулей.
    if not Info^.InList then
        Dispose(Info);

  finally
    FreeLibrary(hDLL);
  end;
end;

procedure TAppServer.GetAvailableModules(Path : String);
var
  SR        : TSearchRec;
begin
  if FindFirst(Path + '*.dll', faAnyFile, SR) = 0 then
    begin
      repeat
        GetCLSIDsFromDLL(Format('%s%s', [Path, SR.Name]));
      until FindNext(SR) <> 0;
      SysUtils.FindClose(SR);
    end;
end;

procedure TAppServer.UnloadDLLs;
type
  TDllCanUnloadNow = function : HResult; stdcall;
var
  i : Integer;
  Info : PDLLInfo;
  DllCanUnloadNow : TDllCanUnloadNow;
begin
  while FDLLGUIDs.Count > 0 do
    begin
      // Поскольку разным CLSID может соответствовать одна DLL, сначала удаляем
      // из списка повторяющиеся ссылки, а затем один раз освобождаем память,
      // выделенную под TDLLInfo и выгружаем DLL
      Info := PDLLInfo(FDLLGUIDs.Objects[FDLLGUIDs.Count - 1]);
      for i := FDLLGUIDs.Count - 1 downto 0 do
        if PDLLInfo(FDLLGUIDs.Objects[i]) = Info then
          FDLLGUIDs.Delete(i);

      if Info^.hDLL <> 0 then
        begin
          @DllCanUnloadNow := GetProcAddress(Info^.hDLL, 'DllCanUnloadNow');
          if Addr(DllCanUnloadNow) <> nil then
            if DllCanUnloadNow = S_FALSE then
              raise Exception.CreateFmt('Внимание! Не удалось выгрузить модуль %s', [Info^.FileName]);

          FreeLibrary(Info^.hDLL);
        end;

      Dispose(Info);
    end;
end;

type
   TModuleInfo = record
      IModule : ITKSModule;
      ModuleIndex : Integer;
   end;

   PModuleInfo = ^TModuleInfo;

function ModuleIndexCompare(Item1, Item2: Pointer): Integer;
begin
    Result := PModuleInfo(Item1)^.ModuleIndex - PModuleInfo(Item2)^.ModuleIndex;
end;

function TAppServer.UnloadModules: HResult;
var
   i : Integer;
   List : TList;
   mi : PModuleInfo;
begin
  List := TList.Create;
  try
     for i := 0 to FModuleList.Count - 1 do begin
         new(mi);
         if FModuleList[i].QueryInterface(ITKSModule, mi^.IModule) = S_OK then begin
            mi^.ModuleIndex := (FModuleList[i] as ITKSModule).getIndex;
            List.Add(mi);
         end else
            Dispose(mi);
     end;
     List.Sort(ModuleIndexCompare);
     FModuleList.Clear;
     FGUIDS.Clear;
     for i := 0 to List.Count - 1 do begin
         mi := PModuleInfo(List[i]);
         mi^.IModule := nil;
         Dispose(mi);
     end;

  finally
     List.Free;
  end;

  Result := S_OK;
end;

function TAppServer.Get_ModuleCount: Integer;
begin
    Result := FModuleList.Count;
end;

function TAppServer.Get_Module(index: Integer): IUnknown;
begin
    FModuleList[index].QueryInterface(IUnknown, Result);
end;

function TAppServer.CompCode: WideString;
begin
    Result := __CC__;
end;

procedure TAppServer.LoadModuleX(MID: TGUID;
                                 var Result : ITKSModule;
                                 const AllowAutoLoad : boolean = True;
                                 const Load2 : boolean = False;
                                 const LoadParam : LongInt = 0;
                                 const shwmsg : boolean = True);
var
   obj  : IUnknown;
   i    : Integer;
   m2   : ITKSModule2;
begin
    Result := nil;
    obj := nil;
    i := FGUIDS.IndexOf(GUIDToString(MID));
    if i <> -1 then begin
        FModuleList[i].QueryInterface(ITKSModule, Result);
        Exit;
    end;
    try
        if FLoadFromFile then
            Obj := CreateComObjectFromFile(MID)
        else
            Obj := CreateComObject(MID);

        FModuleList.Add(obj);
        FGUIDS.Add(GUIDToString(MID));
        Obj.QueryInterface(ITKSModule, Result);
        if Load2 then begin
           if Result.queryInterface(ITKSModule2, m2) = S_OK then begin
               m2.setServerParam(self, LoadParam);
               Exit;
           end;
        end;
        Result.setServer(self);
    except
        on E : Exception do begin
            if shwmsg then
                MessageDlg(Format('Внимание! Не могу загрузить модуль "%s".'#13#10'Текст ошибки: "%s"', [get_module_name(MID), e.message]), mtError, [mbOK], 0)
            else
                raise
        end;
    end;
end;

function TAppServer.LoadModule(MID: TGUID): ITKSModule;
begin
    LoadModuleX(MID, Result, FAutoLoad);
end;

function TAppServer.Get_ApplicationHandle(out Value: Integer): HResult;
begin
    Result := S_OK;
    Value := FHandle;
end;

function TAppServer.Set_ApplicationHandle(Value: Integer): HResult;
begin
    Result := S_OK;
    FHandle := Value;
end;

function TAppServer.StartServer(Load: Integer): HResult;
begin
    Result := E_FAIL;
    if FAutoLoad then
        Result := LoadModules
end;

function TAppServer.StopServer: HResult;
begin
    ExecuteEvent(EVENT_BEFORCLEARMANAGERS);
    {$IFDEF INTERNALMODULES}
    FObjectRefs.clear;
    FObjectNames.clear;
    {$ENDIF}
    FManagers.Clear;
    ExecuteEvent(EVENT_BEFORESTOPSERVER);
    ExecuteEvent(EVENT_STOPSERVER);
    UnloadModules;
    Result := S_OK;
end;

function TAppServer.RegisterManager(const Manager: IUnknown): HResult;
begin
     Result := E_FAIL;
     if Manager <> nil then begin
         FManagers.Add(Manager);
         Result := S_OK;
     end;
end;

function TAppServer.RegisterEvent(const EventName: WideString; const IAction: ITKSAction): HResult;
var
   List : TInterfaceList;
   Index : Integer;
begin
    Result := S_OK;
    Index := FEvents.IndexOf(EventName);
    if Index <> -1 then begin
       List := TInterfaceList(FEvents.Objects[index]);
       List.Add(IAction);
    end else begin
       List := TInterfaceList.Create;
       List.Add(IAction);
       FEvents.AddObject(EventName, List);
    end;
end;

function TAppServer.ExecuteEventList(const EventName: WideString; List : TInterfaceList; res : HResult) : HResult;
const
    arr_bool : array [boolean] of HResult = (E_FAIL, S_OK);
var
   i : Integer;
   param : ITKSEventParam;
   r : boolean;
   ir : Integer;
   evt: ITKSEvent;
   act : ITKSAction;
begin
    r := res = S_OK;
    for i := 0 to List.Count - 1 do try
        param := TTKSEventParam.Create;
        param.Set_Result(S_OK);
        if List[i].QueryInterface(ITKSEvent, evt) = S_OK then
            evt.FireEvent(EventName, '', param)
        else if List[i].QueryInterface(ITKSAction, act) = S_OK then
            act.DoAction(param);
        param.Get_Result(ir);
        r := r and (ir = S_OK);
        param := nil;
    except
      {$IFDEF INTERNALMODULES}
      raise;
      {$ELSE}
      on E : Exception do
        ShowMessage(E.Message);
      {$ENDIF}
    end;
    Result := arr_bool[r];
end;

function TAppServer.ExecuteEvent(const EventName: WideString): HResult;
var
   Index : Integer;
begin
    Result := S_OK;
    if FEvents = nil then begin
       Result := E_FAIL;
       Exit;
    end else begin
       Index := FEvents.IndexOf(EventName);
       if Index <> -1 then begin
          Result := ExecuteEventList(EventName, TInterfaceList(FEvents.Objects[index]), S_OK);
       end;
       Index := FEvents.IndexOf(EVENT_ANY);
       if Index <> -1 then begin
          Result := ExecuteEventList(EventName, TInterfaceList(FEvents.Objects[index]), Result);
       end;
    end;
end;

function TAppServer.QueryInterface(const IID: TGUID; out Obj): HResult; stdcall;
var
   i : Integer;
begin
//   if IsEqualGUID(IID, ITKSShowConfigWindow) then asm
//        int 3;
//   end;
   Result := inherited QueryInterface(IID, Obj);
   if (Result <> S_OK) then
      for i := 0 to FManagers.Count - 1 do begin
          Result := FManagers.Items[i].QueryInterface(IID, Obj);
          if Result = S_OK then
             Break;
      end;
   if (Result <> S_OK) then
      for i := 0 to FModuleList.Count - 1 do begin
          Result := FModuleList.Items[i].QueryInterface(IID, Obj);
          if Result = S_OK then
             Break;
      end;
end;

function TAppServer.LoadModuleParam(MID: TGUID; LoadParam : LongInt) : ITKSModule;
begin
     LoadModuleX(MID, Result, FAutoLoad, True, LoadParam);
end;

function TAppServer.SafeLoadModule(MID: TGUID) : ITKSModule;
begin
    LoadModuleX(MID, Result, FAutoLoad, False, 0, False);
end;

function TAppServer.InternalLoadModules(list : TWideStringList; const mode : TLoadMode) : HResult;
var
    i : Integer;
    aname, avalue, filename : WideString;
    mid: TGUID;
    idialogs : ITKSDialogs;
begin
    for i := 0 to list.count - 1 do begin
        case mode of
        lmFileNameLast : begin
            avalue := list.names[i];
            aname := list.values[avalue];
        end;
        else begin
            aname := list.names[i];
            avalue := list.values[aname];
        end;
        end;
        if (aname <> '') and (avalue <> '') then begin
           try
               if FLoadFromFile then begin
                   filename := ExpandFileName(aname);
                   if not FileExists(filename) then
                      continue;
                   GetCLSIDsFromDLL(filename);
               end;
               if Succeeded(CLSIDFromString(PWideChar(avalue), mid)) then
                   SafeLoadModule(mid);
           except on e : Exception do
               if QueryInterface(ITKSDialogs, idialogs) = S_OK then
                   idialogs.warning(WideFormat('Внимание! Ошибка загрузки модуля %s. '#13#10'%s', [aname, e.message]));
           end;
        end;
    end;
    Result  := S_OK;
end;

// Автоматическая загрузка модулей, прописанных в папке Модули в программе
function TAppServer.LoadModules: HResult;
const
    modules_section_name : WideString = 'Модули';
var
    list : TWideStringList;
begin
    Result := E_FAIL;
    if FIConfig <> nil then begin
        list := TWideStringList.Create;
        try
            list.Text := FIConfig.readsection(modules_section_name);
            InternalLoadModules(List, lmFileNameFirst);
            list.Text := FIConfig.readsection('..\' + modules_section_name);
            InternalLoadModules(List, lmFileNameLast);
            Result := S_OK;
        finally
            list.Free;
        end;
    end;
    AutoLoadModules;    
end;

procedure TAppServer.AutoLoadModules;
var
    i : Integer;
    Info : PDLLInfo;
    module : IUnknown;
    manager : ITKSAutoloader;
    idialogs : ITKSDialogs; 
begin
    if FLoadFromFile then begin
        for i := 0 to (FDLLGUIDs.Count) - 1 do begin
            Info := PDLLInfo(FDLLGUIDs.Objects[i]);
            if Info^.Autoload_Enabled and not Info^.Autoloaded then begin
                Info^.Autoloaded := True;
                try
                    if not CreateComObjectFromInfo(CLASS_AUTOLOAD_MANAGER, Info, module) then
                        continue;
                except
                    if QueryInterface(ITKSDialogs, idialogs) = S_OK then
                        idialogs.warning(WideFormat('Внимание!'#13#10'Модуль "%s" не поддерживает функцию автозагрузки.' +
                                                    #13#10'Возможно вам следует обновить его.', [info^.FileName]));
                    continue;
                end;
                if supports(module, ITKSAutoloader, manager) then
                    manager.LoadModules(Self);
            end;
        end;
    end;
end;

initialization

    {$IFDEF INTERNALMODULES}
    ComServer.UIInteractive := False;
    {$ENDIF}

finalization

end.
