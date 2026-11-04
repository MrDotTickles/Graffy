"""Keep Qt lifetimes consistent when all GUI test modules share one process."""
import gc
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qt_test_application():
    # Module-local fixtures must not destroy and recreate the native QApplication.
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    yield application


@pytest.fixture(autouse=True)
def finish_qt_deletions(qt_test_application):
    yield
    # Python cycles and deleteLater() otherwise outlive a test and are collected
    # while a later global stylesheet is traversing the old native widgets.
    gc.collect()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
