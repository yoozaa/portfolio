unit tkshtml_func;

interface

procedure init_func;

implementation

uses SysUtils, PythonEngine, tkshtml_main, registry, tkscom, windows,
  tkshtml_data, tkshtml_appmanager, VarPyth, Forms
  , tks_tlb, modulesintf, windowhistory, controls
  , htmlayout_dom_h, classes, htmlayout_h, WideStrUtils
  , htmlayoutvalues, tks_hosts, tkshtml_host, htmlayout_behavior_h
  , jclDateTime, shellapi, tks_windowtypes, express_passwd, compcode, pylayout, pyHtml
  , tks_log
  , tkshtml_dialog, pycfgpage, tkshtml_intf
  , TKSImage, PNGImage;


type
   EPyHtmlayoutError = class(EPyStandardError);

var
   Server_QueryInterface : function (const IID: TGUID; out Obj): HResult; stdcall;


procedure get_root_manager(var r : ITKSWindowManager);
begin
     if tkscom.MainServer <> nil then
        tkscom.MainServer.QueryInterface(ITKSWindowManager, r)
     else if Assigned(Server_QueryInterface) then
        Server_QueryInterface(ITKSWindowManager, r);
end;

function get_config_manager : ITKSConfig;
begin
    if (tkscom.MainServer <> nil) then
       tkscom.MainServer.QueryInterface(ITKSConfig, Result)
    else if Assigned(Server_QueryInterface) then
       Server_QueryInterface(ITKSConfig, Result)
    else
        Result := nil;
end;

function get_configx: ITKSConfigX;
begin
    if (tkscom.MainServer <> nil) then
       tkscom.MainServer.QueryInterface(ITKSConfigX, Result)
    else if Assigned(Server_QueryInterface) then
       Server_QueryInterface(ITKSConfigX, Result)
    else
        Result := nil;
end;

function get_appinfo : ITKSAppInfo;
begin
    if (tkscom.MainServer <> nil) then
       tkscom.MainServer.QueryInterface(ITKSAppInfo, Result)
    else if Assigned(Server_QueryInterface) then
       Server_QueryInterface(ITKSAppInfo, Result)
    else
        Result := nil;
end;

function get_window_manager(html : Variant; const modal : boolean; const iwindow : ITKSWindowManager; var creatednew : Pointer) : ITKSWindowManager;
var
   hm : THostManager;
begin
   Result := nil;
   creatednew := nil;
   if iwindow <> nil then begin
      Result := iwindow;
      exit;
   end;
   hm := get_host_manager(TfmHTMLHost, True);
   Result := hm.get_host(html, False, creatednew, boolean(html.create_new_window));
   if not Assigned(Result) then begin
      if modal and not VarIsNone(html) then
         Result := hm.get_host(html, True, creatednew)
      else if iwindow <> nil then
         Result := iwindow
      else
         get_root_manager(Result);
   end;
end;

procedure init_app_handle;
const
   hear : boolean = False;
var
   m : Variant;
begin
   if hear then Exit;
   hear := True;
   m := import('gtd');
   Application.Handle := m.system.getapphandle();
end;

function init_application() : boolean;
begin
  init_app_handle;
  Result := True;
end;

function get_appmanager(HTMLManager : Variant; wm : ITKSWindowManager; const SavePrior : boolean; const DefaultWindow : boolean) : ITKSShowWindow;
var
   appselector : ITKSAppSelector;
   iHTML : IHTMLManager;
begin
    Result := nil;
    if (wm.QueryInterface(ITKSAppSelector, appselector) = S_OK) and
       (appselector.getAppManager(IHTMLManager, iHTML) = S_OK)
    then begin
        iHTML.set_params(HTMLManager, SavePrior);
        iHTML.QueryInterface(ITKSShowWindow, Result);
    end else
       Result := THTMLAppManager.Create(HTMLManager, wm, SavePrior, DefaultWindow);
end;

type
   tapp_info = record
      wm : ITKSWindowManager;
      res : Integer;
      HTMLManager : Variant;
      modal : boolean;
      saveprior : boolean;
      defaultwindow : boolean;
      result : TModalResult;
   end;

   Papp_info = ^tapp_info;

const EXPRESS_ATTR_NAME = 'express';

function show_config_html(const param : LongInt) : boolean; stdcall;
const
   arr : array [boolean] of integer = (0, 1);
var
   app : ITKSApp;
   iShowWindow : ITKSShowWindow;
   iWindow : ITKSWindow;
begin
   Result := True;
   with Papp_info(param)^ do begin
      {$IFNDEF NOREG}
      if GetPythonEngine.PyObject_HasAttrString(ExtractPythonObjectFrom(HTMLManager), EXPRESS_ATTR_NAME) <> 0 then begin
         if check_passwd() <> check_result() then
            Exit;
      end;
      {$ENDIF}
      iShowWindow := get_appmanager(HTMLManager, wm, saveprior, defaultwindow);
      if wm.QueryInterface(ITKSApp, app) = S_OK then
         res := app.run(arr[modal], iShowWindow)
      else
          iShowWindow.ShowWindow(I_NOWINDOW, iWindow);
   end;
end;

function showhtml(HTMLManager : Variant; const modal : boolean = False;
                  const iwindow : ITKSWindowManager = nil;
                  const config_mode : boolean = False;
                  const saveprior : boolean = False;
                  const defaultwindow : boolean = False) : Integer;
var
   created : Pointer;
   p : Papp_info;
   cfg : ITKSShowConfigWindow;
   root_wm : ITKSWindowManager;
begin
    Result := 0;
    if not init_application() then Exit;
    if iwindow <> nil then begin
       // не знаю
       // в принципе если у нас есть уже iwindow то зачем все эти навороты
       // с TAppManager ?
       iwindow.DockWindow(TfmHTMLView.CreateWithManager(HTMLManager, iwindow));
       Exit;
    end;
    created := nil;
    new(p);
    try
       p^.wm := get_window_manager(HTMLManager, modal, iwindow, created);
       p^.HTMLManager := HTMLManager;
       p^.res := 0;
       p^.modal := modal and (created <> nil);
       p^.saveprior := saveprior;
       p^.defaultwindow := defaultwindow;
       root_wm := nil;
       if config_mode then
          get_root_manager(root_wm);
       if (root_wm <> nil) and (root_wm.QueryInterface(ITKSShowConfigWindow, cfg) = S_OK) then
          cfg.showconfigwindow(@show_config_html, LongInt(p))
       else if config_mode and supports(MainServer, ITKSShowConfigWindow, cfg) then 
          cfg.showconfigwindow(@show_config_html, LongInt(p))
       else
          show_config_html(LongInt(p));
       Result := p^.res;
    finally
       dispose(p);
       if created <> nil then
          get_host_manager(TfmHTMLHost, True).remove_host(created);
    end;
end;

function _showhtml ( self, args : PPyObject ) : PPyObject; cdecl;
var
   o : PPyObject;
   modal, config_mode, saveprior, defaultwindow: PPyObject;
   iUnkn : Integer;
   wm : ITKSWindowManager;
begin
  with GetPythonEngine do
    begin
      modal := nil;
      config_mode := nil;
      saveprior := nil;
      defaultwindow := nil;
      wm := nil;
      iUnkn := 0;
      PyArg_ParseTuple( args, 'O|OiOOO', @o, @modal, @iUnkn, @config_mode, @saveprior );
      if iUnkn > 0 then
         IUnknown(iUnkn).QueryInterface(ITKSWindowManager, wm);
      Result := VariantAsPyObject(showhtml(VarPythonCreate(o),
                                  not Assigned(modal) or PyBool_Check(modal) and (PyObject_IsTrue(modal) = 1),
                                  wm,
                                  (config_mode = nil) or (PyObject_IsTrue(config_mode) = 1),
                                  (saveprior = nil) or (PyObject_IsTrue(saveprior) = 1),
                                  (defaultwindow <> nil) and (PyObject_IsTrue(defaultwindow) = 1)
                                  ));
    end;
end;

const
    ucount : Integer = 0;


function CheckRez(rez: integer): boolean;
begin
    with GetPythonEngine do begin
        if rez <> HLDOM_OK then begin
            case rez of
              HLDOM_INVALID_HWND: PyErr_SetString(PyExc_Exception^, 'HLDOM_INVALID_HWND');
              HLDOM_INVALID_HANDLE: PyErr_SetString(PyExc_Exception^, 'HLDOM_INVALID_HANDLE');
              HLDOM_PASSIVE_HANDLE: PyErr_SetString(PyExc_Exception^, 'HLDOM_PASSIVE_HANDLE');
              HLDOM_INVALID_PARAMETER: PyErr_SetString(PyExc_Exception^, 'HLDOM_INVALID_PARAMETER');
              HLDOM_OPERATION_FAILED: PyErr_SetString(PyExc_Exception^, 'HLDOM_OPERATION_FAILED');
            end;
            Result := False;
        end else
            Result := True;
    end;
end;


function _HTMLayout_UseElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
begin
  with GetPythonEngine do
    begin
      Lock;
      PyArg_ParseTuple( args, 'i', @he );
      Result := VariantAsPyObject(HTMLayout_UseElement(he));
      ucount := ucount + 1;
      Unlock;
    end;
end;

function _HTMLayout_UnuseElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
begin
  with GetPythonEngine do
    begin
      Lock;
      PyArg_ParseTuple( args, 'i', @he );
      Result := VariantAsPyObject(HTMLayout_UnuseElement(he));
      ucount := ucount - 1;
      Unlock;
    end;
end;

// hwnd: HWND; uri: LPCWSTR; data: PByte; dataLength: DWORD
function _HTMLayoutDataReady ( self, args : PPyObject ) : PPyObject; cdecl;
var
   h_wnd: HWND;
   uri: LPCWSTR;
   data : PByte;
   dataLength: DWORD;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'Ius#', @h_wnd, @uri, @data, @dataLength );
      Result := VariantAsPyObject(HTMLayoutDataReady(h_wnd, uri, data, dataLength));
    end;
end;

// BOOL HLAPI HTMLayoutDataReadyAsync(HWND hwnd, LPCWSTR uri, LPBYTE data, DWORD dataLength, UINT dataType /*HTMLayoutResourceType*/ );
function _HTMLayoutDataReadyAsync( self, args : PPyObject ) : PPyObject; cdecl;
var
   h_wnd: HWND;
   uri: LPCWSTR;
   data : PByte;
   dataLength: DWORD;
   dataType: UINT;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'Ius#i', @h_wnd, @uri, @data, @dataLength, @dataType);
      Result := VariantAsPyObject(HTMLayoutDataReadyAsync(h_wnd, uri, data, dataLength, dataType));
    end;
end;


//function HTMLayoutGetElementState(he: HElement; pstateBits: ^TElement_STATE_BITS): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutGetElementState';

function _HTMLayoutGetElementState ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   stateBits: TElement_STATE_BITS;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'i', @he );
      if CheckRez(HTMLayoutGetElementState(he, @stateBits)) then
          Result := VariantAsPyObject(stateBits)
      else
          Result := nil;

    end;
end;


//
//function HTMLayoutSetElementState(he: HElement; stateBitsToSet: TElement_STATE_BITS; stateBitsToClear: TElement_STATE_BITS;
//  updateView: BOOL): HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutSetElementState';

function _HTMLayoutSetElementState ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   stateBitsToSet, stateBitsToClear: TElement_STATE_BITS;
   obj : PPyObject;
begin
  with GetPythonEngine do
    begin
      obj := nil;
      PyArg_ParseTuple( args, 'iii|O', @he, @stateBitsToSet, @stateBitsToClear, @obj );
      if CheckRez(HTMLayoutSetElementState(he, stateBitsToSet, stateBitsToClear,
                                           (obj = nil) or (PyObject_IsTrue(obj) = 1))) then
          Result := PyInt_FromLong(HLDOM_OK)
      else
          Result := nil;
    end;
end;

//function HTMLayoutGetStyleAttribute(he: HElement; name: LPCSTR; p_value: LPCWSTR): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutGetStyleAttribute';

function _HTMLayoutGetStyleAttribute ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   n : PAnsiChar;
   p_value : PWideChar;
begin
    with GetPythonEngine do
      begin
        PyArg_ParseTuple( args, 'is', @he, @n );
        if CheckRez(HTMLayoutGetStyleAttribute(he, n, @p_value)) then
            Result := VariantAsPyObject(WideString(p_value))
        else
            Result := nil;
      end;
end;


//function HTMLayoutSetStyleAttribute(he: HElement; name: LPCSTR; value: LPCWSTR): HLDOM_RESULT
//  ; stdcall; external HTMLayout name 'HTMLayoutSetStyleAttribute';

function _HTMLayoutSetStyleAttribute ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   n : PAnsiChar;
   value : WideString;
   obj : PPyObject;
begin
   with GetPythonEngine do
     begin
       PyArg_ParseTuple( args, 'isO', @he, @n, @obj );
       value := PyObjectAsVariant(obj);
       if CheckRez(HTMLayoutSetStyleAttribute(he, n, PWideChar(value))) then
           Result := PyInt_FromLong(HLDOM_OK)
       else
           Result := nil;
     end;
end;


//function HTMLayoutGetAttributeByName(he: HElement; name: LPCSTR; p_value: LPCWSTR): HLDOM_RESULT
//  ; stdcall; external HTMLayout name 'HTMLayoutGetAttributeByName';

function _HTMLayoutGetAttributeByName ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   n : PAnsiChar;
   p_value : PWideChar;
begin
   with GetPythonEngine do
     begin
       PyArg_ParseTuple( args, 'is', @he, @n );
       if CheckRez(HTMLayoutGetAttributeByName(he, n, @p_value)) then
           Result := VariantAsPyObject(WideString(p_value))
       else
           Result := nil;
     end;
end;



//function HTMLayoutSetAttributeByName(he: HElement; name: LPCSTR; value: LPCWSTR): HLDOM_RESULT
//  ; stdcall; external HTMLayout name
//'HTMLayoutSetAttributeByName';

function _HTMLayoutSetAttributeByName ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   n : PAnsiChar;
   value : WideString;
   obj : PPyObject;
   arg : PWideChar;
begin
   with GetPythonEngine do
     begin
       arg := nil;
       PyArg_ParseTuple( args, 'isO', @he, @n, @obj );
       if obj <> Py_None then begin
          value := PyObjectAsVariant(obj);
          if value <> '' then
             arg := PWideChar(value);
       end;
       if CheckRez(HTMLayoutSetAttributeByName(he, n, arg)) then
           Result := PyInt_FromLong(HLDOM_OK)
       else
           Result := nil;
     end;
end;

//function HTMLayoutGetRootElement(hwnd: HWND; phe: pHElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetRootElement';
function _HTMLayoutGetRootElement ( self, args : PPyObject ) : PPyObject; cdecl;
var
   h_wnd: HWND;
   he: HElement;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'I', @h_wnd );
      if CheckRez(HTMLayoutGetRootElement(h_wnd, @he)) then
          Result := VariantAsPyObject(he)
      else
          Result := nil;
    end;
end;

//function HTMLayoutGetNthChild(he: HElement; n: UINT; phe: pHElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetNthChild';
function _HTMLayoutGetNthChild ( self, args : PPyObject ) : PPyObject; cdecl;
var
   i : UINT;
   root, he: HElement;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'iI', @root, @i );
      if CheckRez(HTMLayoutGetNthChild(root, i, @he)) then
          Result := VariantAsPyObject(he)
      else
          Result := nil;
    end;
end;

//function HTMLayoutGetChildrenCount(he: HElement; count: pUINT): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetChildrenCount';
function _HTMLayoutGetChildrenCount ( self, args : PPyObject ) : PPyObject; cdecl;
var
   i : UINT;
   he: HElement;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'i', @he );
      if CheckRez(HTMLayoutGetChildrenCount(he, @i)) then
          Result := PyLong_FromLong(i)
      else
          Result := nil;
    end;
end;

function HTMLayoutElementCallback(he: HElement; param: pointer): BOOL; stdcall;
var
   r : PPyObject;
   pargs : PPyObject;
begin
  with GetPythonEngine do
    begin
      pargs := PyTuple_New(1);
      try
         PyTuple_SetItem(pargs, 0, PyInt_FromLong(he));
         r := PyObject_Call(param, pargs, nil);
         Result := PyObject_IsTrue(r) = 1;
         Py_DECREF(r);
      finally
         Py_DECREF(pargs);
      end;
    end;
end;

//function HTMLayoutVisitElements(he: HElement; tagName: LPCSTR; attributeName: LPCSTR;
//  attributeValue: LPCWSTR; callback: THTMLayoutElementCallback; param: pointer; depth: DWORD):
//  HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutVisitElements';
function _HTMLayoutVisitElements ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   tagName : PAnsiChar;
   attributeName : PAnsiChar;
   attributeValue : WideString;
   attributeValueObj : PPyObject;
   attributeValueP : PWideChar;
   param : PPyObject;
   depth : DWORD;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'issOOi', @he, @tagName, @attributeName, @attributeValueObj, @param, @depth );
      attributeValue := PyObjectAsVariant(attributeValueObj);
      if attributeName = '' then
         attributeName := nil;
      attributeValueP := nil;
      if attributeValue <> '' then
         attributeValueP := PWideChar(attributeValue);
      if CheckRez(HTMLayoutVisitElements(he, tagName, attributeName,
                                         attributeValueP,
                                         @HTMLayoutElementCallback, param, depth)
                 ) then
          Result := PyInt_FromLong(HLDOM_OK)
      else
          Result := nil;
    end;
end;

//function HTMLayoutSelectElements(he: HElement; CSS_selectors: LPCSTR; callback:
//  THTMLayoutElementCallback; param: pointer): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutSelectElements';
function _HTMLayoutSelectElements ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   CSS_selectors : PAnsiChar;
   param : PPyObject;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'isO', @he, @CSS_selectors, @param );
      if CheckRez(HTMLayoutSelectElements(he, CSS_selectors, @HTMLayoutElementCallback, param)) then
          Result := PyInt_FromLong(HLDOM_OK)
      else
          Result := nil;
    end;
end;

//function HTMLayoutUpdateElement(he: HElement; renderNow: BOOL): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutUpdateElement';
function _HTMLayoutUpdateElement ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   b : PPyObject;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'iO', @he, @b );
      if CheckRez(HTMLayoutUpdateElement(he, PyObject_IsTrue(b) = 1)) then
          Result := PyInt_FromLong(HLDOM_OK)
      else
          Result := nil;
    end;
end;

//function HTMLayoutUpdateElementEx(he: HElement; flags: UINT): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutUpdateElementEx';
function _HTMLayoutUpdateElementEx ( self, args : PPyObject ) : PPyObject; cdecl;
var
   he: HElement;
   flags : UINT;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple( args, 'iI', @he, @flags );
        if CheckRez(HTMLayoutUpdateElementEx(he, flags)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;



function _postmessage(self, args : PPyObject) : PPyObject; cdecl;
var
   h_wnd : Integer;
   msg : Integer;
   wParam : Integer;
   lParam : Integer;
   send_to_parent : PPyObject;
   immediately : PPyObject;
begin
  with GetPythonEngine do
    begin
      wParam := 0;
      lParam := 0;
      send_to_parent := nil;
      immediately := nil;
      PyArg_ParseTuple( args, 'ii|iiOO', @h_wnd, @msg, @wParam, @lParam, @send_to_parent, @immediately );
      if (send_to_parent <> nil) and (PyObject_IsTrue(send_to_parent) = 1) then
         h_wnd := getparent(h_wnd);
      if (immediately = nil) or (PyObject_IsTrue(immediately) <> 1) then
         postmessage(h_wnd, msg, wParam, lParam)
      else
         sendmessage(h_wnd, msg, wParam, lParam);
      Result := VariantAsPyObject(True);
    end;
end;


//function HTMLayoutControlGetValue(he: HElement; out pVal: TJSON_VALUE): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutControlGetValue';
function _HTMLayoutControlGetValue(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
   value, null_value: JSON_VALUE;
   vType, vUnits : UINT;
   i_data : Integer;
   s_data : PWideChar;
   i64_data : INT64;
   f_data : FLOAT_VALUE;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'i', @he );
      ValueInit(@value);
      try
         if CheckRez(HTMLayoutControlGetValue(he, @value)) then begin
             ValueType(@value, @vType, @vUnits);
             case vType of
             V_BOOL : begin
                  ValueIntData(@value, @i_data);
                  Result := VariantAsPyObject(i_data <> 0);
             end;
             V_INT : begin
                  ValueIntData(@value, @i_data);
                  Result := VariantAsPyObject(i_data);
             end;
             V_STRING : begin
                  ValueStringData(@value, @s_data, @i_data);
                  Result := VariantAsPyObject(WideString(s_data))
             end;
             V_FLOAT : begin
                  ValueFloatData(@value, @f_data);
                  Result := VariantAsPyObject(f_data)
             end;
             V_DATE : begin
                  ValueInt64Data(@value, @i64_data);
                  try
                    // если заполнен двухзначный год, преобразуем YY в 20YY
                    if i64_data < -473669856000000000 then
                      i64_data := 631139040000000000 + i64_data;
                    Result := VariantAsPyObject(SystemTimeToDateTime(FileTimeToSystemTime(TFileTime(i64_data))));
                  except
                    ValueInit(@null_value);
                    null_value.t := V_NULL;
                    HTMLayoutControlSetValue(he, @null_value);
                    ValueClear(@null_value);
                    Result := ReturnNone;
                  end;
             end;
             else
                Result := ReturnNone;
             end;
         end else
             Result := nil;
      finally
          ValueClear(@value);
      end;
    end;
end;

//function HTMLayoutControlSetValue(he: HElement; const pVal: TJSON_VALUE): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutControlSetValue';
function _HTMLayoutControlSetValue(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
   obj : PPyObject;
   value: JSON_VALUE;
   s : WideString;
   ok : boolean;
   v : Variant;
   dt : TDateTime;
begin
  with GetPythonEngine do
    begin
       PyArg_ParseTuple( args, 'iO', @he, @obj );
       ValueInit(@value);
       try
           ok := True;
           if obj = Py_None then
               value.t := V_NULL
           else if PyBool_Check(obj) then
               ValueIntDataSet(@value, PyObject_IsTrue(obj), V_BOOL, 0)
           else if PyInt_Check(obj) then
               ValueIntDataSet(@value, PyInt_AsLong(obj), V_INT, 0)
           else if PyLong_Check(obj) then
               ValueIntDataSet(@value, PyLong_AsLongLong(obj), V_INT, 0)
           else if PyFloat_Check(obj) then
               ValueFloatDataSet(@value, PyFloat_AsDouble(obj), V_FLOAT, 0)
           else if PyUnicode_Check(obj) then begin
               s := PyUnicode_AsWideString(obj);
               ValueStringDataSet(@value, PWideChar(s), WStrLen(PWideChar(s)), 0);
           end else if PyString_Check(obj) then begin
               s := PyObjectAsString(obj);
               ValueStringDataSet(@value, PWideChar(s), WStrLen(PWideChar(s)), 0);
           end else if ExtractDate(obj, v) then begin
               dt := v;
               ValueInt64DataSet(@value, Int64(DateTimeToFileTime(dt)), V_DATE, 0);
           end else
               ok := False;
           if ok then
               if CheckRez(HTMLayoutControlSetValue(he, @value)) then
                   Result := VariantAsPyObject(True)
               else
                   Result := nil
               else begin
                   PyErr_SetString(PyExc_Exception^, PAnsiChar('_HTMLayoutControlSetValue. Unknown type'));
                   Result := nil;
               end;
       finally
           ValueClear(@value);
       end;
    end;
end;

function _HTMLayoutGetElementDataType(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
   value: JSON_VALUE;
   vType, vUnits : UINT;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple( args, 'i', @he );
        ValueInit(@value);
        try
            if CheckRez(HTMLayoutControlGetValue(he, @value)) then begin
                ValueType(@value, @vType, @vUnits);
                Result := PyInt_FromLong(vType);
            end else
                Result := nil;
        finally
            ValueClear(@value);
        end;
    end;
end;


(** Create new element, the element is disconnected initially from the DOM.
    Element created with ref_count = 1 thus you \b must call HTMLayout_UnuseElement on returned handler.
 * \param tagname \b LPCSTR, html tag of the element e.g. "div", "option", etc.
 * \param textOrNull \b LPCWSTR, initial text of the element or NULL. text here is a plain text - method does no parsing.
 * \param[out ] phe \b #HElement*, variable to receive handle of the element
  **)

(*out*)

//function HTMLayoutCreateElement(tagname: LPCSTR; textOrNull: LPCWSTR; phe: pHElement):
//  HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutCreateElement';

function _HTMLayoutCreateElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   tagname : PAnsiChar;
   textOrNullP : PWideChar;
begin
   with GetPythonEngine do begin
    Lock;
    textOrNullP := nil;
    PyArg_ParseTuple(args, 's|u', @tagname, @textOrNullP);
    if CheckRez(HTMLayoutCreateElement(tagname, textOrNullP, @he)) then begin
        Result := VariantAsPyObject(he);
    end else
        Result := nil;
    Unlock;
   end;
end;

(** Create new element as copy of existing element, new element is a full (deep) copy of the element and
    is disconnected initially from the DOM.
    Element created with ref_count = 1 thus you \b must call HTMLayout_UnuseElement on returned handler.
 * \param he \b #HElement, source element.
 * \param[out ] phe \b #HElement*, variable to receive handle of the new element.
  **)
(*out*)

//function HTMLayoutCloneElement(he: HElement; phe: pHElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutCloneElement';

function _HTMLayoutCloneElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he1, he2 : HElement;
begin
    with GetPythonEngine do begin
        Lock;
        PyArg_ParseTuple(args, 'i', @he1);
        if CheckRez(HTMLayoutCloneElement(he1, @he2)) then
            Result := VariantAsPyObject(he2)
        else
            Result := nil;
        unlock;
    end;
end;

(** Insert element at \i index position of parent.
    It is not an error to insert element which already has parent - it will be disconnected first, but
    you need to update elements parent in this case.
 * \param index \b UINT, position of the element in parent collection.
   It is not an error to provide index greater than elements count in parent -
   it will be appended.
 **)

//function HTMLayoutInsertElement(he: HElement; hparent: HElement; index: UINT): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutInsertElement';

function _HTMLayoutInsertElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he, he_parent : HElement;
   index : UINT;
begin
    with getPythonEngine do begin
        PyArg_ParseTuple(args, 'iiI', @he, @he_parent, @index);
        if CheckRez(HTMLayoutInsertElement(he, he_parent, index)) then begin
            Result := PyInt_FromLong(HLDOM_OK);
            ucount := ucount + 1;
        end else
            Result := nil;
    end;
end;

(** Take element out of its container (and DOM tree).
    Element will be destroyed when its reference counter will become zero
 **)

//function HTMLayoutDetacHElement(he: HElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutDetacHElement';

function _HTMLayoutDetacHElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
begin
   with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutDetacHElement(he)) then begin
            Result := PyInt_FromLong(HLDOM_OK);
            ucount := ucount - 1;
        end else
            Result := nil;
   end;
end;

(**Delete element.
 * \param[in] he \b #HElement
 * \return \b #HLDOM_RESULT
 *
 * This function removes element from the DOM tree and then deletes it.
 *
 * \warning After call to this function \c he will become invalid.
 **)

//function HTMLayoutDeleteElement(he: HElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutDeleteElement';

function _HTMLayoutDeleteElement(self, args : PPyObject) : PPyObject; cdecl;
var
    he : HElement;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutDeleteElement(he)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

(**Get inner text of the element.
 * \param[in] he \b #HElement
 * \param[out] utf8bytes \b pointer to byte address receiving UTF8 encoded plain text
 * \return \b #HLDOM_RESULT
 *)

//function HTMLayoutGetElementInnerText(he: HElement; utf8bytes: pPByte): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetElementInnerText';

function _HTMLayoutGetElementInnerText(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   t : PAnsiChar;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutGetElementInnerText(he, @t)) then
            Result := VariantAsPyObject(strpas(t))
        else
            Result := nil;
    end;
end;

(**Set inner text of the element.
 * \param[in] he \b #HElement
 * \param[in] utf8bytes \b pointer, UTF8 encoded plain text
 * \param[in] length \b UINT, number of bytes in utf8bytes sequence
 * \return \b #HLDOM_RESULT
 *)

//function HTMLayoutSetElementInnerText(he: HElement; utf8bytes: PAnsiChar {LPCBYTE}; length: UINT):
//  HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutSetElementInnerText';

function _HTMLayoutSetElementInnerText(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   data : PAnsiChar;
   cdata : UINT;
begin
   with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'is#', @he, @data, @cdata);
        if CheckRez(HTMLayoutSetElementInnerText(he, data, cdata)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
   end;
end;

//function HTMLayoutGetElementHtml(he: HElement; utf8bytes: PPBYTE; outer: BOOL):
//  HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutGetElementHtml';
function _HTMLayoutGetElementHtml(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   t : PAnsiChar;
   b_obj : PPyObject;
   outer : BOOL;
begin
    with GetPythonEngine do begin
        b_obj := nil;
        PyArg_ParseTuple(args, 'i|O', @he, @b_obj);
        outer := (b_obj = nil) or (PyObject_IsTrue(b_obj) = 1);
        if CheckRez(HTMLayoutGetElementHtml(he, @t, outer)) then
            Result := VariantAsPyObject(strpas(t))
        else
            Result := nil;
    end;
end;


//(**Copies selection to clipboard.
// *
// * \param[in] hWndHTMLayout \b HWND, HTMLayout window handle.
// * \return \b BOOL, TRUE if selected HTML text has been copied to clipboard, FALSE otherwise.
// **)
//
//function HTMLayoutClipboardCopy(hWndHTMLayout: HWND): BOOL; stdcall;
//external HTMLayout name 'HTMLayoutClipboardCopy';

function _HTMLayoutClipboardCopy(self, args: PPyObject): PPyObject; cdecl;
var
   h_wnd: HWND;
   he: HElement;
begin
  with GetPythonEngine do
    begin
      PyArg_ParseTuple( args, 'I', @h_wnd );
      Result := VariantAsPyObject(HTMLayoutClipboardCopy(h_wnd))
    end;
end;


//function HTMLayoutSetElementHtml(he: HElement; html: PAnsiChar; htmlLength: DWORD; where: UINT):
//  HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutSetElementHtml';
function _HTMLayoutSetElementHtml(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   html : PAnsiChar;
   htmlLength : Integer;
   where : UINT;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'is#I', @he, @html, @htmlLength, @where);
        if CheckRez(HTMLayoutSetElementHtml(he, html, htmlLength, where)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end
end;

//function HTMLayoutSelectParent(he: HElement; selector: LPCSTR; depth: UINT; heFound: pHElement):
//  HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutSelectParent';

function _HTMLayoutSelectParent(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
   selector: PAnsiChar;
   depth : Integer;
   heFound: HElement;
begin
   with GetPythonEngine do begin
       heFound := 0;
       depth := 0;
       PyArg_ParseTuple(args, 'is|i', @he, @selector, @depth);
       if CheckRez(HTMLayoutSelectParent(he, selector, depth, @heFound)) then
           Result := PyInt_FromLong(heFound)
       else
           Result := nil;
   end;
end;


//    cmd: UINT; // MOUSE_EVENTS
//    target: HELEMENT; // target element
//    pos: TPOINT; // position of cursor, element relative
//    pos_document: TPOINT; // position of cursor, document root relative
//    button_state: UINT; // MOUSE_BUTTONS
//    alt_state: UINT; // KEYBOARD_STATES
//    cursor_type: UINT; // CURSOR_TYPE to set
//    is_on_icon: BOOL; // mouse is over icon (foreground-image, foreground-repeat:no-repeat)

const
   I_CMD = 0;
   I_TARGET = 1;
   I_POS = 2;
   I_POS_DOCUMENT = 3;
   I_BUTTON_STATE = 4;
   I_ALT_STATE = 5;
   I_CURSOR_TYPE = 6;
   I_IS_ON_ICON = 7;

function _get_mouse_field(self, args : PPyObject) : PPyObject; cdecl;
var
   p : Integer;
   data : PMouseParams;
   i : Integer;
begin
   with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'ii', @p, @i);
        data := PMouseParams(p);
        case i of
        I_TARGET : Result := PyInt_FromLong(data^.target);
        I_POS : begin
                    Result := PyTuple_New(2);
                    PyTuple_SetItem(Result, 0, PyInt_FromLong(data^.pos.x));
                    PyTuple_SetItem(Result, 1, PyInt_FromLong(data^.pos.y));
                end;
        I_POS_DOCUMENT : begin
                    Result := PyTuple_New(2);
                    PyTuple_SetItem(Result, 0, PyInt_FromLong(data^.pos_document.x));
                    PyTuple_SetItem(Result, 1, PyInt_FromLong(data^.pos_document.y));
                end;
        I_BUTTON_STATE : Result := PyInt_FromLong(data^.button_state);
        I_ALT_STATE : Result := PyInt_FromLong(data^.alt_state);
        I_CURSOR_TYPE : Result := PyInt_FromLong(data^.cursor_type);
        I_IS_ON_ICON : begin
                          if data^.is_on_icon then
                              Result := PPyObject(Py_True)
                          else
                              Result := PPyObject(Py_False);
                          Py_IncRef(Result);
                       end;
        else
            Result := PyInt_FromLong(data^.cmd);
        end;
   end;
end;

//function HTMLayoutSendEvent(he: HElement; appEventCode: UINT; heSource: HElement; reason: UINT;
//  handled: pBOOL): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutSendEvent';
function _HTMLayoutSendEvent(self, args : PPyObject) : PPyObject; cdecl;
var
  he: HElement;
  appEventCode: UINT;
  heSource: HElement;
  reason: UINT;
  handled: BOOL;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'iIiI', @he, @appEventCode, @heSource, @reason);
         HTMLayoutSendEvent(he, appEventCode, heSource, reason, @handled);
         if handled then
            Result := PPyObject(Py_True)
         else
            Result := PPyObject(Py_False);
         Py_IncRef(Result);
    end;
end;

//function HTMLayoutPostEvent(he: HElement; appEventCode: UINT; heSource: HElement; reason: UINT):
//  HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutPostEvent';
function _HTMLayoutPostEvent(self, args : PPyObject) : PPyObject; cdecl;
var
  he: HElement;
  appEventCode: UINT;
  heSource: HElement;
  reason: UINT;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'iIiI', @he, @appEventCode, @heSource, @reason);
         if CheckRez(HTMLayoutPostEvent(he, appEventCode, heSource, reason)) then
            Result := PyInt_FromLong(HLDOM_OK)
         else
            Result := nil;
    end;
end;

//function HTMLayoutSetTimer(he: HElement; milliseconds: UINT): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutSetTimer';
function _HTMLayoutSetTimer(self, args : PPyObject) : PPyObject; cdecl;
var
  he: HElement;
  milliseconds: UINT;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'iI', @he, @milliseconds);
         if CheckRez(HTMLayoutSetTimer(he, milliseconds)) then
            Result := PyInt_FromLong(HLDOM_OK)
         else
            Result := nil;
    end;
end;

//function _HTMLayoutSetTimerEx(self, args : PPyObject) : PPyObject; cdecl;
//var
//  he: HElement;
//  milliseconds, timerid: UINT;
//  tp : TIMER_PARAMS;
//begin
//    with GetPythonEngine do begin
//         PyArg_ParseTuple(args, 'iII', @he, @milliseconds, @timerid);
//         tp.timerId := timerid;
//         if CheckRez(HTMLayoutSetTimerEx(he, milliseconds, @tp)) then
//            Result := PyInt_FromLong(HLDOM_OK)
//         else
//            Result := nil;
//    end;
//end;

//function HTMLayoutGetElementIndex(he: HElement; p_index: LPUINT): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetElementIndex';
function _HTMLayoutGetElementIndex(self, args : PPyObject) : PPyObject; cdecl;
var
   he: HElement;
   index : UINT;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutGetElementIndex(he, @index)) then
            Result := PyLong_FromLong(index)
        else
            Result := nil;
    end;
end;

//function HTMLayoutGetParentElement(he: HElement; p_parent_he: pHElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetParentElement';
function _HTMLayoutGetParentElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   phe : HElement;
begin
   with GetPythonEngine do begin
        phe := 0;
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutGetParentElement(he, @phe)) then
            Result := PyInt_FromLong(phe)
        else
            Result := nil;
   end;
end;

//function HTMLayoutScrollToView(he: HElement; flags : UINT): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutScrollToView';
function _HTMLayoutScrollToView(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   flags : Integer;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'ii', @he, @flags);
        if CheckRez(HTMLayoutScrollToView(he, flags)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

//function HTMLayoutGetElementHwnd(he: HElement; p_hwnd: THandle; rootWindow: BOOL): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutGetElementHwnd';
function _HTMLayoutGetElementHwnd(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   b_obj : PPyObject;
   rootWindow : BOOL;
   h : HWND;
begin
   with GetPythonEngine do begin
       b_obj := nil;
       PyArg_ParseTuple(args, 'i|O', @he, @b_obj);
       rootWindow := (b_obj = nil) or (PyObject_IsTrue(b_obj) = 1);
       h := 0;
       if CheckRez(HTMLayoutGetElementHwnd(he, @h, rootWindow)) then
           Result := PyInt_FromLong(h)
       else
           Result := nil;
   end;
end;

//function HTMLayoutIsElementVisible(he: HElement; pVisible: PBOOL): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutIsElementVisible';

function _HTMLayoutIsElementVisible(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   b : BOOL;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'i', @he);
         if CheckRez(HTMLayoutIsElementVisible(he, @b)) then
            Result := VariantAsPyobject(b)
         else
            Result := nil;
    end;
end;

//function HTMLayoutIsElementEnabled(he: HElement; pVisible: PBOOL): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutIsElementVisible';

function _HTMLayoutIsElementEnabled(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   b : BOOL;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'i', @he);
         if CheckRez(HTMLayoutIsElementEnabled(he, @b)) then
            Result := VariantAsPyobject(b)
         else
            Result := nil;
    end;
end;

//function HTMLayoutUpdateWindow(hWndHTMLayout : HWND) : BOOL;
//stdcall; external HTMLayout name 'HTMLayoutUpdateWindow';
function _HTMLayoutUpdateWindow(self, args : PPyObject) : PPyObject; cdecl;
var
   h : HWND;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'I', @h);
        if HTMLayoutUpdateWindow(h) then
           Result := PPyObject(Py_True)
        else
           Result := PPyObject(Py_False);
        Py_IncRef(Result);
    end;
end;

//function HTMLayoutCommitUpdates(hWndHTMLayout : HWND) : BOOL;
//stdcall; external HTMLayout name 'HTMLayoutCommitUpdates';
function _HTMLayoutCommitUpdates(self, args : PPyObject) : PPyObject; cdecl;
var
   h : HWND;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'I', @h);
        if HTMLayoutCommitUpdates(h) then
           Result := PPyObject(Py_True)
        else
           Result := PPyObject(Py_False);
        Py_IncRef(Result);
    end;
end;


function CompareCallback(he1: HElement; he2 : HElement; param: pointer): Integer; stdcall;
var
   r : PPyObject;
   pargs : PPyObject;
begin
  with GetPythonEngine do
    begin
      pargs := PyTuple_New(2);
      try
         PyTuple_SetItem(pargs, 0, PyInt_FromLong(he1));
         PyTuple_SetItem(pargs, 1, PyInt_FromLong(he2));
         r := PyObject_Call(param, pargs, nil);
         Result := PyInt_AsLong(r);
         Py_DECREF(r);
      finally
         Py_DECREF(pargs);
      end;
    end;
end;

//function HTMLayoutSortElements(he : HElement; firstIndex : UINT; lastIndex : UINT; cmpFunc : TELEMENT_COMPARATOR; param : Pointer) : HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutSortElements';

function _HTMLayoutSortElements(self, args : PPyObject) : PPyObject; cdecl;
var
   he : Helement;
   firstIndex : UINT;
   lastIndex : UINT;
   func : PPyObject;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iIIO', @he, @firstIndex, @lastIndex, @func);
        if CheckRez(HTMLayoutSortElements(he, firstIndex, lastIndex, @CompareCallback, func)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

//function HTMLayoutGetElementLocation(he: HElement; p_location: PRECT; areas: UINT):
//HLDOM_RESULT; stdcall; external HTMLayout name 'HTMLayoutGetElementLocation';

function _HTMLayoutGetElementLocation(self, args : PPyObject) : PPyObject; cdecl;
var
   r : TRect;
   he : HElement;
   areas : UINT;
begin
   r := rect(0, 0, 0, 0);
   with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iI', @he, @areas);
        Result := PyTuple_New(4);
        if CheckRez(HTMLayoutGetElementLocation(he, @r, areas)) then begin
            PyTuple_SetItem(Result, 0, PyInt_FromLong(r.Left));
            PyTuple_SetItem(Result, 1, PyInt_FromLong(r.Top));
            PyTuple_SetItem(Result, 2, PyInt_FromLong(r.Right));
            PyTuple_SetItem(Result, 3, PyInt_FromLong(r.Bottom));
        end else
            Result := nil;
   end;
end;

//function HTMLayoutGetElementUID(he: HElement; puid: pUINT): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetElementUID';
function _HTMLayoutGetElementUID(self, args : PPyObject) : PPyObject; cdecl;
var
   he : Helement;
   uid : UINT;
begin
   with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutGetElementUID(he, @uid)) then
            Result := PyInt_FromLong(uid)
        else
            Result := nil;
   end;
end;

//function HTMLayoutGetElementByUID(hwnd: HWND; uid: UINT; phe: pHElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetElementByUID';
function _HTMLayoutGetElementByUID(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   uid : UINT;
   h_wnd : HWND;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'II', @h_wnd, @uid);
         if CheckRez(HTMLayoutGetElementByUID(h_wnd, uid, @he)) then
             Result := PyInt_FromLong(he)
         else
             Result := nil;
    end;
end;


//function HTMLayoutGetElementType(he: HElement; p_type: LPCSTR): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetElementType';

function _HTMLayoutGetElementType(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   p : PAnsiChar;
begin
    with GetPythonEngine do begin
        p := nil;
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutGetElementType(he, @p)) then
            Result := VariantAsPyObject(strpas(p))
        else
            Result := nil;
    end;
end;


//function HTMLayoutGetScrollInfo(he: HElement; scrollPos: PPOINT; viewRect: PRECT; contentSize: PSIZE): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetScrollInfo';

function _HTMLayoutGetScrollInfo(self, args : PPyObject) : PPyObject; cdecl;
var
    he: HElement;
    scrollPos, contentSize: TPoint;
    viewRect: TRect;
begin
    scrollPos := point(0, 0);
    viewRect := rect(0, 0, 0, 0);
    contentSize := point(0, 0);
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutGetScrollInfo(he, @scrollPos, @viewRect, @contentSize)) then
            Result := ArrayToPyTuple([
                        ArrayToPyTuple([scrollPos.X, scrollPos.Y]),
                        ArrayToPyTuple([viewRect.Left,
                                        viewRect.Top,
                                        viewRect.Right,
                                        viewRect.Bottom]),
                        ArrayToPyTuple([contentSize.X, contentSize.Y]) ])
        else
            Result := nil;
    end;
end;

//function HTMLayoutSetScrollPos(he: HElement; scrollPos: TPOINT; smooth: BOOL): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutSetScrollPos';

function _HTMLayoutSetScrollPos(self, args: PPyObject): PPyObject; cdecl;
var
    he: HElement;
    scrollPos: TPoint;
    smooth: BOOL;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iiii', @he, @scrollPos.x, @scrollPos.y, @smooth);
        if CheckRez(HTMLayoutSetScrollPos(he, scrollPos, smooth)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

//function HTMLayoutCallBehaviorMethod(he: HElement; const params: TMETHOD_PARAMS): HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutCallBehaviorMethod';

function _HTMLayoutCallBehaviorMethod(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   p: UINT;
   params: Pointer;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iI', @he, @p);
        params := Pointer(p);
        if CheckRez(HTMLayoutCallBehaviorMethod(he, params)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

function _XCall(self, args : PPyObject) : PPyObject; cdecl;
var
   xp: XCALL_PARAMS;
   he : HElement;
   method_name: PAnsiChar;
   argc: Integer;
   r, v, p: JSON_VALUE;
   argv, pv: PPyObject;
   i, res: Integer;
   p_xargv: Pointer;
   xargv: Array[0..7] of JSON_VALUE;
begin
    with GetPythonEngine do begin
        ValueInit(@v);
        ValueInit(@p);
        ValueInit(@r);
        PyArg_ParseTuple(args, 'isO', @he, @method_name, @argv);
        argc := PyList_Size(argv);
        for i := 0 to argc - 1 do begin
            pv := PyList_GetItem(argv, i);
            if PyBool_Check(pv) then
                ValueIntDataSet(@v, PyObject_IsTrue(pv), V_BOOL, 0)
            else if PyInt_Check(pv) then
                ValueIntDataSet(@v, PyInt_AsLong(pv), V_INT, 0);
            xargv[i] := v;
        end;
        p_xargv := @xargv;
        ValueIntDataSet(@p, Integer(p_xargv), V_INT, 0);
        xp.methodID := Cardinal(TBEHAVIOR_METHOD_IDENTIFIERS(XCALL));
        xp.method_name := method_name;
        xp.argc := argc;
        xp.argv := p_xargv;
        xp.retval := r;
        res := HTMLayoutCallBehaviorMethod(he, @xp);
        ValueClear(@r);
        ValueClear(@p);
        ValueClear(@v);
        Result := PyInt_FromLong(res);
    end;
end;

function _setSelection(self, args : PPyObject) : PPyObject; cdecl;
var
   sp: TEXT_EDIT_SELECTION_PARAMS;
   he : HElement;
   s_start, s_end: Integer;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iii', @he, @s_start, @s_end);
        sp.methodID := Cardinal(TBEHAVIOR_METHOD_IDENTIFIERS(TEXT_EDIT_SET_SELECTION));
        sp.selection_start := s_start;
        sp.selection_end := s_end;
        Result := PyInt_FromLong(HTMLayoutCallBehaviorMethod(he, @sp));
    end;
end;

function _debug_get_ucount(self, args : PPyObject) : PPyObject; cdecl;
begin
     with GetPythonEngine do begin
         Result := PyInt_FromLong(ucount);
     end;
end;

function _shellexecute(self, args : PPyObject) : PPyObject; cdecl;
var
   operation, filename, parameters, directory : PAnsiChar;
   showcmd : Integer;
begin
   with GetPythonEngine do begin
        operation := nil;
        parameters := nil;
        directory := nil;
        showcmd := SW_SHOW;
        PyArg_ParseTuple(args, 's|sssi', @filename, @operation, @parameters, @directory, @showcmd);
        Result := PyInt_FromLong(ShellExecuteA(Application.Handle, operation, filename, parameters, directory, showcmd));
   end;
end;

function _HTMInsertMenu( self, args : PPyObject ) : PPyObject; cdecl;
var
   htmlmanager, o : PPyObject;
   menumode : Integer;
   pyMenu : ITKSPyMenuManager;
   wm : ITKSWindowManager;
   iActive : ITKSActiveWindow;
   iWindow : ITKSWindow;
   v : Variant;
   creatednew : Pointer;
   himage : Integer;
begin
  with GetPythonEngine do
    begin
      menumode := 0;
      himage := INVALID_HANDLE_VALUE;
      PyArg_ParseTuple( args, 'OO|ii', @htmlmanager, @o, @menumode, @himage );
      wm := get_window_manager(VarPythonCreate(htmlmanager), False, nil, creatednew);
      if (wm <> nil) and
         (wm.QueryInterface(ITKSActiveWindow, iActive) = S_OK)
      then begin
         iActive.get_active_window(iWindow);
         if (iWindow <> nil) and
            (iWindow.QueryInterface(ITKSPyMenuManager, pyMenu) = S_OK)
         then begin
             v := VarPythonCreate(o);
             pyMenu.insertmenu(v, menumode, himage);
         end;
      end;
      Result := ReturnNone;
    end;
end;

//function HTMLayoutGetFocusElement(hwnd: HWND; phe: pHElement): HLDOM_RESULT; stdcall;
//external HTMLayout name 'HTMLayoutGetFocusElement';
function _HTMLayoutGetFocusElement(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   h_wnd : HWND;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'I', @h_wnd);
         if CheckRez(HTMLayoutGetFocusElement(h_wnd, @he)) then
             Result := PyInt_FromLong(he)
         else
             Result := nil;
    end;
end;

//function HTMLayoutGetElementIntrinsicHeight(he : Helement; forWidth : INT; pHeight : PINT) : HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutGetElementIntrinsicHeight';
function _HTMLayoutGetElementIntrinsicHeight(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   forWidth, Height : Integer;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'ii', @he, @forWidth);
        if CheckRez(HTMLayoutGetElementIntrinsicHeight(he, forWidth, @Height)) then
            Result := PyInt_FromLong(Height)
        else
            Result := nil;
    end;
end;

//function HTMLayoutShowPopup(hePopup : Helement; heAnchor : Helement; placement : UINT) : HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutShowPopup';
function _HTMLayoutShowPopup(self, args : PPyObject) : PPyObject; cdecl;
var
   hePopup : Helement;
   heAnchor : Helement;
   placement : UINT;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iiI', @hePopup, @heAnchor, @placement);
        if CheckRez(HTMLayoutShowPopup(hePopup, heAnchor, placement)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

function get_popup_mode(placement : WORD; animation : PPyObject) : UINT;
const
    bool_arr : array [boolean] of WORD = (0, 1);
begin
    Result := (bool_arr[(animation <> nil) and (GetPythonEngine.PyObject_IsTrue(animation) = 1)] or placement shl 16);
end;

//function HTMLayoutShowPopupAt(hePopup : Helement; pos : TPOINT; mode : UINT) : HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutShowPopupAt';
function _HTMLayoutShowPopupAt(self, args : PPyObject) : PPyObject; cdecl;
var
   hePopup : Helement;
   x, y : Integer;
   placement : WORD;
   animation : PPyObject;
   p : TPoint;
   mode : UINT;
begin
    with GetPythonEngine do begin
        animation := nil;
        PyArg_ParseTuple(args, 'iiii|O', @hePopup, @x, @y, @placement, @animation);
        p := Point(x, y);
        mode := get_popup_mode(placement, animation);
        if CheckRez(HTMLayoutShowPopupAt(hePopup, p, mode)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;


//function HTMLayoutTrackPopupAt(hePopup : Helement; posRoot : TPOINT; mode : UINT; pheItem : PHELEMENT) : HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutTrackPopupAt';
function _HTMLayoutTrackPopupAt(self, args : PPyObject) : PPyObject; cdecl;
var
   hePopup : Helement;
   x, y : Integer;
   placement : WORD;
   animation : PPyObject;
   heItem : HELEMENT;
begin
    with GetPythonEngine do begin
        animation := nil;
        PyArg_ParseTuple(args, 'iiii|O', @hePopup, @x, @y, @placement, @animation);
        if CheckRez(HTMLayoutTrackPopupAt(hePopup,
                                          Point(x, y),
                                          get_popup_mode(placement, animation),
                                          @heItem)) then
            Result := PyInt_FromLong(heItem)
        else
            Result := nil;
    end;
end;

//function HTMLayoutHidePopup(he : Helement) : HLDOM_RESULT;
//stdcall; external HTMLayout name 'HTMLayoutHidePopup';
function _HTMLayoutHidePopup(self, args : PPyObject) : PPyObject; cdecl;
var
   he : Helement;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'i', @he);
        if CheckRez(HTMLayoutHidePopup(he)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

function _HTMLayout_window_id(self, args : PPyObject) : PPyObject; cdecl;
var
   iwindowid : ITKSWindowID;
   wm : ITKSWindowManager;
   r : Integer;
   html : PPyObject;
   modal : PPyObject;
   creatednew : Pointer;
begin
   r := -1;
   with GetPythonEngine do begin
      PyArg_ParseTuple(args, 'OO', @html, @modal);
      wm := get_window_manager(VarPythonCreate(html), PyObject_IsTrue(modal) = 1, nil, creatednew);
      if wm <> nil then begin
         if wm.queryinterface(ITKSWindowID, iwindowid) = S_OK then
            r := iwindowid.get_id();
      end;
      Result := PyInt_FromLong(r);
   end;
end;

function _HTMLayoutAttachHandler( self, args : PPyObject ) : PPyObject; cdecl;
var
   he : HElement;
   event_handler : PPyObject;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'iO', @he, @event_handler);
         TPyEventHandler.CreateWithObj(VarPythonCreate(event_handler)).AttachEventHandler(he);
         Result := PyInt_FromLong(HLDOM_OK);
    end;
end;

function _HTMLayoutSetCapture( self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
begin
    with GetPythonEngine do begin
         PyArg_ParseTuple(args, 'i', @he);
         Result := PyInt_FromLong(HTMLayoutSetCapture(he));
    end;
end;


//function HTMLayoutGetCharacterRect(he: Helement; pos: Integer; outRect: PRECT) : HLDOM_RESULT;
function _HTMLayoutGetCharacterRect(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   pos : Integer;
   outRect: TRect;
begin
    outRect := rect(0, 0, 0, 0);
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'ii', @he, @pos);
        if CheckRez(HTMLayoutGetCharacterRect(he, pos, @outRect)) then
            Result := ArrayToPyTuple([outRect.Left, outRect.Top, outRect.Right, outRect.Bottom])
        else
            Result := nil;
    end;
end;


function HTMLayoutEnumerationCallback(p: pointer; he: HElement; pos: Integer; postype: Integer; code: WCHAR): BOOL; stdcall;
var
    pargs : PPyObject;
begin
    with GetPythonEngine do begin
        pargs := Py_BuildValue('(iiiu#)', he, pos, postype, WideString(code), Length(code));
        try
            Result := PyObject_Call(p, pargs, nil) = PPyObject(Py_True);
        finally
            Py_DECREF(pargs);
        end;
    end;
end;

//function HTMLayoutEnumerate(he: Helement; pcb: THTMLayoutEnumerationCallback; p: Pointer; forward: boolean) : HLDOM_RESULT;
function _HTMLayoutEnumerate(self, args : PPyObject) : PPyObject; cdecl;
var
   he : HElement;
   p: Pointer;
   fwd: BOOL;
begin
    with GetPythonEngine do begin
        PyArg_ParseTuple(args, 'iOi', @he, @p, @fwd);
        if CheckRez(HTMLayoutEnumerate(he, @HTMLayoutEnumerationCallback, p, fwd)) then
            Result := PyInt_FromLong(HLDOM_OK)
        else
            Result := nil;
    end;
end;

// Функция используется для того, чтобы определить, является ли текущее приложение активным
// Она нужна, чтобы определить, надо ли ставить фокус куда-нибудь по умолчанию при генерации страницы
// Без нее фокус ставится даже тогда, когда окно программы не активно
function _HTMLayoutIsForeground(self, args : PPyObject) : PPyObject; cdecl;
begin
    // GetActiveWindow выдает handle окна, которое активно в текущем потоке (thread)
    // насколько я понимаю и люди тоже так пишут, что если поток не активен (в смысле приложение)
    // то эта функция выдает 0, что собственно нам и надо
    with GetPythonEngine do
        Result := VariantAsPyObject(GetActiveWindow() <> 0)
end;

function show_config_dialog(const param : LongInt) : boolean; stdcall;
const
   arr : array [boolean] of integer = (0, 1);
var
   p : Papp_info;
begin
   Result := True;
   p := Papp_info(param);
   p^.result := tkshtml_dialog.showhtmldialog(p^.HTMLManager, p^.wm)
end;

function _showhtmldialog( self, args : PPyObject ) : PPyObject; cdecl;
var
   o : PPyObject;
   config_mode : PPyObject;
   is_config_mode : boolean;
   p : Papp_info;
   root_wm : ITKSWindowManager;
   cfg : ITKSShowConfigWindow;
begin
   Result := nil;
   root_wm := nil;
   if not init_application() then Exit;
   with GetPythonEngine do begin
        o := nil;
        config_mode := nil;
        PyArg_ParseTuple(args, 'O|O', @o, @config_mode);
        is_config_mode := (config_mode <> nil) and (PyObject_IsTrue(config_mode) = 1);
        new(p);
        try
            p^.HTMLManager := VarPythonCreate(o);
            p^.result := mrNone;
            get_root_manager(root_wm);
            p^.wm := root_wm;
            if is_config_mode and (root_wm <> nil) and (root_wm.QueryInterface(ITKSShowConfigWindow, cfg) = S_OK) then
               cfg.showconfigwindow(@show_config_dialog, LongInt(p))
            else if is_config_mode and supports(MainServer, ITKSShowConfigWindow, cfg) then
               cfg.showconfigwindow(@show_config_dialog, LongInt(p))
            else
               show_config_dialog(LongInt(p));
            Result := VariantAsPyObject(p^.result);
        finally
            dispose(p);
        end;
   end;
end;

function register_configpage( self, args : PPyObject) : PPyObject; cdecl;
var
   pname : PAnsiChar;
   png_file: PAnsiChar;
   cls : PPyObject;
   iconfig : ITKSConfig;
   PNGObj   : TPNGObject;
   ConfigImage: TTKSImage;
begin
   with GetPythonEngine do begin
      PyArg_ParseTuple(args, 'sO|s', @pname, @cls, @png_file);
      iconfig := get_config_manager();
      if length(png_file) > 1 then begin
         ConfigImage := TTKSImage.Create(nil);
         PNGObj := TPNGObject.Create;
         PNGObj.LoadFromFile(png_file);
         ConfigImage.Picture.Bitmap.Assign(PNGObj);
         PNGObj.Free;
      end else begin
         ConfigImage := nil;
      end;
      if iconfig <> nil then begin
         iconfig.RegisterPage(pname, ConfigImage, TPyConfigPage.CreatePageWithHtml(cls));
      end;
      Result := ReturnNone;
   end;
end;


function show_tks_config( self, args : PPyObject ) : PPyObject; cdecl;
var
    iconfigx: ITKSConfigX;
    page_name : PAnsiChar;
    subpage_index : Integer;
begin
    with GetPythonEngine do begin
        subpage_index := 0;
        PyArg_ParseTuple(args, 's|i', @page_name, @subpage_index);
        iconfigx := get_configx();
        if iconfigx <> nil then
            iconfigx.DoConfigX(page_name, subpage_index);

        Result := ReturnNone;
    end;
end;


function AntiKaspersky( self, args : PPyObject) : PPyObject; cdecl;
begin
   with GetPythonEngine do
     Result := VariantAsPyObject('1234567890ABCDEF');
end;

function htmlaction( self, args : PPyObject ) : PPyObject; cdecl;
var
   iUnkn : Integer;
   cmd : Integer;
   obj : PPyObject;
   wm : ITKSWindowManager;
   iActive : ITKSActiveWindow;
   iWindow : ITKSWindow;
   ihtmlaction : IPyHtmlAction;
begin
   with GetPythonEngine do begin
       PyArg_ParseTuple(args, 'iiO', @iUnkn, @cmd, @obj);
       if iUnkn > 0 then begin
          if IUnknown(iUnkn).QueryInterface(ITKSWindowManager, wm) = S_OK then begin
              if (wm <> nil) and
                 (wm.QueryInterface(ITKSActiveWindow, iActive) = S_OK)
              then begin
                 iActive.get_active_window(iWindow);
                 if (iWindow <> nil) and
                    (iWindow.QueryInterface(IPyHtmlAction, ihtmlaction) = S_OK)
                 then begin
                      Result := VariantAsPyObject(ihtmlaction.DoPyHtmlAction(cmd, obj) = S_OK);
                 end;
              end;
          end;
       end;
   end;
end;


procedure init_func;
var
   H_WINGTD : LongInt;
begin
    AddMethod('showhtml', _showhtml, 'showhtml(html_document, modal = False, iwindow = 0) -> modalresult');
    AddMethod('showhtmldialog', _showhtmldialog, 'showhtml(html_document) -> modalresult');
    // Регистрация класса документа в качестве страницы настроек.
    AddMethod('register_configpage', register_configpage, 'register_configpage(name_string, html_document_cls, icon_png) -> None');
    //=============== layout functions =================
    AddMethod('HTMLayout_UseElement', _HTMLayout_UseElement, 'HTMLayout_UseElement');
    AddMethod('HTMLayout_UnuseElement', _HTMLayout_UnuseElement, 'HTMLayout_UnuseElement');
    AddMethod('HTMLayoutDataReady', _HTMLayoutDataReady, 'HTMLayoutDataReady');
    AddMethod('HTMLayoutDataReadyAsync', _HTMLayoutDataReadyAsync, 'Use this function outside of HLN_LOAD_DATA request');

    AddMethod('HTMLayoutGetElementState', _HTMLayoutGetElementState, 'HTMLayoutGetElementState');
    AddMethod('HTMLayoutSetElementState', _HTMLayoutSetElementState, 'HTMLayoutSetElementState');

    AddMethod('HTMLayoutGetStyleAttribute', _HTMLayoutGetStyleAttribute, 'HTMLayoutGetStyleAttribute');
    AddMethod('HTMLayoutSetStyleAttribute', _HTMLayoutSetStyleAttribute, 'HTMLayoutSetStyleAttribute');

    AddMethod('HTMLayoutGetAttributeByName', _HTMLayoutGetAttributeByName, 'HTMLayoutGetAttributeByName');
    AddMethod('HTMLayoutSetAttributeByName', _HTMLayoutSetAttributeByName, 'HTMLayoutSetAttributeByName');

    AddMethod('HTMLayoutGetRootElement', _HTMLayoutGetRootElement, 'HTMLayoutGetRootElement');
    AddMethod('HTMLayoutGetNthChild', _HTMLayoutGetNthChild, 'HTMLayoutGetNthChild');
    AddMethod('HTMLayoutGetChildrenCount', _HTMLayoutGetChildrenCount, 'HTMLayoutGetChildrenCount');

    AddMethod('HTMLayoutVisitElements', _HTMLayoutVisitElements, 'HTMLayoutVisitElements');
    AddMethod('HTMLayoutSelectElements', _HTMLayoutSelectElements, 'HTMLayoutSelectElements');

    AddMethod('HTMLayoutUpdateElement', _HTMLayoutUpdateElement, 'HTMLayoutUpdateElement');
    AddMethod('HTMLayoutUpdateElementEx', _HTMLayoutUpdateElementEx, 'HTMLayoutUpdateElementEx');

    AddMethod('HTMLayoutControlGetValue', _HTMLayoutControlGetValue, 'HTMLayoutControlGetValue');
    AddMethod('HTMLayoutControlSetValue', _HTMLayoutControlSetValue, 'HTMLayoutControlSetValue');
    AddMethod('HTMLayoutGetElementDataType', _HTMLayoutGetElementDataType, 'HTMLayoutGetElementDataType(he) -> UINT');

    AddMethod('postmessage', _postmessage, 'postmessage(h_wnd, msg, wParam, lParam, send_to_parent) -> None');

    AddMethod('HTMLayoutCreateElement', _HTMLayoutCreateElement, 'HTMLayoutCreateElement(tagName, Text = None) -> HElement');
    AddMethod('HTMLayoutCloneElement', _HTMLayoutCloneElement, 'HTMLayoutCloneElement(he) -> HElement');
    AddMethod('HTMLayoutInsertElement', _HTMLayoutInsertElement, 'HTMLayoutInsertElement(he, he_parent, index) -> HLDOM_RESULT');
    AddMethod('HTMLayoutDetachElement', _HTMLayoutDetacHElement, 'HTMLayoutDetachElement(he) -> HLDOM_RESULT');
    AddMethod('HTMLayoutDeleteElement', _HTMLayoutDeleteElement, 'HTMLayoutDeleteElement(he) -> HLDOM_RESULT');
    AddMethod('HTMLayoutGetElementInnerText', _HTMLayoutGetElementInnerText, 'HTMLayoutGetElementInnerText(he) -> AnsiString');
    AddMethod('HTMLayoutSetElementInnerText', _HTMLayoutSetElementInnerText, 'HTMLayoutSetElementInnerText(he, AnsiString) -> HLDOM_RESULT');
    AddMethod('HTMLayoutGetElementHtml', _HTMLayoutGetElementHtml, 'HTMLayoutGetElementHtml(he, outer) -> AnsiString');
    AddMethod('HTMLayoutSetElementHtml', _HTMLayoutSetElementHtml, 'HTMLayoutSetElementHtml(he, AnsiString, where) -> HLDOM_RESULT');
    AddMethod('HTMLayoutSelectParent', _HTMLayoutSelectParent, 'HTMLayoutSelectParent(he, css_selector, depth = 0) -> HElement');

    //AddMethod('get_mouse_field', _get_mouse_field, 'get_mouse_field(mousedata, field_id) -> field data');
    AddMethod('HTMLayoutSendEvent', _HTMLayoutSendEvent, 'HTMLayoutSendEvent(he, appEventCode, heTarget, reason) -> bool (handled or not)');
    AddMethod('HTMLayoutPostEvent', _HTMLayoutPostEvent, 'HTMLayoutPostEvent(he, appEventCode, heTarget, reason) -> HLDOM_RESULT');
    AddMethod('HTMLayoutSetTimer', _HTMLayoutSetTimer, 'HTMLayoutSetTimer(he, milliseconds) -> HLDOM_RESULT');
//    AddMethod('HTMLayoutSetTimerEx', _HTMLayoutSetTimerEx, 'HTMLayoutSetTimer(he, milliseconds, timerid) -> HLDOM_RESULT');

    AddMethod('HTMLayoutGetElementIndex', _HTMLayoutGetElementIndex, 'HTMLayoutGetElementIndex(he) -> index');
    AddMethod('HTMLayoutScrollToView', _HTMLayoutScrollToView, 'HTMLayoutScrollToView(he, flags) -> HLDOM_RESULT');
    AddMethod('HTMLayoutGetParentElement', _HTMLayoutGetParentElement, 'HTMLayoutGetParentElement(he) -> phe');

    AddMethod('HTMLayoutGetElementHwnd', _HTMLayoutGetElementHwnd, 'HTMLayoutGetElementHwnd(he) -> hwnd');

    AddMethod('HTMLayoutIsElementVisible', _HTMLayoutIsElementVisible, 'HTMLayoutIsElementVisible(he) -> bool');
    AddMethod('HTMLayoutIsElementEnabled', _HTMLayoutIsElementEnabled, 'HTMLayoutIsElementEnabled(he) -> bool');

    AddMethod('HTMLayoutUpdateWindow', _HTMLayoutUpdateWindow, 'HTMLayoutUpdateWindow(HWND) -> bool');
    AddMethod('HTMLayoutCommitUpdates', _HTMLayoutCommitUpdates, 'HTMLayoutCommitUpdates(HWND) -> bool');

    AddMethod('HTMLayoutSortElements', _HTMLayoutSortElements, 'HTMLayoutSortElements(he, fi, li, func) -> HLDOM_RESULT');

    AddMethod('HTMLayoutGetElementLocation', _HTMLayoutGetElementLocation, 'HTMLayoutGetElementLocation(he, areas) -> tuple(left, top, right, bottom)');
    AddMethod('HTMLayoutGetElementUID', _HTMLayoutGetElementUID, 'HTMLayoutGetElementUID(he) -> UID');
    AddMethod('HTMLayoutGetElementByUID', _HTMLayoutGetElementByUID, 'HTMLayoutGetElementByUID(h_wnd, uid) -> HElement');
    AddMethod('HTMLayoutGetElementType', _HTMLayoutGetElementType, 'HTMLayoutGetElementType(he) -> element_type_str');

    AddMethod('HTMLayoutGetScrollInfo', _HTMLayoutGetScrollInfo , 'HTMLayoutGetScrollInfo(he) -> tuple(tuple(X, Y), tuple(Left, Top, Right, Bottom), tuple(X, Y))');
    AddMethod('HTMLayoutSetScrollPos', _HTMLayoutSetScrollPos , 'HTMLayoutSetScrollPos(he, scrollPos, smooth) -> HLDOM_RESULT');
    AddMethod('HTMLayoutCallBehaviorMethod', _HTMLayoutCallBehaviorMethod , 'HTMLayoutCallBehaviorMethod(he, params) -> HLDOM_RESULT');
    AddMethod('XCall', _XCall , '');
    AddMethod('setSelection', _setSelection , 'setSelection(he, s_start, s_end) -> HLDOM_RESULT');

    AddMethod('shellexecute', _shellexecute, 'shellexecute() -> None');

    AddMethod('debug_get_ucount', _debug_get_ucount, '');

    AddMethod('HTMInsertMenu', _HTMInsertMenu, 'HTMInsertMenu(html_document, root_menu, menu_index = 0) -> None');
    AddMethod('HTMLayoutGetFocusElement', _HTMLayoutGetFocusElement, 'HTMLayoutGetFocusElement(hwnd) -> he');
    AddMethod('HTMLayoutGetElementIntrinsicHeight', _HTMLayoutGetElementIntrinsicHeight, 'HTMLayoutGetElementIntrinsicHeight(he, forWidth) -> Height');

    AddMethod('HTMLayoutShowPopup', _HTMLayoutShowPopup, 'HTMLayoutShowPopup(hePopup, heAnchor, position) -> HLDOM_RESULT');
    AddMethod('HTMLayoutShowPopupAt', _HTMLayoutShowPopupAt, 'HTMLayoutShowPopupAt(hePopup, (point_x, point_y), mode) -> HLDOM_RESULT');
    AddMethod('HTMLayoutTrackPopupAt', _HTMLayoutTrackPopupAt, 'HTMLayoutTrackPopupAt(hePopup, (point_x, point_y), mode) -> selected_he');
    AddMethod('HTMLayoutHidePopup', _HTMLayoutHidePopup, 'HTMLayoutHidePopup(he) -> HLDOM_RESULT');

    AddMethod('HTMLayout_window_id', _HTMLayout_window_id, 'HTMLayout_window_id() -> html window id');

    AddMethod('HTMLayoutAttachHandler', _HTMLayoutAttachHandler, 'HTMLayoutAttachHandler(he, event_handler) -> HLDOM_RESULT');
    AddMethod('HTMLayoutSetCapture', _HTMLayoutSetCapture, 'HTMLayoutSetCapture(he) -> HLDOM_RESULT');

    AddMethod('HTMLayoutGetCharacterRect', _HTMLayoutGetCharacterRect, 'HTMLayoutGetCharacterRect(he, pos) -> tuple(left, top, right, bottom)');
    AddMethod('HTMLayoutEnumerate', _HTMLayoutEnumerate, 'HTMLayoutEnumerate(he, callback, forward) -> HLDOM_RESULT');

    AddMethod('HTMLayoutClipboardCopy', _HTMLayoutClipboardCopy, 'HTMLayoutClipboardCopy(HWND) -> BOOL');

    AddMethod('HTMLayoutIsForeground', _HTMLayoutIsForeground, '');
    AddMethod('AntiKaspersky', AntiKaspersky, '');
    AddMethod('show_tks_config', show_tks_config, 'show_tks_config(page_name, subpage_index=0)');

    AddMethod('htmlaction', htmlaction, '');

    H_WINGTD := getModuleHandle(nil);
    if H_WINGTD <> 0 then begin
       @Server_QueryInterface := getProcAddress(H_WINGTD, 'Server_QueryInterface');
       if Assigned(Server_QueryInterface) then
          Server_QueryInterface(ITKSServer, tkscom.MainServer);
    end;
end;


initialization

finalization

   ucount := 0;

end.
