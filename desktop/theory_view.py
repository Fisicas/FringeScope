"""Offline publication-style theory reader. No browser engine or network needed."""
from pathlib import Path
from PySide6 import QtWidgets as Q,QtCore,QtGui
from paper_style import register_fonts

class TheoryPage(Q.QWidget):
    def __init__(self,root,parent=None):
        super().__init__(parent);self.root=Path(root);self.family=register_fonts();self.theme='dark'
        layout=Q.QVBoxLayout(self);layout.setContentsMargins(0,8,0,0)
        toolbar=Q.QHBoxLayout();layout.addLayout(toolbar)
        label=Q.QLabel('Theory and evidence');toolbar.addWidget(label,1)
        toolbar.addWidget(Q.QLabel('Text size'))
        self.font_size=Q.QSpinBox();self.font_size.setRange(16,28);self.font_size.setSuffix(' px');self.font_size.setValue(20)
        self.font_size.setToolTip('Adjust body text and equations together.');toolbar.addWidget(self.font_size)
        open_copy=Q.QPushButton('Open reading copy');open_copy.clicked.connect(self.open_reading_copy);toolbar.addWidget(open_copy)
        row=Q.QHBoxLayout();row.setContentsMargins(0,4,0,0);layout.addLayout(row,1)
        self.contents=Q.QListWidget();self.contents.setFixedWidth(220);self.contents.setWordWrap(True)
        self.contents.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.contents.setStyleSheet('QListWidget {background:#f7f8f9;color:#35424e;border:0;font-size:13px;padding:10px;} QListWidget::item {padding:10px 4px;border-bottom:1px solid #e1e5e8;} QListWidget::item:selected {background:#e5edef;color:#163f4c;}')
        from build_theory import headings
        for title,anchor in headings(self.root):
            item=Q.QListWidgetItem(title);item.setData(QtCore.Qt.ItemDataRole.UserRole,anchor);self.contents.addItem(item)
        self.contents.currentItemChanged.connect(self.navigate);row.addWidget(self.contents)
        self.reader=Q.QTextBrowser();self.reader.setOpenExternalLinks(True)
        self.reader.setStyleSheet(f'QTextBrowser {{background:#ffffff;color:#20242a;border:0;font-family:"{self.family}";font-size:20px;}}')
        self.reader.document().setDocumentMargin(28)
        self.reader.document().setBaseUrl(QtCore.QUrl.fromLocalFile(str(self.root)+'/'))
        row.addWidget(self.reader,1)
        self.resize_timer=QtCore.QTimer(self);self.resize_timer.setSingleShot(True);self.resize_timer.setInterval(100);self.resize_timer.timeout.connect(self.refresh)
        self.reader.viewport().installEventFilter(self)
        self.font_size.valueChanged.connect(self.refresh)
        self.set_theme('dark')
        self.refresh()

    def set_theme(self,theme):
        if not hasattr(self,'_saved_fraction'):self.prepare_theme_change()
        self.theme=theme;dark=theme=='dark'
        bg='#191c21' if dark else '#ffffff';fg='#d9dde2' if dark else '#20242a'
        side='#1f2329' if dark else '#f3f4f6';muted='#b3bbc4' if dark else '#3a444e'
        selected='#2b3a48' if dark else '#dde8f2';border='#363c44' if dark else '#d5d9de'
        self.contents.setStyleSheet(f'QListWidget {{background:{side};color:{muted};border:0;font-size:13px;padding:10px;}} QListWidget::item {{padding:9px 4px;border-bottom:1px solid {border};}} QListWidget::item:selected {{background:{selected};color:{fg};}}')
        self.reader.setStyleSheet(f'QTextBrowser {{background:{bg};color:{fg};border:0;font-family:"{self.family}";font-size:20px;}}')
        self.refresh()

    def prepare_theme_change(self):
        bar=self.reader.verticalScrollBar()
        self._saved_fraction=bar.value()/max(bar.maximum(),1)

    def refresh(self,*_):
        from build_theory import build_html
        if not self.isVisible():return
        width=max(400,self.reader.viewport().width()-56)
        key=(self.font_size.value(),width,self.theme)
        if key==getattr(self,'_render_key',None):return
        self._render_key=key
        scroll=self.reader.verticalScrollBar();fraction=getattr(self,'_saved_fraction',scroll.value()/max(scroll.maximum(),1))
        if hasattr(self,'_saved_fraction'):del self._saved_fraction
        self.reader.setHtml(build_html(self.root,self.font_size.value(),content_width=width,embedded=True,theme=self.theme))
        self.reader.document().setBaseUrl(QtCore.QUrl.fromLocalFile(str(self.root)+'/'))
        # QTextDocument supports precise line spacing, unlike several HTML/CSS
        # features. Apply it to text paragraphs, preserving equation images.
        block=self.reader.document().begin()
        while block.isValid():
            cursor=QtGui.QTextCursor(block);fmt=cursor.blockFormat()
            it=block.begin();has_image=False
            while not it.atEnd():
                fragment=it.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():has_image=True
                it+=1
            # Inherited proportional body spacing also scales inline-image
            # line boxes in QTextDocument. Reset those explicitly: a 680 px
            # figure must not reserve a 1000 px line box and leave a huge gap.
            fmt.setLineHeight(100 if has_image else 132,QtGui.QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            if has_image:fmt.setTopMargin(6);fmt.setBottomMargin(8)
            cursor.setBlockFormat(fmt)
            block=block.next()
        self.reader.document().documentLayout().documentSize()
        scroll.setValue(round(fraction*scroll.maximum()))

    def navigate(self,item,previous=None):
        if item:
            self.reader.scrollToAnchor(item.data(QtCore.Qt.ItemDataRole.UserRole))
            bar=self.reader.verticalScrollBar();bar.setValue(max(0,bar.value()-40))

    def eventFilter(self,watched,event):
        if watched is self.reader.viewport() and event.type()==QtCore.QEvent.Type.Resize:
            self.resize_timer.start()
        return super().eventFilter(watched,event)

    def showEvent(self,event):
        super().showEvent(event)
        self.resize_timer.start()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'resize_timer'):self.resize_timer.start()

    def open_reading_copy(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.root/'THEORY.html')))
