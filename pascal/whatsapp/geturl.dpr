program geturl;

uses sysutils, whatsapp_tools;

begin

     try
     if paramcount > 1 then begin
         if not retrieve_to_file(paramstr(1), paramstr(2)) then 
             writeln('error')
     end else 
         writeln('no params');
     except
          on e : exception do
              writeln('error: ', e.message)
     end;

end.