"""Shared pytest setup.

The window tests (test_app_starts.py, test_device_editors.py) create Qt widgets. If any of
them is still alive when Python shuts down, Qt can crash the run on exit (after every test
has passed). So at the end of the session every remaining window is deleted and Qt is shut
down first, while Python is still running normally.
"""
import sys


def pytest_sessionfinish(session, exitstatus):
    if "PySide6.QtWidgets" not in sys.modules:
        return                          # no window tests ran
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.shutdown()
