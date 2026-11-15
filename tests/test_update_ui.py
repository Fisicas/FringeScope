import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6 import QtWidgets as Q,QtTest
from update_ui import Controller
import updater


def test_simulated_offer_download_install_flow(monkeypatch,tmp_path):
 app=Q.QApplication.instance() or Q.QApplication([])
 class Window(Q.QWidget):
  closed=False
  def closeEvent(self,event):self.closed=True;super().closeEvent(event)
 window=Window();controller=Controller(window);events=[]
 release={'version':'0.12.0'}
 monkeypatch.setattr(updater,'enabled',lambda:True)
 monkeypatch.setattr(updater,'install_dir',lambda:tmp_path)
 monkeypatch.setattr(updater,'available',lambda version:release)
 monkeypatch.setattr(Q.QMessageBox,'question',lambda *args:Q.QMessageBox.StandardButton.Yes)
 monkeypatch.setattr(updater,'download',lambda value,**kwargs:tmp_path/'fixture.exe')
 monkeypatch.setattr(updater,'launch',lambda exe,folder:events.append((exe,folder)))
 controller.check()
 for _ in range(100):
  QtTest.QTest.qWait(20)
  if window.closed:break
 controller.stop()
 assert events==[(tmp_path/'fixture.exe',tmp_path)] and window.closed
 window.deleteLater();app.processEvents()


def test_publication_hold_stops_before_worker(monkeypatch):
 app=Q.QApplication.instance() or Q.QApplication([])
 window=Q.QWidget();controller=Controller(window)
 monkeypatch.setattr(updater,'enabled',lambda:False)
 monkeypatch.setattr(updater,'available',lambda version:(_ for _ in ()).throw(AssertionError('Unexpected update check')))
 controller.check()
 assert controller.worker is None
 window.deleteLater();app.processEvents()
