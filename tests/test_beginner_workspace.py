import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import pytest
from PyQt6.QtWidgets import QApplication, QToolBar, QToolButton
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.dialogs.welcome_dialog import WelcomeDialog

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

def test_welcome_choices_and_close(app):
    dialog = WelcomeDialog()
    dialog.select("sample")
    assert dialog.choice == "sample"
    assert dialog.result() == dialog.DialogCode.Accepted

def test_welcome_recent_project_action(app, tmp_path, monkeypatch):
    recent = tmp_path / "Experiment & Notes.kgraph"
    window = MainWindow()
    monkeypatch.setattr(window, "_load_recent_projects", lambda: [str(recent)])
    opened = []
    monkeypatch.setattr(window, "open_recent_project", opened.append)

    def choose_recent(dialog):
        button = next(b for b in dialog.findChildren(QToolButton) if b.text() == "Recent projects")
        action = button.menu().actions()[0]
        assert action.text() == "Experiment && Notes.kgraph"
        action.trigger()
        return dialog.result()

    monkeypatch.setattr(WelcomeDialog, "exec", choose_recent)
    window.show_getting_started()
    assert opened == [str(recent)]


@pytest.mark.parametrize("width,height", [(800,600),(1024,768),(1440,900)])
def test_guided_workspace_stays_usable_and_restores_advanced_tools(app,width,height):
    window = MainWindow(project=SampleProjects.create_spectroscopy_sample())
    window.enable_guided_workspace()
    window.setMinimumSize(640,480)
    window.resize(width,height)
    window.show()
    app.processEvents()
    assert window.quick_start_toolbar.isVisible()
    assert window.center_tabs.width() > 300
    assert not window.findChild(QToolBar,"ToolbarFileData").isVisible()
    assert not window.dock_properties.isVisible()
    window.advanced_tools_action.setChecked(True)
    assert window.findChild(QToolBar,"ToolbarFileData").isVisible()
    assert window.dock_properties.isVisible()
    window.close()


def test_guided_workspace_cancels_destructive_new_project(app, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    window = MainWindow()
    window.enable_guided_workspace()
    original = window.project
    window.project.workbooks[0].sheets[0].columns[0].data = [1,2,3]
    monkeypatch.setattr(QMessageBox,"question",lambda *a,**k: QMessageBox.StandardButton.Cancel)
    window.new_project()
    assert window.project is original
    assert not window._confirm_pending_changes()
    monkeypatch.setattr(QMessageBox,"question",lambda *a,**k: QMessageBox.StandardButton.Discard)
    window.close()
