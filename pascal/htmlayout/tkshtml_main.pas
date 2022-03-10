unit tkshtml_main;

interface

uses PythonEngine, tkscom, Dialogs;

procedure inittkshtml; cdecl;

function AddMethod( AMethodName  : PAnsiChar;
                    AMethod  : PyCFunction;
                    ADocString : PAnsiChar ) : PPyMethodDef;

var
  PyModule : TPythonModule;

implementation

uses tkshtml_func, tkshtml_data, pyWrap, tks_pythonengine;

var
   engine : TPythonEngine;

procedure inittkshtml;
begin
  try
    engine := createPythonEngine(True);
    PyModule := TPythonModule.Create(nil);
    PyModule.ModuleName := 'tkshtml';
    tkshtml_func.init_func;
    PyModule.Engine := engine;
    pyWrap.initwrap(PyModule);
    PyModule.Initialize;
    dm := Tdm.Create(nil);
  except
  end;
end;


function AddMethod( AMethodName  : PAnsiChar;
                    AMethod  : PyCFunction;
                    ADocString : PAnsiChar ) : PPyMethodDef;
begin
   Result := PyModule.AddMethod(AMethodName, AMethod, ADocString);
end;

initialization

finalization

  if Assigned(dm) then
      dm.Free;

  freewrap;
  PyModule.Free;

end.
