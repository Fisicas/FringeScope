"""Original selected C-direction artwork. Generates editable SVG and PNG/ICO."""
from pathlib import Path
import os, math, json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets as Q, QtCore, QtGui, QtSvg
from PIL import Image
import branding as B


def path(points,color,width=4,opacity=1):
    d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}" stroke-linecap="round" stroke-linejoin="round"/>'


def mark(small=False):
    s=f'<rect x="2" y="2" width="124" height="124" rx="29" fill="{B.PANEL}" stroke="{B.LINE}" stroke-width="3"/>'
    s+=f'<circle cx="60" cy="58" r="35" fill="none" stroke="{B.BLUE}" stroke-width="{8 if small else 5}"/>'
    s+=path([(85,85),(108,108)],B.AMBER,10 if small else 7)
    s+=path([(29+62*i/120,59-16*math.sin(2*math.pi*i/120)) for i in range(121)],B.GREEN,7 if small else 4)
    if not small:
        s+=path([(60,18),(60,29)],B.MUTED,3)
        s+=path([(60,87),(60,98)],B.MUTED,3)
        s+=f'<circle cx="60" cy="59" r="4" fill="{B.AMBER}"/>'
    return s


def text(x,y,value,size=20,color=B.TEXT,weight=400):
    import html
    return f'<text x="{x}" y="{y}" font-family="{B.FONT}" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(value)}</text>'


def svg(body,w,h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><title>{B.NAME}: {B.SUBTITLE}</title>{body}</svg>'


def card(social=False):
    w,h=(1280,640) if social else (1080,600)
    s=f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="26" fill="{B.BG}" stroke="{B.LINE}" stroke-width="2"/>'
    s+=f'<g transform="translate(64,86) scale({190/128})">{mark()}</g>'
    s+=text(294,139,B.NAME,62,weight=600)
    s+=text(297,183,'Time-resolved step-scan FTIR',24,B.MUTED)
    s+=text(297,217,'artifact simulator',24,B.MUTED)
    s+=text(298,253,f'Version {B.VERSION} · Simulated data',15,B.AMBER)
    if social:
        s+=text(96,383,'Explore interferograms, spectra and kinetics.',29)
        s+=text(96,432,'Mirror motion · Optical leakage · Electrical pickup',24,B.MUTED)
    # Decorative analytic fringe, never presented as an acquired spectrum.
    for phase,col,amp in [(0,B.BLUE,23),(.45,B.GREEN,19),(.9,B.CORAL,15)]:
        s+=path([(1+(w-2)*i/600,h-60-amp*math.exp(-((i/600-.35)/.17)**2)*math.cos(2*math.pi*16*i/600+phase)) for i in range(601)],col,1.6,.65)
    return svg(s,w,h)


def render(source,target,size=None):
    r=QtSvg.QSvgRenderer(QtCore.QByteArray(source.encode('utf-8')))
    assert r.isValid(),target
    native=r.defaultSize();w,h=size or (native.width(),native.height())
    im=QtGui.QImage(w,h,QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    im.fill(QtCore.Qt.GlobalColor.transparent)
    painter=QtGui.QPainter(im);painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    r.render(painter,QtCore.QRectF(0,0,w,h));painter.end()
    assert im.save(str(target)),target


def main():
    app=Q.QApplication([]);B.ensure_fonts();B.ASSETS.mkdir(exist_ok=True)
    assets={'fringescope':svg(mark(),128,128),'fringescope_small':svg(mark(True),128,128),
            'splash_background':card(),'social_card':card(True)}
    for name,source in assets.items():
        (B.ASSETS/f'{name}.svg').write_text(source,encoding='utf-8')
        render(source,B.ASSETS/f'{name}.png')
    sizes=(16,20,24,32,48,64,128,256)
    for size in sizes:
        render(svg(mark(size<=24),128,128),B.ASSETS/f'fringescope_{size}.png',(size,size))
    images=[Image.open(B.ASSETS/f'fringescope_{s}.png').convert('RGBA') for s in sizes]
    images[-1].save(B.ASSETS/'fringescope.ico',format='ICO',sizes=[(s,s) for s in sizes],append_images=images[:-1])
    manifest={'name':B.NAME,'subtitle':B.SUBTITLE,'version':B.VERSION,'selected_direction':'C — Spectral focus / magnifying lens',
              'artwork':'Original editable SVG with locally rendered PNG and multiresolution ICO',
              'small_icon':'Simplified mark at 16, 20 and 24 px',
              'decorative_waveform':'Analytic artwork; not measured or simulated spectra',
              'splash':'Background has no baked-in progress text; startup.py draws live stages'}
    (B.ASSETS/'branding_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'assets':str(B.ASSETS),'icon_sizes':sizes,'status':'rendered'}))


if __name__=='__main__':main()
