"""Screen-only UFit-family palette. Publication plots keep their light style."""
from PySide6 import QtGui
from matplotlib.colors import to_hex,LinearSegmentedColormap
import branding as B
from display_format import ReadableScalarFormatter
from matplotlib.ticker import ScalarFormatter

DARK_STYLE='''
QWidget {background:#1f2329;color:#d9dde2;font-family:"Segoe UI";font-size:12px;}
QLabel#Title {font-size:19px;font-weight:600;color:#eef0f2;}
QLabel#Hint {color:#9aa3ad;}
QLabel#Badge {color:#9aa3ad;font-size:11px;}
QLabel#Status {background:#191c21;padding:7px;border:1px solid #3a4048;border-radius:2px;}
QLabel#Warnings {color:#e3bf7f;padding:3px;}
QPushButton {background:#2a2f36;border:1px solid #4a515b;border-radius:2px;padding:6px 11px;}
QPushButton:hover {background:#333941;border-color:#77808b;}
QPushButton:focus {border-color:#88b1d4;}
QPushButton:disabled {color:#6f7782;border-color:#3a4048;}
QPushButton#Primary {background:#2f5476;border:1px solid #88b1d4;color:#f4f6f8;font-weight:600;padding:8px 12px;}
QPushButton#Primary:hover {background:#3a6588;}
QPushButton#ArtifactToggle {background:#24282e;border:1px solid #4a515b;font-size:12px;font-weight:600;padding:7px;}
QPushButton#ArtifactToggle:checked {background:#2b3a48;border:1px solid #88b1d4;color:#f4f6f8;}
QPushButton#LookItem {background:transparent;border:1px solid transparent;text-align:left;padding:0;}
QPushButton#LookItem:hover {background:#2a2f36;border-color:#4a515b;}
QPushButton#LookItem:focus {border-color:#88b1d4;}
QFrame#TourPanel QLabel#TourMark {background:#88b1d4;color:#14181d;font-weight:700;font-size:11px;}
QFrame#TourPanel {background:#191c21;border:1px solid #4a515b;border-left:3px solid #88b1d4;}
QFrame#TourPanel QLabel {background:transparent;}
QLabel#TourStep {color:#9aa3ad;}
QLabel#TourTitle {font-size:16px;font-weight:600;color:#eef0f2;}
QLabel#TourHeading {font-weight:600;color:#eef0f2;margin-top:4px;}
QToolButton#Disclosure {border:none;text-align:left;padding:8px 4px;font-weight:600;color:#d0d5db;}
QToolButton#Disclosure:hover {color:#88b1d4;}
QWidget#Section {background:#191c21;border:1px solid #363c44;border-radius:2px;}
QWidget#SectionBody {border:none;background:#191c21;}
QDoubleSpinBox,QSpinBox,QComboBox {background:#272c33;border:1px solid #4a515b;border-radius:2px;padding:4px;}
QToolTip {color:#eef0f2;background:#2b3038;border:1px solid #77808b;padding:7px;}
QTabBar::tab {background:#24282e;padding:8px 12px;border-bottom:2px solid transparent;}
QTabBar::tab:selected {background:#2c323a;border-bottom:2px solid #88b1d4;}
QScrollArea {border:0;}
QScrollBar:vertical {background:#1b1e23;width:12px;margin:0;}
QScrollBar::handle:vertical {background:#4f5761;min-height:32px;border-radius:2px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QSplitter::handle {background:#363c44;width:5px;}
'''

LIGHT_STYLE=DARK_STYLE
for before,after in {
    '#1f2329':'#f3f4f6','#d9dde2':'#222a32','#eef0f2':'#111820','#9aa3ad':'#56606b',
    '#191c21':'#ffffff','#3a4048':'#c9ced4','#e3bf7f':'#8a4b12','#2a2f36':'#eceef1',
    '#4a515b':'#a3abb4','#333941':'#e2e5e9','#77808b':'#6b7580','#88b1d4':'#245f8f',
    '#6f7782':'#9aa2ab','#2f5476':'#245f8f','#f4f6f8':'#ffffff','#3a6588':'#1d4f78',
    '#24282e':'#eceef1','#2b3a48':'#dde8f2','#14181d':'#ffffff','#d0d5db':'#2a333c',
    '#363c44':'#cdd2d8','#272c33':'#ffffff','#2b3038':'#f7f8fa','#2c323a':'#ffffff',
    '#1b1e23':'#e6e9ec','#4f5761':'#9aa3ad',
}.items():LIGHT_STYLE=LIGHT_STYLE.replace(before,after)
# The checked source button keeps dark text in light mode.
LIGHT_STYLE=LIGHT_STYLE.replace('QPushButton#ArtifactToggle:checked {background:#dde8f2;border:1px solid #245f8f;color:#ffffff;}',
                                'QPushButton#ArtifactToggle:checked {background:#dde8f2;border:1px solid #245f8f;color:#111820;}')
STYLE=DARK_STYLE  # source compatibility; the default is dark.

def apply(app,theme='dark'):
    app.setStyleSheet(DARK_STYLE if theme=='dark' else LIGHT_STYLE)
    from PySide6.QtGui import QPalette,QColor
    dark=theme=='dark';palette=QPalette()
    for role,color in {
        QPalette.ColorRole.Window:'#1f2329' if dark else '#f3f4f6',
        QPalette.ColorRole.Base:'#191c21' if dark else '#ffffff',
        QPalette.ColorRole.AlternateBase:'#272c33' if dark else '#eceef1',
        QPalette.ColorRole.Text:'#d9dde2' if dark else '#222a32',
        QPalette.ColorRole.WindowText:'#d9dde2' if dark else '#222a32',
        QPalette.ColorRole.Button:'#2a2f36' if dark else '#eceef1',
        QPalette.ColorRole.ButtonText:'#d9dde2' if dark else '#222a32',
        QPalette.ColorRole.Highlight:'#3a6588' if dark else '#245f8f',
        QPalette.ColorRole.HighlightedText:'#ffffff',
        QPalette.ColorRole.Link:'#85c5ff' if dark else '#166277',
        QPalette.ColorRole.LinkVisited:'#c7a6ed' if dark else '#71508d',
    }.items():palette.setColor(role,QColor(color))
    app.setPalette(palette)

def accent(theme='dark'):
    """Interface accent and the text colour drawn on it."""
    return ('#88b1d4','#14181d') if theme=='dark' else ('#245f8f','#ffffff')


SCREEN_CMAP=LinearSegmentedColormap.from_list('FringeScope signed',[B.BLUE,B.PANEL,B.CORAL])


def style_figure(fig,theme='dark'):
    dark=theme=='dark'
    bg=B.BG if dark else '#f7f9fa';panel=B.PANEL if dark else '#ffffff'
    text=B.TEXT if dark else '#24323e';muted='#a4b0bb' if dark else '#526574'
    grid_color='#52606b' if dark else '#b6c6d0'
    compact=fig.bbox.width<1050
    mapping={'#278b72':B.GREEN,'#d65d3f':B.CORAL,'#268bd2':B.BLUE,'#df8a25':'#f2b24c',
             '#79627e':'#b8a0cf','#303945':'#b9c4ce','#808080':'#b9c4ce','#000000':'#8e9aa8',
             '#25836b':B.GREEN,'#28876a':B.GREEN,'#315c91':B.BLUE,'#337fba':B.BLUE,
             '#b74e3e':B.CORAL}
    if not dark:mapping={}
    fig.set_facecolor(bg)
    for item in fig.texts:item.set_color(text)
    axes=list(fig.axes)
    for ax in fig.axes:axes.extend(ax.child_axes)
    for ax in axes:
        for axis,scale in [(ax.xaxis,ax.get_xscale()),(ax.yaxis,ax.get_yscale())]:
            if scale=='linear' and isinstance(axis.get_major_formatter(),ScalarFormatter):
                axis.set_major_formatter(ReadableScalarFormatter())
        ax.set_facecolor(panel)
        ax.tick_params(colors=muted,which='both')
        for spine in ax.spines.values():spine.set_color(grid_color)
        for label in [ax.title,ax._left_title,ax._right_title,ax.xaxis.label,ax.yaxis.label,ax.xaxis.get_offset_text(),ax.yaxis.get_offset_text()]:label.set_color(text)
        if compact:
            for title in [ax.title,ax._left_title,ax._right_title]:title.set_fontsize(9)
            ax.xaxis.label.set_fontsize(8);ax.yaxis.label.set_fontsize(8);ax.tick_params(labelsize=7)
        for item in ax.texts:
            item.set_color(text)
            if item.get_bbox_patch() is not None:item.get_bbox_patch().set_facecolor(panel)
        for line in ax.lines:
            try:key=to_hex(line.get_color()).lower()
            except (ValueError,TypeError):continue
            if key in mapping:line.set_color(mapping[key])
        for item in ax.collections:
            if hasattr(item,'get_cmap') and item.get_array() is not None and item.get_array().size>8:
                item.set_cmap(SCREEN_CMAP if dark else 'RdBu_r')
        for item in ax.images:
            if item.get_cmap().name in ('RdBu_r','FringeScope signed'):item.set_cmap(SCREEN_CMAP if dark else 'RdBu_r')
        for grid in ax.get_xgridlines()+ax.get_ygridlines():grid.set_color(grid_color);grid.set_alpha(.20)
        legend=ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor(panel);legend.get_frame().set_edgecolor(grid_color)
            for item in legend.get_texts():
                item.set_color(text)
                if compact:item.set_fontsize(6.5)
            for line in legend.get_lines():
                key=to_hex(line.get_color()).lower()
                if key in mapping:line.set_color(mapping[key])
