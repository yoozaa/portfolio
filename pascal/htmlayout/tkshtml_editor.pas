unit tkshtml_editor;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, tks_pydocument, Menus, SynEditHighlighter, SynHighlighterHtml,
  SynEdit, SynMemo, ExtCtrls, TB2Item, TB2Dock, TB2Toolbar, tks_TLB,
  StdCtrls;

type
  TpyHTMLEditor = class(TfmPyDocument)
    HTMLMemo: TSynMemo;
    HTMLHighlighter: TSynHTMLSyn;
    HTMLSaveItem: TTBItem;
    selectoredit: TEdit;
    TBControlItem1: TTBControlItem;
    selectitem: TTBItem;
    procedure HTMLSaveItemClick(Sender: TObject);
    procedure selectitemClick(Sender: TObject);
    procedure selectoreditKeyDown(Sender: TObject; var Key: Word;
      Shift: TShiftState);
  private
    { Private declarations }
    FEditor : Variant;
  protected
    procedure DoSetDockManager(wm : ITKSWindowManager); override;
  public
    { Public declarations }
    constructor CreateWithEditor(Editor : Variant);
    destructor Destroy; override;
    procedure SaveToFile;
  end;


implementation

{$R *.dfm}

uses VarPyth;

constructor TpyHTMLEditor.CreateWithEditor(Editor : Variant);
begin
    Inherited Create(nil);
    FEditor := Editor;
end;

destructor TpyHTMLEditor.Destroy;
begin
    FEditor := Null;
    Inherited;
end;

procedure TpyHTMLEditor.HTMLSaveItemClick(Sender: TObject);
begin
  inherited;
  SavetoFile;
end;

procedure TpyHTMLEditor.SaveToFile;
begin
    FEditor.savetofile(VarPythonCreate(HTMLMemo.Lines.Text))
end;

procedure TpyHTMLEditor.selectitemClick(Sender: TObject);
begin
  inherited;
  FEditor.select(VarPythonCreate(selectoredit.text))
end;

procedure TpyHTMLEditor.selectoreditKeyDown(Sender: TObject; var Key: Word;
  Shift: TShiftState);
begin
  inherited;
  if key = VK_RETURN then begin
     key := 0;
     HTMLSaveItemClick(nil);
  end;
end;

procedure TpyHTMLEditor.DoSetDockManager(wm : ITKSWindowManager);
begin
    Inherited;
    HTMLMemo.Lines.Text := FEditor.loadfromfile();
end;

end.
