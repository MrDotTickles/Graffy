import numpy as np
import pytest
from omnigraph.core.column_formula import FormulaEvaluator
from omnigraph.core.worksheet import Worksheet

@pytest.mark.parametrize("expression",[
    "np.load('private.npy')", "np.save('output.npy', A)",
    "np.__dict__", "np.ctypeslib.load_library('x','.')", "A.__class__",
    "().__class__.__base__", "(lambda: 1)()", "[x for x in A]",
    "__import__('os')", "np.array([1]).tofile('output.bin')",
    "col.__globals__", "np.sin.__class__", "np.loadtxt('private.csv')"])
def test_formulas_cannot_access_files_or_python_internals(expression,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    sheet=Worksheet.create_default(num_rows=3)
    sheet.columns[0].data=[1,2,3]
    with pytest.raises(ValueError):FormulaEvaluator.evaluate(expression,sheet)
    assert not list(tmp_path.iterdir())

def test_approved_numpy_math_and_slices_still_work():
    sheet=Worksheet.create_default(num_rows=3);sheet.columns[0].data=[1,2,3]
    result=FormulaEvaluator.evaluate('np.where(A > 1, np.sqrt(A), 0)',sheet)
    assert np.allclose(result,[0,np.sqrt(2),np.sqrt(3)])
    assert np.allclose(FormulaEvaluator.evaluate('np.sin(A) + mean(A)',sheet),np.sin([1,2,3])+2)


@pytest.mark.parametrize("url",["http://example.com/update.exe","file:///private/file","https://user:password@example.com/a"])
def test_update_download_rejects_unsafe_urls(url,tmp_path,monkeypatch,qt_test_application):
    from omnigraph.core.updater import FileDownloadWorker
    import omnigraph.core.updater as updater
    def blocked(*args,**kwargs):raise AssertionError("Network must not be called")
    monkeypatch.setattr(updater.urllib.request,'urlopen',blocked)
    worker=FileDownloadWorker(url,str(tmp_path/'update.exe'))
    errors=[];worker.error.connect(errors.append);worker.run()
    assert errors and 'HTTPS' in errors[0]
    assert not list(tmp_path.iterdir())


def test_release_gate_rejects_private_files_and_redacts_secrets(tmp_path):
    from scripts.public_release_audit import private_path,inspect_bytes
    assert private_path('Projects/private.kgraph')
    assert private_path('nested/.env.production')
    assert private_path('signing/certificate.pfx')
    assert not private_path('.env.example')
    token='gh'+'p_'+'a'*36
    result=inspect_bytes(token.encode(),'example.txt')
    assert result and token not in str(result)


@pytest.mark.parametrize("url",["file:///private/file","javascript:alert(1)","http://example.com"])
def test_update_browser_fallback_rejects_non_web_actions(url,qt_test_application,monkeypatch):
    from omnigraph.ui.dialogs import update_dialog
    from omnigraph.core.updater import UpdateInfo
    dialog=update_dialog.UpdateDialog(auto_check=False)
    dialog.last_info=UpdateInfo('1','2',True,'','',url,html_url=url)
    opened=[]
    monkeypatch.setattr(update_dialog.QDesktopServices,'openUrl',lambda value:opened.append(value))
    monkeypatch.setattr(update_dialog.QMessageBox,'warning',lambda *args:None)
    dialog._on_browser_fallback_clicked()
    assert not opened
    dialog.close()


def test_rebuilding_views_at_nondefault_interface_scale(qt_test_application):
    from omnigraph.ui.main_window import MainWindow
    from omnigraph.ui.samples import SampleProjects
    window=MainWindow(project=SampleProjects.create_spectroscopy_sample())
    window.set_interface_scale(1.25,persist=False)
    window._populate_all_views()
    assert window.center_tabs.count()==2
    window.set_zoom_level(1.2)
    window._populate_all_views()
    assert window.center_tabs.count()==2
    window.set_interface_scale(1,persist=False);window.reset_zoom()
    window._remember_saved_state();window.close()


def test_release_gate_covers_json_secrets_and_credential_stores():
    import json
    from scripts.public_release_audit import inspect_bytes,private_path
    secret='a'*32
    result=inspect_bytes(json.dumps({'api_key':secret}).encode(),'config.json')
    assert result and secret not in str(result)
    for name in ('.npmrc','.netrc','id_ed25519','data/private.sqlite','config.pem'):
        assert private_path(name)


def test_vendor_license_does_not_substitute_for_application_license(tmp_path):
    from scripts.public_release_audit import audit_package
    resource=tmp_path/'_internal';vendor=resource/'thirdparty';vendor.mkdir(parents=True)
    (vendor/'LICENSE').write_text('A vendor license is not the application license')
    findings,_=audit_package(tmp_path)
    assert {'path':'LICENSE','rule':'missing-distribution-notice'} in findings


def test_package_requires_exact_application_license(tmp_path):
    from scripts.public_release_audit import audit_package
    resource=tmp_path/'_internal';resource.mkdir()
    (resource/'LICENSE').write_text('Not the selected application license')
    findings,_=audit_package(tmp_path)
    assert {'path':'LICENSE','rule':'wrong-application-license'} in findings


def test_public_toolbar_icons_are_allowed_but_user_pdfs_are_not():
    from scripts.public_release_audit import private_path
    assert not private_path('_internal/matplotlib/mpl-data/images/back.pdf',package=True)
    assert private_path('_internal/matplotlib/mpl-data/images/private-report.pdf',package=True)
    assert private_path('exports/back.pdf',package=True)
