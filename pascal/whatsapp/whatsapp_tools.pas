unit whatsapp_tools;

interface

uses Classes, {OverbyteIcsHttpProt,} windows, forms, sysutils, mystrutils;

//function retrieve_url_data(const url : WideString; const stream : TStream) : boolean;
//function retrieve_to_file(const url, filename : WideString) : boolean;

function GetApplicationVersion_Small : String;

implementation

{
function retrieve_url_data(const url : WideString; const stream : TStream) : boolean;
var
   HttpCli: THttpCli;
begin
    Result := False;
    HttpCli := TSSLHttpCli.Create(nil);
    try
        HttpCli.RcvdStream := stream;
        HttpCli.URL := url;
        HttpCli.Get;
        if HttpCli.StatusCode = 200 then
            Result := True;
    finally
        HttpCli.Free;
    end;
end;

function retrieve_to_file(const url, filename : WideString) : boolean;
var
    fstream : TFileStream;
begin
    Result := False;
    fstream := TFileStream.Create(filename, fmCreate);
    with fstream do try
        result := retrieve_url_data(url, fstream);
    finally
        Free;
    end;
end;
}

function GetApplicationVersion(const rev : boolean = False) : String;
var
   VersionBuffer : String;
   Version : PChar;
   Revision : PChar;
   VersionSize: DWORD;
   Dummy : DWORD;
begin
   Result:='N/A';
   VersionSize:=GetFileVersionInfoSize(PChar(Application.ExeName), Dummy);
   if VersionSize<>0 then begin
      SetLength(VersionBuffer,VersionSize);
      if (GetFileVersionInfo(PChar(Application.ExeName),Dummy,VersionSize,PChar(VersionBuffer))) then
         if (VerQueryValue(Pchar(VersionBuffer),'\StringFileInfo\041904E3\FileVersion',Pointer(Version),VersionSize))
         then
            Result := StrPas(Version);
         if rev then begin
             if (VerQueryValue(Pchar(VersionBuffer),'\StringFileInfo\041904E3\Revision',Pointer(Revision),VersionSize))
             then
                Result := perljoin('.', [Result, StrPas(Revision)]);
         end;
   end;
end;

function GetApplicationVersion_Small : String;
begin
    Result := copy(GetApplicationVersion, 5, MaxInt);
end;


end.
