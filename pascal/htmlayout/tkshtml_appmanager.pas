unit tkshtml_appmanager;

interface

uses windows, tks_appmanager, tks_TLB;

type

    IHTMLManager = interface
    ['{1B4698D4-6356-444C-B55C-97BF670DA504}']
        function set_params(HTMLManager : Variant; const SavePrior : boolean) : HResult; stdcall;
    end;

    THTMLAppManager = class(TAppManager, IHTMLManager)
    private
        FHTMLManager : Variant;
        FHistoryModule : Variant;
        FSavePrior : boolean;
        FDefaultWindow : boolean;
        function get_iwindow() : LongInt;
    protected
        procedure DoShowWindow(var WindowType : Integer; out iWindow : ITKSWindow); override;
        function getDefaultWindowType : Integer; override;
        function IsCurrentWindowType(const WindowType : Integer) : boolean; override;
        function AppendToHistory(const WindowType : Integer; const iWindow : ITKSWindow) : boolean; override;
    public
        constructor Create(HTMLManager : variant; wm : ITKSWindowManager; const SavePrior : boolean; const DefaultWindow: boolean); virtual;
        function set_params(HTMLManager : Variant; const SavePrior : boolean) : HResult; stdcall;
        function appendedtohistory(const WindowType : Integer) : HResult; override; stdcall;
        function getdescription : WideString; override; stdcall;
    end;

const

     I_HTML_MAINWINDOW = 0;
     I_HTML_HISTORY = 1;

implementation

uses pyHTML, VarPyth, modulesintf;

function THTMLAppManager.getdescription : WideString;
begin
  Result := 'HTMLAppManager';
end;

function THTMLAppManager.get_iwindow() : LongInt;
begin
   Result := LongInt(windowmanager);
end;

procedure THTMLAppManager.DoShowWindow(var WindowType : Integer; out iWindow : ITKSWindow);
var
   pwindow : ITKSWindow;
   iActiveWindow : ITKSActiveWindow;
   defwindow : ITKSDefaultWindow;
begin
    if WindowType <> I_HTML_MAINWINDOW then
       FHTMLManager := FHistoryModule.get_history_element(self.get_iwindow());
    if not VarIsNone(FHTMLManager) then begin
       pwindow :=  nil;
       if FSavePrior then begin
          if windowmanager.QueryInterface(ITKSActiveWindow, iActiveWindow) = S_OK then
             iActiveWindow.get_active_window(pwindow);
       end;
       iWindow := TfmHTMLView.CreateWithManager(FHTMLManager, windowmanager, pwindow);
       WindowType := FHistoryModule.append_to_history(FHTMLManager, self.get_iwindow());
       FSavePrior := False;
       if FDefaultWindow then begin
           if WindowManager.QueryInterface(ITKSDefaultWindow, defwindow) = S_OK then
               defwindow.SetDefaultWindow();
       end;
    end;
end;

function THTMLAppManager.getDefaultWindowType : Integer;
begin
    Result := I_HTML_MAINWINDOW;
end;

constructor THTMLAppManager.Create(HTMLManager : variant; wm : ITKSWindowManager; const SavePrior : boolean; const DefaultWindow : Boolean);
begin
   Inherited CreateManager(wm);
   FHistoryModule := import('gtd.html.history');
   FDefaultWindow := DefaultWindow;
   set_params(HTMLManager, SavePrior);
end;

function THTMLAppManager.set_params(HTMLManager : Variant; const SavePrior : boolean) : HResult;
begin
   FHTMLManager := HTMLManager;
   FSavePrior := SavePrior;
   Result := S_OK;
end;

function THTMLAppManager.IsCurrentWindowType(const WindowType : Integer) : boolean;
begin
   Result := False;
end;

function THTMLAppManager.AppendToHistory(const WindowType : Integer; const iWindow : ITKSWindow) : boolean;
begin
   Result := WindowType <> I_HTML_MAINWINDOW;
end;

function THTMLAppManager.appendedtohistory(const WindowType : Integer) : HResult;
begin
    Result := Inherited appendedtohistory(WindowType);
    FHistoryModule.append_to_history(None, self.get_iwindow());
end;

end.
