"""Nonblocking startup/manual update check and install offer, as in FermatTrace."""
from PySide6 import QtCore,QtWidgets as Q
import updater,branding

class Worker(QtCore.QThread):
    done=QtCore.Signal(object,str)
    def __init__(self,task,parent):super().__init__(parent);self.task=task
    def run(self):
        try:self.done.emit(self.task(),'')
        except Exception as error:self.done.emit(None,str(error))

class Controller(QtCore.QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.worker=None
        Q.QApplication.instance().aboutToQuit.connect(self.stop)
    def stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption();self.worker.wait(35000)
    def check(self,manual=False):
        if self.worker and self.worker.isRunning():return
        if not updater.enabled() or updater.install_dir() is None:
            if manual:Q.QMessageBox.information(self.window,'FringeScope updates','Updates are disabled in this local review build. No network request was made. Released installed copies can check automatically; source and portable copies do not self-update.')
            return
        self.worker=Worker(lambda:updater.available(branding.VERSION),self)
        self.worker.done.connect(lambda result,error:self.checked(result,error,manual));self.worker.start()
    def checked(self,result,error,manual):
        if error or not result:
            if manual:Q.QMessageBox.information(self.window,'FringeScope updates',error or 'No newer stable installer is available.')
            return
        if Q.QMessageBox.question(self.window,'FringeScope update',f'Version {result["version"]} is available. Download, verify and install it now? FringeScope will close and reopen. Finish any unsaved work first.')!=Q.QMessageBox.StandardButton.Yes:return
        QtCore.QTimer.singleShot(0,lambda:self.start_download(result))
    def start_download(self,result):
        self.worker=Worker(lambda:updater.download(result,cancel=lambda:QtCore.QThread.currentThread().isInterruptionRequested()),self)
        self.worker.done.connect(self.downloaded);self.worker.start()
    def downloaded(self,path,error):
        if error:Q.QMessageBox.warning(self.window,'Update not installed',error);return
        try:updater.launch(path,updater.install_dir())
        except Exception as error:Q.QMessageBox.warning(self.window,'Update not installed',str(error));return
        self.window.close()
