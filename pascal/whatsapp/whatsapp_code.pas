unit whatsapp_code;

interface

uses SysUtils, whatsapp_crypto, windows, classes{, ceflib};

function decode_code(var arr : array of string) : string; overload;
//function decode_code(l : TStrings) : PBYTE; overload;
//function decode_code_str(l : TStrings) : string; overload;

function generate_pas(l : TStrings; const arrname : string = 'whatsapp_user_js'): string;

implementation

function decode_code(var arr : array of string) : string; overload;
var
    s : string;
    i : Integer;
    len : DWORD;
    p : PBYTE;
begin
    s := emptyStr;
    for i := low(arr) to high(arr) do
        s := s + arr[i];
    len := length(s);
    {$IFDEF WRITELN}
    writeln(len);
    {$ENDIF}
    p := crypto_string_to_binary(PAnsiChar(s), len);
    try
        setlength(Result, len);
        StrLCopy(PAnsiChar(Result), PansiChar(p), len);
    finally
        FreeMem(p);
    end;
end;

function decode_code(l : TStrings) : PBYTE; overload;
var
    s : string;
    i : Integer;
    len : DWORD;
begin
    s := '';
    for i := 0 to l.Count - 1 do
        s := s + l[i];
    len := length(s);
    Result := crypto_string_to_binary(PAnsiChar(s), len);
end;

function decode_code_str(l : TStrings) : string; overload;
var
    p : PBYTE;
begin
    Result := '';
    p := decode_code(l);
    try
        Result := strpas(PansiChar(p));
    finally
        FreeMem(p);
    end;
end;

function generate_pas(l : TStrings; const arrname : string = 'whatsapp_user_js'): string;
var
    p : TStrings;
    i : integer;
begin
    p := TStringList.Create;
    try
        p.Add('const');
        p.add(format(#9'%s : array [0..%d] of string = (', [arrname, l.Count - 1]));
        for i := 0 to l.Count - 1 do begin
            if i = l.Count - 1 then
                p.add(format(#9#9'''%s''', [l[i]]))
            else
                p.add(format(#9#9'''%s'',', [l[i]]));
        end;
        p.add(#9');');
        Result := p.Text;
    finally
        p.Free;
    end;
end;


end.
