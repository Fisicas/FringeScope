"""Early Qt splash and actual startup stages. No numerical imports at module load."""
import sys, time, traceback
from PySide6 import QtWidgets as Q, QtCore, QtGui, QtSvg
import branding as B

STAGES=('Loading numerical and plotting libraries','Building the interface',
        'Preparing the simulated signal','Opening FringeScope')


class Splash(Q.QWidget):
    def __init__(self):
        super().__init__(None,QtCore.Qt.WindowType.SplashScreen|QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(810,450);self.setWindowTitle(B.NAME);self.setWindowIcon(B.icon())
        self.background=QtSvg.QSvgRenderer(str(B.ASSETS/'splash_background.svg'))
        if not self.background.isValid():raise FileNotFoundError('Missing FringeScope splash background')
        self.current=None;self.started=None;self.timings={};self.stage_history=[]
        screen=Q.QApplication.primaryScreen()
        if screen:self.move(screen.availableGeometry().center()-self.rect().center())

    def begin(self,index):
        now=time.perf_counter()
        if self.current is not None:self.timings[self.current]=now-self.started
        self.current=index;self.started=now;self.stage_history.append(index)
        self.repaint()
        Q.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def complete(self):
        if self.current is not None:self.timings[self.current]=time.perf_counter()-self.started
        self.current=None;self.repaint()

    def paintEvent(self,event):
        p=QtGui.QPainter(self)
        p.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing|QtGui.QPainter.RenderHint.TextAntialiasing)
        p.scale(self.width()/1080,self.height()/600)
        self.background.render(p,QtCore.QRectF(0,0,1080,600))
        for index,label in enumerate(STAGES):
            y=310+index*34;done=index in self.timings;active=index==self.current
            color=B.GREEN if done else B.AMBER if active else B.LINE
            p.setPen(QtGui.QPen(QtGui.QColor(color),2.5));p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawEllipse(QtCore.QPointF(306,y-6),7,7)
            if done:
                p.drawLine(QtCore.QPointF(302,y-6),QtCore.QPointF(305,y-3))
                p.drawLine(QtCore.QPointF(305,y-3),QtCore.QPointF(311,y-10))
            elif active:
                p.setBrush(QtGui.QColor(B.AMBER));p.drawEllipse(QtCore.QPointF(306,y-6),3,3)
            font=QtGui.QFont(B.FONT);font.setPixelSize(19);p.setFont(font)
            p.setPen(QtGui.QColor(B.TEXT if done or active else B.MUTED))
            p.drawText(QtCore.QPointF(326,y),label)
            if done:
                font.setPixelSize(15);p.setFont(font);p.setPen(QtGui.QColor(B.MUTED))
                p.drawText(QtCore.QRectF(930,y-20,100,26),QtCore.Qt.AlignmentFlag.AlignRight,f'{self.timings[index]:.2f} s')
        p.end()


def bootstrap(argv=None,observer=None):
    """Return the ready application/window; observer is only for startup QA."""
    args=list(sys.argv if argv is None else argv)
    application=Q.QApplication.instance() or Q.QApplication(args)
    application.setApplicationName(B.NAME);application.setApplicationVersion(B.VERSION)
    B.ensure_fonts();application.setWindowIcon(B.icon())
    splash=None
    try:
        if '--no-splash' not in args:
            splash=Splash();splash.show()
        def stage(index):
            if splash:splash.begin(index)
            if observer:observer(index,splash,None)
        stage(0)
        # The visible splash is already painted before these imports execute.
        from app import MainWindow,configure_app
        configure_app(application);stage(1)
        window=MainWindow(startup_progress=stage)
        if window.result is None:raise RuntimeError('Initial simulated signal could not be prepared')
        stage(3);window.show()
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        if splash:splash.complete()
        if observer:observer('ready',splash,window)
        if splash:splash.close()
        window._startup_timings=dict(splash.timings) if splash else {}
        return application,window
    except Exception:
        if splash:splash.close()
        raise


def main():
    try:
        from runtime_paths import user_dir
        import os
        os.environ.setdefault('MPLCONFIGDIR',str(user_dir()/'matplotlib'))
        application,window=bootstrap()
        if '--self-test-output' in sys.argv:
            from bundle_selftest import run
            run(application,window,sys.argv[sys.argv.index('--self-test-output')+1])
            window.close();return 0
        return application.exec()
    except Exception:
        details=traceback.format_exc();print(details,file=sys.stderr)
        if Q.QApplication.instance():
            Q.QMessageBox.critical(None,'FringeScope startup error','FringeScope could not start.\n\n'+details)
        return 1


if __name__=='__main__':sys.exit(main())
