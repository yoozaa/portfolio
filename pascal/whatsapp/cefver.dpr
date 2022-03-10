program cefver;

{$APPTYPE CONSOLE}

uses
  uceftypes, 
  uCEFMiscFunctions;

var
   v : TFileVersionInfo;
begin

   GetDLLVersion(paramstr(1) + '\libcef.dll', v);
   writeln(v.MajorVer, '.', v.MinorVer, '.', v.Release, '.', v.Build);

end.
