"""Keep Qt lifetimes consistent when all GUI test modules share one process."""
import gc
import os
import hashlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6 import QtCore
from PyQt6.QtCore import QCoreApplication, QEvent
from pathlib import Path
from PyQt6.QtWidgets import QApplication


_OriginalSettings=QtCore.QSettings
_settings_root=None


class IsolatedSettings(_OriginalSettings):
    def __init__(self,*args,**kwargs):
        if (len(args)>=2 and isinstance(args[0],str) and isinstance(args[1],str)) or not args:
            if _settings_root is None:
                raise RuntimeError("QSettings must be initialized by the session fixture")
            identity="\0".join(args[:2]) if args else "default"
            filename=hashlib.sha256(identity.encode()).hexdigest()+".ini"
            tail=args[2:] if args else ()
            super().__init__(str(_settings_root/filename),_OriginalSettings.Format.IniFormat,*tail,**kwargs)
        else:
            super().__init__(*args,**kwargs)


# Applied before test collection so even local imports use isolated preferences.
QtCore.QSettings=IsolatedSettings


@pytest.fixture(scope="session", autouse=True)
def qt_test_application(tmp_path_factory):
    global _settings_root
    _settings_root=tmp_path_factory.mktemp("preferences")
    application=QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    yield application


@pytest.fixture(autouse=True)
def finish_qt_deletions(qt_test_application):
    yield
    # Python cycles and deleteLater() otherwise outlive a test and are collected
    # while a later global stylesheet is traversing the old native widgets.
    gc.collect()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
