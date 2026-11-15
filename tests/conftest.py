"""Keep one Qt application alive for the GUI contract tests."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest

@pytest.fixture(scope='session',autouse=True)
def qt_application():
    from PySide6.QtWidgets import QApplication
    application=QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    yield application
