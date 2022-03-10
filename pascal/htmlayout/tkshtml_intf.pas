unit tkshtml_intf;

interface

uses PythonEngine;

type

    IPyHtmlAction = interface(IUnknown)
    ['{9D02E223-08E2-4568-90C2-EA7F6F18436F}']
        function DoPyHtmlAction(const cmd : Integer; const param : PPyObject) : HResult;
    end;

implementation

end.
