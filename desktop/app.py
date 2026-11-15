"""FringeScope: simulated TRSS workspace and linked artifact exploration."""
if __name__=='__main__':
    from startup import main
    raise SystemExit(main())

import sys,json,traceback
from html import escape
from pathlib import Path
from dataclasses import fields
from datetime import datetime
import numpy as np
from PySide6 import QtWidgets as Q,QtCore,QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from ftir_sim import Settings,simulate,fit_das,ROOT,export_result
from theory_view import TheoryPage
from ui_help import SOURCES,TIPS
from display_format import number as display_number
import branding as B
import plots,ui_theme
import tour as TOUR


def tooltip(text):
    return '<qt><table width="420"><tr><td>'+escape(text)+'</td></tr></table></qt>'


class PreciseSpin(Q.QDoubleSpinBox):
    """Retain source precision while displaying at most two decimal places."""
    def textFromValue(self,value):return display_number(value)
    def valueFromText(self,text):
        try:return float(text.strip())
        except ValueError:return self.value()
    def validate(self,text,pos):
        if text.strip() in ('','-','+','.','-.','+.') or text.lower().endswith(('e','e-','e+')):
            return QtGui.QValidator.State.Intermediate,text,pos
        try:value=float(text)
        except ValueError:return QtGui.QValidator.State.Invalid,text,pos
        state=QtGui.QValidator.State.Acceptable if self.minimum()<=value<=self.maximum() else QtGui.QValidator.State.Intermediate
        return state,text,pos


class Section(Q.QWidget):
    def __init__(self,title,checkable=False,expanded=False):
        super().__init__();self.setObjectName('Section')
        outer=Q.QVBoxLayout(self);outer.setContentsMargins(7,0,7,4);outer.setSpacing(0)
        header=Q.QHBoxLayout();outer.addLayout(header)
        self.disclosure=Q.QToolButton();self.disclosure.setObjectName('Disclosure')
        self.disclosure.setText(title);self.disclosure.setCheckable(True)
        self.disclosure.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.disclosure.setSizePolicy(Q.QSizePolicy.Policy.Expanding,Q.QSizePolicy.Policy.Preferred)
        header.addWidget(self.disclosure,1)
        self.enable=Q.QCheckBox('On') if checkable else None
        if self.enable:header.addWidget(self.enable)
        self.body=Q.QWidget();self.body.setObjectName('SectionBody')
        self.form=Q.QFormLayout(self.body);self.form.setContentsMargins(3,5,3,10);self.form.setSpacing(8)
        self.form.setFieldGrowthPolicy(Q.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.form.setRowWrapPolicy(Q.QFormLayout.RowWrapPolicy.WrapLongRows)
        outer.addWidget(self.body);self.disclosure.toggled.connect(self.set_open)
        self.setSizePolicy(Q.QSizePolicy.Policy.Expanding,Q.QSizePolicy.Policy.Maximum)
        self.set_open(expanded)
    def set_open(self,on):
        self.disclosure.setChecked(on);self.body.setVisible(on)
        self.disclosure.setArrowType(QtCore.Qt.ArrowType.DownArrow if on else QtCore.Qt.ArrowType.RightArrow)
        self.body.updateGeometry();self.updateGeometry()


class PlotPage(Q.QWidget):
    def __init__(self):
        super().__init__();layout=Q.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.figure=Figure(figsize=(12,7));self.canvas=FigureCanvasQTAgg(self.figure)
        self.toolbar=NavigationToolbar2QT(self.canvas,self);layout.addWidget(self.toolbar)
        self.canvas.setMinimumSize(640,520)
        self.plot_scroll=Q.QScrollArea();self.plot_scroll.setWidgetResizable(True);self.plot_scroll.setFrameShape(Q.QFrame.Shape.NoFrame)
        self.plot_scroll.setMinimumSize(0,140);self.plot_scroll.setWidget(self.canvas);layout.addWidget(self.plot_scroll,1)
        self.handles=None;self.defaults=[]


class LookItem(Q.QPushButton):
    """A numbered, word-wrapped, keyboard-accessible tour target."""
    def __init__(self,number,text):
        super().__init__();self.setObjectName('LookItem');self.setAccessibleName(f'{number}. {text}')
        layout=Q.QHBoxLayout(self);layout.setContentsMargins(6,5,6,5);layout.setSpacing(8)
        mark=Q.QLabel(str(number));mark.setObjectName('TourMark');mark.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter);mark.setFixedSize(20,20)
        label=Q.QLabel(text);label.setWordWrap(True)
        for item in (mark,label):item.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(mark,0,QtCore.Qt.AlignmentFlag.AlignTop);layout.addWidget(label,1)
        self.setSizePolicy(Q.QSizePolicy.Policy.Expanding,Q.QSizePolicy.Policy.Preferred)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):return self.layout().heightForWidth(width)
    def sizeHint(self):return QtCore.QSize(260,self.layout().heightForWidth(260))
    def minimumSizeHint(self):return QtCore.QSize(120,30)


class TourPanel(Q.QFrame):
    """Left-hand panel shown instead of the controls while the guided tour runs."""
    def __init__(self):
        super().__init__();self.setObjectName('TourPanel')
        layout=Q.QVBoxLayout(self);layout.setContentsMargins(12,10,12,12);layout.setSpacing(8)
        head=Q.QHBoxLayout();self.step=Q.QLabel();self.step.setObjectName('TourStep');head.addWidget(self.step,1)
        self.end=Q.QPushButton('End tour');self.end.setToolTip('Leave the tour and restore your previous controls and selections.');head.addWidget(self.end)
        layout.addLayout(head)
        self.title=Q.QLabel();self.title.setObjectName('TourTitle');self.title.setWordWrap(True);layout.addWidget(self.title)
        self.changed=Q.QLabel();self.changed.setWordWrap(True);layout.addWidget(self.changed)
        heading=Q.QLabel('Where to look');heading.setObjectName('TourHeading');layout.addWidget(heading)
        note=Q.QLabel('The same numbers mark the plots and source buttons. Click an item to show and outline it.');note.setObjectName('Hint');note.setWordWrap(True);layout.addWidget(note)
        self.items=Q.QVBoxLayout();self.items.setSpacing(3);layout.addLayout(self.items)
        layout.addStretch(1)
        nav=Q.QHBoxLayout();self.back=Q.QPushButton('Back');self.next=Q.QPushButton('Next');self.next.setObjectName('Primary')
        nav.addWidget(self.back);nav.addWidget(self.next,1);layout.addLayout(nav)


class MainWindow(Q.QMainWindow):
    def __init__(self,startup_progress=None):
        super().__init__();self.setWindowTitle(f'{B.NAME} · v{B.VERSION}');self.setWindowIcon(B.icon())
        self.resize(1720,1040);self.setMinimumSize(1000,560)
        self.ready=False;self.theme='dark';self.controls={};self.sections={};self.artifact_buttons={};self.pages={}
        self.result=None;self.fit=None;self.dragging=False
        self.view_high=2*Settings().fold_width;self.view_low=Settings().fold_width
        self.timer=QtCore.QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.recompute)
        self.resize_timer=QtCore.QTimer(self);self.resize_timer.setSingleShot(True);self.resize_timer.setInterval(120)
        self.resize_timer.timeout.connect(lambda:self.draw())
        central=Q.QWidget();self.setCentralWidget(central);outer=Q.QVBoxLayout(central);outer.setSpacing(8)
        heading=Q.QHBoxLayout();outer.addLayout(heading)
        logo=Q.QLabel();logo.setPixmap(B.icon().pixmap(44,44));heading.addWidget(logo)
        brand=Q.QVBoxLayout();heading.addLayout(brand,1)
        title=Q.QLabel(B.NAME);title.setObjectName('Title');brand.addWidget(title)
        subtitle=Q.QLabel(B.SUBTITLE);subtitle.setObjectName('Hint');brand.addWidget(subtitle)
        badge=Q.QLabel('Simulated data');badge.setObjectName('Badge');heading.addWidget(badge)
        self.appearance=Q.QComboBox();self.appearance.addItem('Dark mode','dark');self.appearance.addItem('Light mode','light')
        self.appearance.setAccessibleName('Application appearance');self.appearance.setToolTip('Change the interface, plots, equations and theory figures together. Numerical data are unchanged. Dark mode is the startup default.')
        self.appearance.currentIndexChanged.connect(self.theme_changed);heading.addWidget(self.appearance)
        self.tour_step=-1;self.tour_saved=None;self.tour_focus=None
        self.tour_button=Q.QPushButton('Guided tour');self.tour_button.setToolTip('Four steps: ideal, mirror motion, globar leakage and 532 nm pickup. Ending the tour restores your controls and selections.')
        self.tour_button.clicked.connect(self.advance_tour);heading.addWidget(self.tour_button)
        from update_ui import Controller
        self.updates=Controller(self)
        check=Q.QPushButton('Check updates');check.clicked.connect(lambda:self.updates.check(manual=True));heading.addWidget(check)
        self.update_timer=QtCore.QTimer(self);self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(lambda:self.updates.check(manual=False));self.update_timer.start(2000)
        clear=Q.QPushButton('Reset to ideal');clear.clicked.connect(self.reset_ideal);heading.addWidget(clear);self.reset_button=clear
        export=Q.QPushButton('Export run');export.clicked.connect(self.export);heading.addWidget(export);self.export_button=export
        self.hint=Q.QLabel(self.DEFAULT_HINT);self.hint.setObjectName('Hint');outer.addWidget(self.hint)
        toggles=Q.QHBoxLayout();outer.addLayout(toggles)
        for key,(label,setting,tip) in SOURCES.items():
            button=Q.QPushButton(label+'\nOff');button.setCheckable(True);button.setObjectName('ArtifactToggle')
            button.setToolTip(tooltip(tip));button.setAccessibleName(label+' on/off')
            button.clicked.connect(lambda on,k=key:self.toggle_artifact(k,on))
            self.artifact_buttons[key]=button;toggles.addWidget(button,1)
        self.splitter=Q.QSplitter(QtCore.Qt.Orientation.Horizontal);outer.addWidget(self.splitter,1)
        self.scroll=Q.QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setMinimumWidth(290)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_widget=Q.QWidget();self.side=Q.QVBoxLayout(side_widget);self.side.setContentsMargins(0,0,7,0);self.side.setSpacing(7)
        self.side.setSizeConstraint(Q.QLayout.SizeConstraint.SetMinAndMaxSize)
        self.scroll.setWidget(side_widget)
        self.tour_panel=TourPanel();self.tour_scroll=Q.QScrollArea();self.tour_scroll.setWidgetResizable(True);self.tour_scroll.setWidget(self.tour_panel)
        self.tour_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tour_panel.next.clicked.connect(lambda:self.goto_tour_step(self.tour_step+1))
        self.tour_panel.back.clicked.connect(lambda:self.goto_tour_step(self.tour_step-1))
        self.tour_panel.end.clicked.connect(lambda:self.end_tour(False))
        self.left=Q.QStackedWidget();self.left.addWidget(self.scroll);self.left.addWidget(self.tour_scroll);self.left.setMinimumWidth(290)
        self.splitter.addWidget(self.left)
        self.build_controls();self.side.addStretch()
        right_widget=Q.QWidget();right=Q.QVBoxLayout(right_widget);right.setContentsMargins(0,0,0,0);right.setSpacing(7)
        self.splitter.addWidget(right_widget);self.splitter.setSizes([350,1350]);self.splitter.setStretchFactor(1,1)
        self.status=Q.QLabel();self.status.setObjectName('Status');self.status.setWordWrap(True);self.status.setMinimumHeight(60);right.addWidget(self.status)
        selection=Q.QHBoxLayout();self.selection_row=selection;right.addLayout(selection)
        selection.addWidget(Q.QLabel('Kinetics (cm⁻¹)'))
        self.wn=self.number(1697,self.view_low,self.view_high,1);self.wn.setMaximumWidth(125)
        self.wn.setToolTip('Select the nearest native wavenumber channel. Clicking or dragging the contour updates both selections; the crosshair reports the actual channel.');self.wn.valueChanged.connect(self.selection_changed);selection.addWidget(self.wn)
        selection.addWidget(Q.QLabel('Spectrum (µs)'))
        self.time=self.number(100,-153,3381,6);self.time.setMaximumWidth(115)
        self.time.setToolTip('Numeric times may be between bins and are linearly interpolated. Contour clicks and the slider snap to native 6 µs bin centers.');self.time.valueChanged.connect(self.selection_changed);selection.addWidget(self.time)
        self.slider=Q.QSlider(QtCore.Qt.Orientation.Horizontal);self.slider.setRange(0,589);self.slider.valueChanged.connect(self.slider_changed);selection.addWidget(self.slider,1)
        home=Q.QPushButton('Reset view');home.setToolTip('Restore the full spectral/time view without changing selected sources, parameters or data selections.');home.clicked.connect(lambda:self.draw(preserve=False));selection.addWidget(home)
        self.selection_label=Q.QLabel();self.selection_label.setObjectName('Hint');right.addWidget(self.selection_label)
        self.tabs=Q.QTabWidget();right.addWidget(self.tabs,1)
        for name in ['Explore','Compare','DAS and offset','Optical contributions','Diagnostics','Demonstrations']:
            page=PlotPage();self.pages[name]=page;self.tabs.addTab(page,name)
            page.canvas.mpl_connect('resize_event',lambda event:self.resize_timer.start() if self.ready else None)
        diagnostic_bar=Q.QHBoxLayout()
        self.diagnostic=Q.QComboBox()
        for name in ['Interferograms','Mirror waveform','Sampling and pulse guide']:self.diagnostic.addItem(name)
        self.diagnostic.setToolTip('The sampling map depends on wavelength and OPD grid. The normalized pulse guide depends on pulse/response shape, not leakage strength. Applied amplitudes are in Optical contributions.')
        diagnostic_bar.addWidget(Q.QLabel('Diagnostic view'));diagnostic_bar.addWidget(self.diagnostic,1)
        self.pages['Diagnostics'].layout().insertLayout(0,diagnostic_bar)
        self.diagnostic.currentIndexChanged.connect(lambda:self.draw())
        from demo_plots import VIEWS
        self.demo_data=None;self.demo=Q.QComboBox();self.demo.addItems(VIEWS)
        self.demo.setToolTip(tooltip('Original Rödig-inspired simulations with fixed, explicitly stated acquisitions. These lessons are independent of the workspace artifact toggles. No experimental arrays are used.'))
        lesson=Q.QHBoxLayout();lesson.addWidget(Q.QLabel('Scientific demonstration'));lesson.addWidget(self.demo,1)
        self.pages['Demonstrations'].layout().insertLayout(0,lesson)
        demo_hint=Q.QLabel('Fixed illustrative acquisitions · independent of workspace toggles · settings and assumptions are stated in each figure.');demo_hint.setObjectName('Hint');demo_hint.setWordWrap(True)
        self.pages['Demonstrations'].layout().insertWidget(1,demo_hint)
        self.demo.currentIndexChanged.connect(lambda:self.draw(preserve=False))
        self.theory_page=TheoryPage(ROOT);self.tabs.addTab(self.theory_page,'Theory and evidence')
        self.tabs.currentChanged.connect(self.tab_changed)
        self.warning=Q.QLabel();self.warning.setObjectName('Warnings');self.warning.setWordWrap(True);self.warning.setMinimumHeight(40);right.addWidget(self.warning)
        canvas=self.pages['Explore'].canvas
        canvas.setToolTip('Left-click or drag the contour to select time and wavenumber. Spectrum/DAS clicks select wavenumber; kinetics clicks select time. Disable toolbar pan/zoom to select.')
        canvas.mpl_connect('button_press_event',self.plot_press)
        canvas.mpl_connect('motion_notify_event',self.plot_motion)
        canvas.mpl_connect('button_release_event',lambda event:setattr(self,'dragging',False))
        self.ready=True
        area=self.screen().availableGeometry()
        self.resize(min(1720,max(self.minimumWidth(),area.width()-24)),min(1040,max(self.minimumHeight(),area.height()-60)))
        if startup_progress:startup_progress(2)
        self.recompute()

    def closeEvent(self,event):
        self.update_timer.stop();self.timer.stop();self.resize_timer.stop();self.updates.stop()
        super().closeEvent(event)

    def number(self,value,lo,hi,step=1):
        widget=PreciseSpin();widget.setDecimals(12);widget.setRange(lo,hi);widget.setSingleStep(step);widget.setValue(value)
        widget.setMinimumWidth(112);widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        return widget

    def section(self,title,key=None,parent=None,expanded=False):
        box=Section(title,key is not None,expanded)
        if parent is None:self.side.addWidget(box)
        else:parent.addRow(box)
        if key:
            self.controls[key]=box.enable;self.sections[key]=box
            box.enable.setToolTip(tooltip(TIPS.get(key,title)))
            box.disclosure.setToolTip(tooltip(TIPS.get(key,title)))
            box.enable.toggled.connect(lambda on,k=key:self.source_toggled(k,on))
        return box

    def spin(self,form,label,key,value,lo,hi,step=1):
        if key in ('coadds','mains_harmonic'):
            widget=Q.QSpinBox();widget.setRange(int(lo),int(hi));widget.setSingleStep(int(step));widget.setValue(int(value))
        else:widget=self.number(value,lo,hi,step)
        widget.setToolTip(tooltip(TIPS.get(key,label)))
        form.addRow(label,widget);form.labelForField(widget).setWordWrap(True)
        self.controls[key]=widget;widget.valueChanged.connect(self.schedule)
        return widget

    def combo(self,form,label,key,items):
        widget=Q.QComboBox();widget.setMinimumContentsLength(12)
        widget.setSizeAdjustPolicy(Q.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        for value,text in items:
            widget.addItem(text,value)
            widget.setItemData(widget.count()-1,tooltip(text+' — '+TIPS.get(key,label)),QtCore.Qt.ItemDataRole.ToolTipRole)
        widget.setToolTip(tooltip(TIPS.get(key,label)));form.addRow(label,widget);form.labelForField(widget).setWordWrap(True)
        self.controls[key]=widget;widget.currentIndexChanged.connect(self.schedule)
        return widget

    def build_controls(self):
        p=Settings()
        for source,(label,setting,tip) in SOURCES.items():
            box=self.section(label,setting);box.disclosure.setToolTip(tooltip(tip));box.enable.setToolTip(tooltip(tip))
            f=box.form
            if source=='mirror':
                self.spin(f,'Amplitude (nm)','mirror_nm',p.mirror_nm,0,20,.25)
                self.spin(f,'Frequency (Hz)','frequency_hz',p.frequency_hz,10,10000,5)
                self.spin(f,'Temporal phase (°)','phase_deg',p.phase_deg,-180,180,5)
                self.spin(f,'Common bias (nm)','bias_nm',25,-50,50,1)
                self.combo(f,'Motion waveform','waveform',[('sine','Biased sinusoid'),('harmonic2','Composite: f + 2f'),('harmonic3','Composite: f + 2f + 3f'),('servo','Composite: servo-like'),('envelope','Composite: envelope')])
                detail=self.section('Detailed motion settings',parent=f)
                for label,key,lo,hi,step in [('2f / fundamental','second_ratio',0,1,.02),('2f phase (°)','second_phase_deg',-180,180,5),('3f / fundamental','third_ratio',0,1,.02),('3f phase (°)','third_phase_deg',-180,180,5),('Frequency drift (Hz/ms)','chirp_hz_per_ms',-150,150,5),('Envelope slope','envelope_slope',-3,3,.1),('Quadrature slope','quadrature_slope',-3,3,.1),('Servo-step fraction','servo_fraction',0,1,.05)]:
                    self.spin(detail.form,label,key,.15 if key=='servo_fraction' else getattr(p,key),lo,hi,step)
                self.combo(detail.form,'Step/shot phase','phase_mode',[('locked','Trigger locked'),('random','Random step/shot'),('free','Free running')])
                for label,key,lo,hi,step in [('Coadds per step','coadds',1,100,1),('Repetition (Hz)','repetition_hz',1,50,1),('Settling (ms)','settle_ms',0,1000,1)]:self.spin(detail.form,label,key,getattr(p,key),lo,hi,step)
            elif source=='globar':
                self.spin(f,'Folded leak scale','globar_fraction',p.globar_fraction,0,10,.05)
                self.spin(f,'Blocking (OD)','blocking_od',0,0,10,.5)
                detail=self.section('Filter / transient assumptions',parent=f)
                self.spin(detail.form,'Leak center (cm⁻¹)','leak_center',p.leak_center,100,9000,100)
                self.spin(detail.form,'Leak σ (cm⁻¹)','leak_width',p.leak_width,10,3000,50)
                self.spin(detail.form,'Changing leak (ppm)','leak_transient_ppm',0,-10000,10000,100)
            elif source=='laser':
                self.spin(f,'Pulse area / IFG (µs)','laser_area_us',.00002,0,.1,.00001)
                self.spin(f,'Blocking (OD)','laser_blocking_od',0,0,12,.5)
                detail=self.section('Pulse and optical path',parent=f)
                self.combo(detail.form,'Optical path','laser_route',[('interferometric','OPD-modulated return'),('bypass_uniform','Uniform direct bypass'),('bypass_scatter','Step-dependent bypass')])
                for label,key,value,lo,hi,step in [('Optical FWHM (ns)','pulse_fwhm_ns',6,.1,200,1),('Reflection tail (ns)','reflection_ns',20,0,300,5),('Electronics τ (µs)','response_us',.15,0,100,.1),('Pulse delay (µs)','laser_delay_us',0,-20,100,.01)]:self.spin(detail.form,label,key,value,lo,hi,step)
        model=self.section('Chemical model and fitting')
        self.spin(model.form,'Fast heating τ (µs)','heat_tau',p.heat_tau,.5,100,1)
        self.spin(model.form,'Recombination τ (µs)','rp_tau',p.rp_tau,25,10000,10)
        for label,key in [('Fast heating amplitude ×','heat_scale'),('Decaying PSI amplitude ×','rp_scale'),('Unresolved offset ×','offset_scale')]:self.spin(model.form,label,key,1,0,5,.1)
        for label,key,value,lo,hi,step in [('Fit from (µs)','fit_start',0,0,3300,6),('Fit to (µs)','fit_stop',3378,50,3381,60),('Fit low (cm⁻¹)','fit_low',1200,self.view_low,self.view_high,10),('Fit high (cm⁻¹)','fit_high',1900,self.view_low,self.view_high,10)]:self.spin(model.form,label,key,value,lo,hi,step)
        self.offset=Q.QCheckBox('Fit non-decaying offset');self.offset.setChecked(True);self.offset.setToolTip('Include a constant spectral-amplitude basis in the fit. This does not remove the input offset; use Unresolved offset × to change the simulated signal.');model.form.addRow(self.offset);self.offset.toggled.connect(self.schedule)
        refit=Q.QPushButton('Refit the two lifetimes');refit.setToolTip('Unweighted variable projection with signed amplitudes and beta = 1. Fit convergence does not establish a physical assignment or uncertainty.');refit.clicked.connect(self.refit);model.form.addRow(refit)
        self.advanced=self.section('Advanced effects / readout')
        electrical=self.section('Electrical pickup','electrical',parent=self.advanced.form)
        self.combo(electrical.form,'Frequency source','electrical_mode',[('mains','60 Hz harmonic'),('free','Free frequency')])
        self.spin(electrical.form,'Mains harmonic n','mains_harmonic',14,1,100,1)
        self.spin(electrical.form,'Free frequency (Hz)','electrical_frequency',840,10,100000,10)
        self.spin(electrical.form,'Pickup / IFG peak','electrical_fraction',p.electrical_fraction,0,.05,.0001)
        self.spin(electrical.form,'Temporal phase (°)','electrical_phase_deg',0,-180,180,5)
        def electrical_fields():
            mains=self.controls['electrical_mode'].currentData()=='mains'
            for key,visible in [('mains_harmonic',mains),('electrical_frequency',not mains)]:
                widget=self.controls[key];widget.setVisible(visible);electrical.form.labelForField(widget).setVisible(visible)
        self.controls['electrical_mode'].currentIndexChanged.connect(electrical_fields);electrical_fields()
        registration=self.section('Return-position mismatch','zpd',parent=self.advanced.form)
        self.spin(registration.form,'Return offset (nm)','return_nm',2,-20,20,.5)
        self.spin(registration.form,'Step jitter SD (nm)','jitter_nm',1,0,20,.25)
        self.combo(self.advanced.form,'Phase readout','phase_readout',[('real','Fixed-phase real'),('magnitude','Magnitude comparison')])

    def value(self,widget):
        if isinstance(widget,Q.QComboBox):return widget.currentData()
        if isinstance(widget,Q.QCheckBox):return widget.isChecked()
        return widget.value()

    def set_control(self,key,value):
        widget=self.controls[key]
        if isinstance(widget,Q.QComboBox):widget.setCurrentIndex(widget.findData(value))
        elif isinstance(widget,Q.QCheckBox):widget.setChecked(bool(value))
        else:widget.setValue(value)

    def settings(self):
        valid={item.name for item in fields(Settings)}
        args={key:self.value(widget) for key,widget in self.controls.items() if key in valid}
        args.update(source='model',enabled=True,hene=False);args['coadds']=int(args['coadds'])
        if not args['wobble']:args['bias_nm']=0.
        if self.controls['electrical_mode'].currentData()=='mains':args['electrical_frequency']=60*int(self.controls['mains_harmonic'].value())
        return Settings(**args)

    def source_toggled(self,key,on):
        if key in self.sections:self.sections[key].set_open(on)
        if self.ready and on:QtCore.QTimer.singleShot(0,lambda:self.scroll.ensureWidgetVisible(self.sections[key],0,12))
        self.sync_artifact_buttons();self.schedule()

    def sync_artifact_buttons(self):
        for key,(label,setting,tip) in SOURCES.items():
            if setting not in self.controls:continue
            on=self.controls[setting].isChecked();button=self.artifact_buttons[key]
            mark=''
            if self.tour_step>=0:
                look=[t for t,_ in TOUR.STEPS[self.tour_step]['look']]
                if 'source:'+setting in look:mark=f'   [{look.index("source:"+setting)+1}]'
            blocker=QtCore.QSignalBlocker(button);button.setChecked(on);button.setText(label+mark+('\nOn' if on else '\nOff'));del blocker

    def toggle_artifact(self,key,on):
        self.set_control(SOURCES[key][1],on)
        self.timer.stop();self.recompute()

    def reset_ideal(self):
        for key in ['wobble','globar','laser','electrical','zpd']:self.set_control(key,False)
        QtCore.QTimer.singleShot(0,lambda:self.scroll.verticalScrollBar().setValue(0))
        self.timer.stop();self.recompute()

    DEFAULT_HINT='Switch a source on below. Click or drag the contour to choose a spectrum and kinetic trace. New users can start with the guided tour.'

    def advance_tour(self):
        """Toolbar button: start the tour, or end it and restore the workspace."""
        if self.tour_step<0:self.goto_tour_step(0)
        else:self.end_tour(False)

    def goto_tour_step(self,k):
        if k<0:return
        if k>=len(TOUR.STEPS):return self.end_tour(True)
        if self.tour_step<0:
            self.tour_analysis=(self.p,self.result,self.fit)
            self.tour_saved=({key:self.value(widget) for key,widget in self.controls.items()},self.wn.value(),self.time.value(),self.offset.isChecked(),self.tabs.currentIndex())
        self.tour_step=k;self.tour_focus=None;step=TOUR.STEPS[k]
        defaults=Settings()
        for key in self.controls:
            if hasattr(defaults,key):self.set_control(key,getattr(defaults,key))
        for key,value in TOUR.step_controls(k).items():
            if key=='offset':self.offset.setChecked(value)
            else:self.set_control(key,value)
        self.wn.setValue(TOUR.WAVENUMBER);self.time.setValue(step['time_us'])
        self.timer.stop();self.tabs.setCurrentWidget(self.pages['Explore']);self.show_tour_panel();self.recompute()
        if step['alias']:self.wn.setValue(self.result['laser_alias_cm1'])
        self.tour_panel.next.setFocus()

    def show_tour_panel(self):
        panel=self.tour_panel;step=TOUR.STEPS[self.tour_step];n=len(TOUR.STEPS)
        panel.step.setText(f'Guided tour · step {self.tour_step+1} of {n}')
        panel.title.setText(step['title']);panel.changed.setText('<b>What changed.</b> '+escape(step['changed']))
        while panel.items.count():
            item=panel.items.takeAt(0)
            if item.widget():item.widget().deleteLater()
        for number,(target,text) in enumerate(step['look'],1):
            button=LookItem(number,text);button.clicked.connect(lambda _=False,t=target:self.focus_tour_target(t));panel.items.addWidget(button)
        panel.back.setEnabled(self.tour_step>0);panel.next.setText(step['next']+'  →')
        self.left.setCurrentWidget(self.tour_scroll);self.tour_button.setText('End tour')
        self.hint.setText(f'Guided tour, step {self.tour_step+1} of {n}: read the panel on the left, look at the numbered plots, then press “{step["next"]}”.')
        self.sync_artifact_buttons()

    def focus_tour_target(self,target):
        if target.startswith('source:'):
            key=next((k for k,(label,setting,tip) in SOURCES.items() if setting==target[7:]),None)
            if key:self.artifact_buttons[key].setFocus()
            return
        self.tour_focus=target
        page=self.pages['Optical contributions' if target[:1]=='o' and target[1:].isdigit() else 'Explore']
        if self.tabs.currentWidget()!=page:self.tabs.setCurrentWidget(page)
        else:self.draw()

    def tour_axes(self,page,name,target):
        if name=='Explore' and page.handles and target in page.handles['axes']:return page.handles['axes'][target]
        if name=='Optical contributions' and target[:1]=='o' and target[1:].isdigit():
            axes=page.figure.axes;index=int(target[1:])
            return axes[index] if index<len(axes) else None
        return None

    def draw_tour_marks(self,page,name):
        if self.tour_step<0:return
        accent,ink=ui_theme.accent(self.theme)
        for number,(target,text) in enumerate(TOUR.STEPS[self.tour_step]['look'],1):
            ax=self.tour_axes(page,name,target)
            if ax is None:continue
            ax.text(1,1.015,str(number),transform=ax.transAxes,ha='right',va='bottom',fontsize=9,fontweight='bold',color=ink,
                    bbox=dict(boxstyle='square,pad=0.3',fc=accent,ec='none'),zorder=20,clip_on=False)
            if target==self.tour_focus:
                for spine in ax.spines.values():spine.set_color(accent);spine.set_linewidth(2.2)

    def end_tour(self,completed=True):
        if self.tour_step<0 or self.tour_saved is None:return
        values,wn,time,offset,tab=self.tour_saved
        for key,value in values.items():self.set_control(key,value)
        self.wn.setValue(wn);self.time.setValue(time);self.offset.setChecked(offset)
        self.tour_step=-1;self.tour_saved=None;self.tour_focus=None;self.tour_button.setText('Guided tour')
        self.left.setCurrentWidget(self.scroll)
        self.hint.setText(('Tour finished. ' if completed else 'Tour ended. ')+'Your previous controls, selections and exact fit are restored. The Demonstrations tab has fixed lessons on harmonics and coaddition.')
        self.timer.stop();self.p,self.result,self.fit=self.tour_analysis;self.tour_analysis=None
        self.tabs.setCurrentIndex(tab);self.draw();self.tour_button.setFocus()

    def schedule(self,*_):
        if not self.ready:return
        self.sync_artifact_buttons();self.timer.start()

    def tab_changed(self,*_):
        reading=self.tabs.currentWidget()==self.theory_page
        demonstration=self.tabs.currentWidget()==self.pages['Demonstrations'];focused=reading or demonstration
        self.left.setVisible(not focused);self.status.setVisible(not focused)
        self.selection_label.setVisible(not focused);self.warning.setVisible(not focused);self.hint.setVisible(not focused)
        self.reset_button.setVisible(not focused);self.export_button.setVisible(not reading)
        self.export_button.setText('Export demonstrations' if demonstration else 'Export run')
        for button in self.artifact_buttons.values():button.setVisible(not focused)
        for index in range(self.selection_row.count()):
            widget=self.selection_row.itemAt(index).widget()
            if widget:widget.setVisible(not focused)
        self.draw()

    def theme_changed(self,*_):
        self.theme=self.appearance.currentData()
        if hasattr(self,'theory_page'):self.theory_page.prepare_theme_change()
        ui_theme.apply(Q.QApplication.instance(),self.theme)
        if hasattr(self,'theory_page'):self.theory_page.set_theme(self.theme)
        if self.ready:self.draw()

    def recompute(self):
        if not self.ready:return
        self.timer.stop();self.sync_artifact_buttons()
        try:
            self.p=self.settings();self.result=simulate(self.p)
            self.fit=fit_das(self.result,self.p,False,self.controls['fit_start'].value(),self.controls['fit_stop'].value(),self.controls['fit_low'].value(),self.controls['fit_high'].value(),self.offset.isChecked())
            self.draw()
        except Exception as error:self.warning.setText(f'Configuration error: {error}');traceback.print_exc()

    def refit(self):
        try:
            self.fit=fit_das(self.result,self.p,True,self.controls['fit_start'].value(),self.controls['fit_stop'].value(),self.controls['fit_low'].value(),self.controls['fit_high'].value(),self.offset.isChecked());self.draw()
        except Exception as error:self.warning.setText(str(error))

    def _render(self,fig,name):
        r,p,f=self.result,self.p,self.fit;j=np.argmin(abs(r['t_us']-self.time.value()))
        if name=='Explore':return plots.overview(fig,r,p,f,j,self.wn.value(),time_us=self.time.value())
        if name=='Compare':plots.contours(fig,r)
        elif name=='DAS and offset':plots.das_detail(fig,r,f)
        elif name=='Optical contributions':plots.optical_contributions(fig,r,p,self.time.value(),self.wn.value())
        elif name=='Demonstrations':
            from demo_model import build_demonstrations
            from demo_plots import draw
            if self.demo_data is None:self.demo_data=build_demonstrations()
            draw(fig,self.demo_data,self.demo.currentIndex())
        elif name=='Diagnostics':
            mode=self.diagnostic.currentText()
            if mode=='Interferograms':plots.interferograms(fig,r,j)
            elif mode=='Mirror waveform':plots.waveform_view(fig,r,p,self.wn.value())
            else:plots.optics(fig,r,p)

    def draw(self,*_,preserve=True):
        if self.result is None:return
        active=[label for label,key,tip in SOURCES.values() if getattr(self.p,key)]
        active+=['Electrical pickup'] if self.p.electrical else []
        active+=['Return mismatch'] if self.p.zpd else []
        self.status.setText(('Active: '+', '.join(active) if active else 'Ideal simulated signal · all artifact sources off')+
            f'   |   Artifact RMS: {display_number(self.result["artifact_rms_full_OD"]*1e6)} µOD (full band)\n'+
            f'2 exponentials + {"offset" if self.offset.isChecked() else "no offset"} · τ = {display_number(self.fit["taus"][0])}, {display_number(self.fit["taus"][1])} µs · fit RMS = {display_number(self.fit["rms"]*1e6)} µOD')
        self.warning.setText(' '.join(self.result['warnings']+self.fit.get('notes',[])))
        self.update_selection_label()
        name=self.tabs.tabText(self.tabs.currentIndex())
        if name not in self.pages:return
        page=self.pages[name];saved=[]
        if preserve and page.defaults:
            for ax,(default_x,default_y) in zip(page.figure.axes,page.defaults):
                x,y=ax.get_xlim(),ax.get_ylim()
                saved.append((x if not np.allclose(x,default_x) else None,y if not np.allclose(y,default_y) else None))
        try:
            page.handles=self._render(page.figure,name);ui_theme.style_figure(page.figure,self.theme);self.draw_tour_marks(page,name)
            page.defaults=[(ax.get_xlim(),ax.get_ylim()) for ax in page.figure.axes]
            page.toolbar.update();page.toolbar.push_current()
            if len(saved)==len(page.figure.axes):
                for ax,(x,y) in zip(page.figure.axes,saved):
                    if x is not None:ax.set_xlim(x)
                    if y is not None:ax.set_ylim(y)
                if any(x is not None or y is not None for x,y in saved):page.toolbar.push_current()
            page.canvas.draw_idle()
        except Exception as error:self.warning.setText(str(error));traceback.print_exc()

    def update_selection_label(self):
        if self.result is None:return
        r=self.result;j=np.argmin(abs(r['nu']-self.wn.value()));index=np.argmin(abs(r['t_us']-self.time.value()))
        blocker=QtCore.QSignalBlocker(self.slider);self.slider.setValue(int(index));del blocker
        native=abs(r['t_us'][index]-self.time.value())<1e-8
        self.selection_label.setText(f'Selected: {display_number(r["nu"][j])} cm⁻¹ · {display_number(self.time.value())} µs'+(' · native time bin' if native else ' · linear time interpolation')+f'     |     Full band {display_number(self.view_high)}–{display_number(self.view_low)} cm⁻¹')

    def selection_changed(self,*_):
        if self.result is None:return
        self.update_selection_label()
        page=self.pages['Explore']
        if self.tabs.currentWidget()==page and page.handles:
            auto=[]
            for key in ['spectrum','kinetics']:
                ax=page.handles['axes'][key];index=page.figure.axes.index(ax)
                auto.append((ax,index,np.allclose(ax.get_ylim(),page.defaults[index][1])))
            plots.update_overview(page.handles,self.result,self.fit,self.wn.value(),self.time.value())
            for ax,index,allowed in auto:
                if allowed:
                    ax.relim();ax.autoscale_view(scalex=False,scaley=True)
                    page.defaults[index]=(page.defaults[index][0],ax.get_ylim())
            page.canvas.draw_idle()
        else:self.draw()

    def slider_changed(self,index):
        if self.result is not None:self.time.setValue(float(self.result['t_us'][index]))

    def _select_event(self,event):
        page=self.pages['Explore'];handles=page.handles
        if not handles or page.toolbar.mode:return
        axis=event.inaxes
        if axis not in handles['axes'].values():return
        wn=None;time=None
        if axis==handles['axes']['contour']:wn=event.xdata;time=event.ydata
        elif axis in [handles['axes']['spectrum'],handles['axes']['das']]:wn=event.xdata
        elif axis==handles['axes']['kinetics']:time=event.xdata
        if wn is not None:
            j=np.argmin(abs(self.result['nu']-wn));blocker=QtCore.QSignalBlocker(self.wn);self.wn.setValue(float(self.result['nu'][j]));del blocker
        if time is not None:
            j=np.argmin(abs(self.result['t_us']-time));blocker=QtCore.QSignalBlocker(self.time);self.time.setValue(float(self.result['t_us'][j]));del blocker
        self.selection_changed()

    def plot_press(self,event):
        if event.button==1 and not self.pages['Explore'].toolbar.mode:
            self.dragging=True;self._select_event(event)
    def plot_motion(self,event):
        if self.dragging:self._select_event(event)

    def export(self):
        from runtime_paths import export_parent
        base=Q.QFileDialog.getExistingDirectory(self,'Parent folder for a new FringeScope run',str(export_parent()))
        if not base:return
        try:
            if self.tabs.currentWidget()==self.pages['Demonstrations']:
                from build_demos import export_demonstrations
                dest=export_demonstrations(Path(base)/('FringeScope_demonstrations_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')),self.demo_data)
                self.pages['Demonstrations'].figure.savefig(dest/f'selected_screen_{self.theme}.png',dpi=170)
                (dest/'view_settings.json').write_text(json.dumps({'selected_demonstration':self.demo.currentText(),'application_version':B.VERSION,'appearance':self.theme,'scope':'Fixed demonstrations; workspace simulation settings do not apply.'},indent=2),encoding='utf-8')
                self.statusBar().showMessage(f'Saved new local demonstrations: {dest}',15000)
                return
            dest=export_result(self.result,Path(base)/('FringeScope_run_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')))
            name=self.tabs.tabText(self.tabs.currentIndex())
            if name in self.pages:
                self.pages[name].figure.savefig(dest/f'screen_{self.theme}.png',dpi=170)
                light=Figure(figsize=(12,7));self._render(light,name);light.savefig(dest/'figure_publication.png',dpi=180,facecolor='white')
            np.savetxt(dest/'DAS_and_offset.csv',np.column_stack([self.result['nu'],self.fit['das'].T]),delimiter=',',header='wavenumber_cm-1,heating_OD,recombination_OD'+(',offset_OD' if len(self.fit['das'])>2 else ''))
            metadata={key:value for key,value in self.fit.items() if not isinstance(value,np.ndarray)}
            j=np.argmin(abs(self.result['nu']-self.wn.value()))
            metadata.update(taus_us=self.fit['taus'].tolist(),selected_time_us=self.time.value(),requested_wavenumber_cm1=self.wn.value(),actual_wavenumber_cm1=float(self.result['nu'][j]),
                selection_processing='Contour/slider snap to native bins. Numeric off-grid times use linear interpolation.',electrical_frequency_mode=self.controls['electrical_mode'].currentData(),
                mains_harmonic=int(self.controls['mains_harmonic'].value()),application_version=B.VERSION,appearance=self.theme)
            if name in self.pages:
                metadata['screen_axes_limits']=[{'x':[float(v) for v in ax.get_xlim()],'y':[float(v) for v in ax.get_ylim()],
                    'xlabel':ax.get_xlabel(),'ylabel':ax.get_ylabel()} for ax in self.pages[name].figure.axes]
                metadata['publication_figure_view']='Full model band in the original light palette; selected time and wavenumber retained.'
            (dest/'analysis_settings.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
            for name in ['THEORY.md','REFERENCES.bib','synthetic_model.json','MODEL_ASSUMPTIONS.md']:(dest/name).write_bytes((ROOT/name).read_bytes())
            self.statusBar().showMessage(f'Saved new local run: {dest}',15000)
        except Exception as error:self.warning.setText(f'Export failed: {error}');traceback.print_exc()


def configure_app(app):
    import matplotlib
    folder=Path(matplotlib.get_data_path())/'fonts/ttf'
    for name in ['DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSerif.ttf','DejaVuSerif-Bold.ttf','DejaVuSerif-Italic.ttf']:QtGui.QFontDatabase.addApplicationFont(str(folder/name))
    app.setStyle('Fusion');app.setFont(QtGui.QFont(B.FONT,9));ui_theme.apply(app,'dark')


def main():
    from startup import main as start
    return start()
