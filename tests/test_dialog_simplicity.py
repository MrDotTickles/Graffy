import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget, QPushButton
from PyQt6.QtCore import QRect
from pandas.testing import assert_frame_equal
from omnigraph.ui.dialogs.import_dialog import ImportDialog
from omnigraph.ui.dialogs.ai_extractor_dialog import AIDataExtractorDialog
from omnigraph.ui.dialogs.export_dialog import ExportDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.samples import SampleProjects
from omnigraph.graphing.plot_manager import PlotManager

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

def test_both_import_routes_read_the_same_instrument_text(app):
    text = "Time (s),Signal (V)\n0,10\n1,20\n2,30"
    regular = ImportDialog(initial_text=text)
    graph_import = AIDataExtractorDialog(SampleProjects.create_spectroscopy_sample())
    graph_import.tabs_source.setCurrentIndex(1)
    graph_import.txt_paste.setPlainText(text)
    graph_import._run_extraction()
    assert_frame_equal(regular.imported_dataframe, graph_import.extraction_result.dataframe)
    assert regular.btn_ok.isEnabled()
    assert "AI" not in graph_import.windowTitle()
    regular.close(); graph_import.close()

def test_import_advanced_settings_survive_collapse(app):
    dialog = ImportDialog()
    assert not dialog.btn_ok.isEnabled()
    dialog.combo_header.setCurrentIndex(3)
    dialog.parsing_toggle.setChecked(True)
    dialog.parsing_toggle.setChecked(False)
    assert dialog.combo_header.currentData() == "none"
    assert dialog.chk_auto_plot.parent() is not dialog.destination_options
    dialog.close()

def test_export_does_not_replace_without_permission(app, tmp_path, monkeypatch):
    project=SampleProjects.create_spectroscopy_sample()
    dialog=ExportDialog(PlotManager(project.graphs[0],project))
    path=tmp_path/"existing.png"; path.write_bytes(b"keep me")
    dialog.txt_path.setText(str(path))
    monkeypatch.setattr(QMessageBox,"question",lambda *a,**k:QMessageBox.StandardButton.No)
    monkeypatch.setattr(dialog.plot_manager,"export_image",lambda *a,**k:pytest.fail("must not overwrite"))
    dialog._on_export()
    assert path.read_bytes()==b"keep me"
    dialog.close()

def test_small_screen_keeps_import_buttons_accessible(app, monkeypatch):
    class Screen:
        def availableGeometry(self): return QRect(0,0,400,400)
    monkeypatch.setattr(QWidget,"screen",lambda self:Screen())
    dialog=ImportDialog(initial_text="X,Y\n0,1\n1,2")
    dialog.show(); app.processEvents()
    assert dialog.width() <= 368
    assert dialog.height() <= 352
    assert dialog.btn_ok.mapTo(dialog,dialog.btn_ok.rect().bottomRight()).y() <= dialog.height()
    assert dialog.btn_ok.mapTo(dialog,dialog.btn_ok.rect().bottomRight()).x() <= dialog.width()
    dialog.close()

def test_specialized_import_preview_is_not_hidden_in_advanced_options(app):
    dialog=AIDataExtractorDialog(SampleProjects.create_spectroscopy_sample())
    dialog.show(); app.processEvents()
    preview=next(b for b in dialog.findChildren(QPushButton) if b.text()=="Preview data")
    assert preview.isVisible()
    assert not dialog.raw_options.isVisible()
    dialog.close()
