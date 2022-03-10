unit whatsapp_value;

interface

uses pythonengine, classes, sysutils, variants, ucefinterfaces, uceftypes, uCEFv8Value;

type

    IWAppValue  = interface
    ['{1B6BB534-8FF1-4F84-9B38-45CC9A57B174}']
        function get_desc() : WideString; stdcall;
    end;

    TCefv8Value = class(TInterfacedObject, ICefv8Value, IWAppValue)
    private
        fvalue : ICefv8Value;
    public
        constructor CreateWithValue(value : ICefv8Value);
        destructor Destroy; override;
        property value : ICefv8Value read fvalue implements ICefv8Value;
    public
        function get_desc() : WideString; stdcall;
    end;

//    TCefVariant = class(TInterfacedObject, ICefv8Value)
//    private
//        fvalue : variant;
//    public
//        constructor CreateWithVariant(value : Variant);
//        destructor Destroy; override;
//    public
//
//    end;

function pythontovalue(p : PPyObject) : ICefv8Value;
function valuetopython(const value: ICefv8Value) : PPyObject;
function varianttovalue(v : Variant) : ICefv8Value;

function valuetostring(value : ICefv8Value) : ustring;
function valuetostring2(value : ICefv8Value; const q : boolean = False) : ustring;

function get_key_value(value : ICefv8Value; const key : ustring): ustring;

implementation

uses VarPyth;

constructor TCefv8Value.CreateWithValue(value : ICefv8Value);
begin
    Inherited Create();
    fvalue := value;
end;

destructor TCefv8Value.Destroy;
begin
    fvalue := nil;
    inherited;
end;

function TCefv8Value.get_desc() : WideString; stdcall;
begin
    Result := '';
    if value.IsValid then
        Result := Result + ' IsValid';
    if value.IsUndefined then
        Result := Result + ' IsUndefined';
    if value.IsNull then
        Result := Result + ' IsNull';
    if value.IsBool then
        Result := Result + ' IsBool';
    if value.IsInt then
        Result := Result + ' IsInt';
    if value.IsUInt then
        Result := Result + ' IsUInt';
    if value.IsDouble then
        Result := Result + ' IsDouble';
    if value.IsDate then
        Result := Result + ' IsDate';
    if value.IsString then
        Result := Result + ' IsString';
    if value.IsObject then
        Result := Result + ' IsObject';
    if value.IsArray then
        Result := Result + ' IsArray';
    if value.IsFunction then
        Result := Result + ' IsFunction';
end;

function valuetopython(const value: ICefv8Value) : PPyObject;
var
    y, m, d, h, mi, sec, ms, jd, wd : WORD;
    dt : TDateTime;
    s : ustring;
    i : Integer;
    keys : TStrings;
    v : ICefv8Value;
    key : string;
    p : PPyObject;
    args : PPyObject;
begin
    with GetPythonEngine do begin
        if not value.IsValid or value.IsUndefined or value.IsNull then begin
            Result := ReturnNone;
        end else if value.IsBool then begin
            if value.GetBoolValue then
                Result := PPyObject(Py_True)
            else
                Result := PPyObject(Py_False);
            Py_XIncRef(Result);
        end else if value.IsUInt then begin
            Result := PyInt_FromLong(value.GetUIntValue)
        end else if value.IsInt then begin
            Result := PyInt_FromLong(value.GetIntValue)
        end else if value.IsDouble then begin
            Result := PyFloat_FromDouble(value.GetDoubleValue)
        end else if value.IsDate then begin
            dt := value.GetDateValue;
            DecodeDate( dt, y, m, d );
            DecodeTime( dt, h, mi, sec, ms );
            args := ArrayToPyTuple([y, m, d, h, mi, sec, ms*1000]);
            try
              Result := PyEval_CallObjectWithKeywords(PyDateTime_DateTimeType, args, nil);
              CheckError(False);
            finally
              Py_DecRef(args);
            end;
        end else if value.IsString then begin
            s := value.GetStringValue;
            Result := PyUnicode_FromWideString(PWideChar(s));
        end else if value.IsObject then begin
            // считаем, что это обычный json
            Result := PyDict_New;
            keys := TStringList.Create;
            try
                value.GetKeys(keys);
                for i := 0 to keys.count - 1 do begin
                    key := keys[i];
                    v := value.GetValueByKey(key);
                    p := valuetopython(v);
                    if p <> nil then begin
                        PyDict_SetItemString(Result, PAnsiChar(key), p);
                        Py_DECREF(p);
                    end;
                end;
            finally
                keys.Free;
            end;
        end else if value.IsArray then begin
            Result := PyList_New(0);
            for i := 0 to value.GetArrayLength - 1 do begin
                v := value.GetValueByIndex(i);
                p := valuetopython(v);
                if p <> nil then begin
                    PyList_Append(Result, p);
                    Py_XDecRef(p);
                end;
            end;
        end else
            Result := ReturnNone;
    end;
end;

// TCefv8ValueRef

procedure SetDictData(p : PPyObject; v : ICefv8Value);
var
    i : Integer;
    key : PPyObject;
    keys : PPyObject;
    value : PPyObject;
    pname : WideString;
begin
    with GetPythonEngine do begin
        keys := PyDict_Keys(p);
        for i := 0 to PySequence_Length(keys)-1 do begin
            key := PySequence_GetItem(keys, i);
            if key = nil then
                continue;
            pname := PyObjectAsVariant(key);
            value := PyDict_GetItem(p, key);
            v.SetValueByKey(pname, pythontovalue(value), 0);
        end;
    end;
end;

function GetSequenceItem(sequence : PPyObject; idx : Integer) : ICefv8Value;
var
    val : PPyObject;
begin
    with GetPythonEngine do begin
        val := PySequence_GetItem( sequence, idx );
        try
            Result := pythontovalue(val);
        finally
            Py_XDecRef( val );
        end;
    end;
end;

function pythontovalue(p : PPyObject) : ICefv8Value;
var
    v : Variant;
    seq_length : Integer;
    i : Integer;
begin
    with GetPythonEngine do begin
        if PyBool_Check(p) then
            Result := TCefv8ValueRef.NewBool(PyObject_IsTrue(p) = 1)
        else if PyInt_Check(p) then
            Result := TCefv8ValueRef.NewInt(PyInt_AsLong(p))
        else if PyFloat_Check(p) then
            Result := TCefv8ValueRef.NewDouble(PyFloat_AsDouble(p))
        else if extractdate(p, v) then
            Result := TCefv8ValueRef.NewDate(v)
        else if PyUnicode_Check(p) then
            Result := TCefv8ValueRef.NewString(PyUnicode_AsWideString(p))
        else if PyString_Check(p) then
            Result := TCefv8ValueRef.NewString(PyObjectAsString(p))
        else if PyDict_Check(p) then begin
            Result := TCefv8ValueRef.NewObject(nil, nil);
            SetDictData(p, Result);
        end else if PySequence_Check(p) = 1 then begin
            seq_length := PySequence_Length(p);
            Result := TCefv8ValueRef.NewArray(seq_length);
            for i := 0 to seq_length - 1 do
                Result.SetValueByIndex(i, GetSequenceItem(p, i));
        end else
            Result := TCefv8ValueRef.NewNull;
    end;
end;

function varianttovalue(v : Variant) : ICefv8Value;
var
    p : PPyObject;
begin
    p := ExtractPythonObjectFrom(v);
    Result := pythontovalue(p);
end;


function valuetostring(value : ICefv8Value) : ustring;
var
    i : Integer;
begin
    Result := '';
    if value.IsBool then begin
        if value.GetBoolValue then
            Result := 'true'
        else
            Result := 'false'
    end else if value.IsInt then begin
        Result := IntToStr(value.GetIntValue)
    end else begin
        Result := Result + value.GetStringValue;
    end;
end;

function valuetostring2(value : ICefv8Value; const q : boolean = False) : ustring;
var
    i : Integer;
begin
    Result := '';
    if value.IsArray then begin
        Result := '[';
        for i := 0 to value.GetArrayLength - 1 do begin
            if i > 0 then
                Result := Result + ', ';
            Result := Result + valuetostring2(value.GetValueByIndex(i), True);
        end;
        Result := Result + ']';
    end else if value.IsInt then
        Result := IntToStr(value.GetIntValue)
    else begin
        if q then
            Result := '"';
        Result := Result + value.GetStringValue;
        if q then
            Result := Result + '"';
    end;
end;

function get_key_value(value : ICefv8Value; const key : ustring): ustring;
begin
    Result := '';
    if value.HasValueByKey(key) then
        Result := valuetostring(value.GetValueByKey(key));
end;

end.
