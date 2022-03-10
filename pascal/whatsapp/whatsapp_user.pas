unit whatsapp_user;

interface

uses sysutils;

var
    WAPP_USERS : string = 'users\';
    WAPP_USERNAME : string = 'default';
    WAPP_DEFAULTCOOKIESDIR : string = 'cookies\';
    WAPP_DEFAULTCACHEDIR : string = 'cache\';
    WAPP_DEFAULTDATADIR : string = 'data\';


const
    WAPP_DEFAULT_PAGE = 'https://web.whatsapp.com/';
    //WAPP_DEFAULT_PAGE = 'https://web.whatsapp222.com/';
    //WAPP_DEFAULT_PAGE = 'http://vlad.tks.ru';

function wapp_get_cookiesdir : string;
function wapp_get_cachedir : string;

procedure setcookiesdirectory;

implementation

uses uCEFInterfaces, uCEFCookieManager, uCEFApplication;

function wapp_get_userdir : string;
begin
    Result := WAPP_USERS + wapp_username
end;

function wapp_get_cookiesdir : string;
begin
    Result := wapp_get_userdir + '\' + WAPP_DEFAULTCOOKIESDIR
end;

function wapp_get_cachedir : string;
begin
    Result := wapp_get_userdir + '\' + WAPP_DEFAULTCACHEDIR
end;

function wapp_get_datadir : string;
begin
    Result := wapp_get_userdir + '\' + WAPP_DEFAULTDATADIR
end;

procedure setcookiesdirectory;
var
  CookieManager: ICefCookieManager;
  CookiesPath  : String;
begin
  CookiesPath := wapp_get_cookiesdir;
  CookieManager := TCefCookieManagerRef.Global(nil);
  CookieManager.SetStoragePath(CookiesPath, True, nil)
end;

initialization

  if paramcount > 0 then
      wapp_username := paramstr(1);

  //CefUserDataPath := ExtractFilePath(paramstr(0)) + wapp_get_datadir;

end.
