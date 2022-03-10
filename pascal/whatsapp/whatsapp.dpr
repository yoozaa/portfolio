program whatsapp;

uses
  sysutils,
  uCEFApplication,
  uceftypes,
  ucefinterfaces,
  Windows,
  Forms,
  WideStrUtils,
  BigIni,
  main in 'main.pas' {MainForm},
  whatsapp_user in 'whatsapp_user.pas',
  whatsapp_value in 'whatsapp_value.pas',
  pyDecl in '..\..\python\pyDecl.pas',
  whatsapp_tools in 'whatsapp_tools.pas',
  udform in '..\..\common\udform.pas' {DForm},
  whatsapp_clicker in 'whatsapp_clicker.pas',
  whatsapp_request in 'whatsapp_request.pas',
  whatsapp_pythonthread in 'whatsapp_pythonthread.pas',
  whatsapp_crypto in 'whatsapp_crypto.pas',
  whatsapp_code in 'whatsapp_code.pas',
  //whatsapp_prefs in 'whatsapp_prefs.pas' {TfmPrefs},
  whatsapp_request_get in 'whatsapp_request_get.pas';

{$R *.res}
{$R version.res}
{$IFDEF DEBUGVERSION}
     // {$MESSAGE FATAL 'debugversion'};
{$ENDIF}

{$SetPEFlags IMAGE_FILE_LARGE_ADDRESS_AWARE}


var
    cert_filename : string = 'whatsapp.crt';
    i : Integer;
    error_message : WideString = '';
    user_agent : WideString;

    cefroot : WideString;

procedure AlterCommandLine (const processType: ustring; const commandLine: ICefCommandLine);
begin
    commandLine.AppendSwitch('enable-aggressive-domstorage-flushing');
end;

function get_user_agent(const filename, defvalue : WideString) : WideString;
begin
    result := defvalue;
    if fileexists(filename) then
    with TbigInifile.Create(filename) do try
        Result := readstring('settings', 'user_agent', defvalue);
    finally
        Free;
    end;
end;

begin

  GlobalCEFApp              := TCefApplication.Create;
  try

      cefroot := WideFormat('cef_%d.%d.%d.%d', [
          CEF_SUPPORTED_VERSION_MAJOR,
          CEF_SUPPORTED_VERSION_MINOR,
          CEF_SUPPORTED_VERSION_RELEASE,
          CEF_SUPPORTED_VERSION_BUILD
      ]);

      GlobalCEFApp.FrameworkDirPath     := cefroot;
      GlobalCEFApp.ResourcesDirPath     := cefroot;
      GlobalCEFApp.LocalesDirPath       := WideFormat('%s\locales', [cefroot]);

      GlobalCEFApp.RemoteDebuggingPort := 9000;
      // GlobalCEFApp.RenderProcessHandler := TCustomRenderProcessHandler.Create;

      GlobalCEFApp.OnWebKitInitialized := TCustomRenderProcessHandler.OnWebKitInitialized;
      GlobalCEFApp.OnContextCreated := TCustomRenderProcessHandler.OnContextCreated;
      GlobalCEFApp.OnContextReleased := TCustomRenderProcessHandler.OnContextReleased;


//      GlobalCEFApp.BrowserProcessHandler := TCefBrowserProcessHandlerOwn.Create;

//      GlobalCEFApp.FlashEnabled := True;
      GlobalCEFApp.FastUnload   := True;   // Enable the fast unload controller, which speeds up tab/window close by running a tab's onunload js handler independently of the GUI

      GlobalCEFApp.Cache := ExtractFilePath(paramstr(0)) + wapp_get_cachedir;

      if paramcount > 0 then begin
          udform.data3_ini := Format('users\%s\whatsapp.ini', [ParamStr(1)]);

          for i := 1 to paramcount do begin
              if paramstr(i) = '-c' then begin
                  if i < paramcount then begin
                      cert_filename := paramstr(i + 1);
                  end;
              end;
          end;

          if FileExists(cert_filename) then
              check_cert(cert_filename, ParamStr(1), error_message)
          else
              error_message := WideFormat('Не найден файл сертификата привязки %s', [cert_filename]);

      end else begin
          udform.data3_ini := 'users\default\whatsapp.ini';
          error_message := 'Не указан номер телефона';
      end;

      GlobalCEFApp.AddCustomCommandLine('--enable-aggressive-domstorage-flushing');

      user_agent := '';
      user_agent := get_user_agent('whatsapp.ini', user_agent);
      user_agent := get_user_agent(udform.data3_ini, user_agent);
      if user_agent <> '' then 
          GlobalCEFApp.UserAgent := user_agent;

      GlobalCEFApp.SingleProcess := True;
      if GlobalCEFApp.StartMainProcess then begin

          if error_message <> EmptyStr then begin
              MessageBoxW(0, PWideChar(WideString(error_message)), 'Error', 0)
          end else begin
              Application.Initialize;
              Application.CreateForm(TMainForm, MainForm);
              PyDecl.initPyDecl(MainForm.AfterInitPython);
              Application.Run;
          end;

      end;

  finally
      GlobalCEFApp.Free;
  end;

end.
