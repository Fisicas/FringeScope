"""Create an offline publication-style theory page with deterministic equations.

The source is THEORY.md. All scientific prose/citations are preserved. Equations
replace plain-text formula blocks or restate formulas already described there.
"""
from pathlib import Path
import html,json,re
from paper_style import serif_family

EQUATIONS={
    'chemical':(r'$\Delta A(\tilde{\nu},t)=\left[H(\tilde{\nu})e^{-t/\tau_{\mathrm{H}}}+R(\tilde{\nu})e^{-t/\tau_{\mathrm{R}}}+C(\tilde{\nu})\right]u(t)$',
        'Delta A(nu,t) = [H(nu) exp(-t/tau_H) + R(nu) exp(-t/tau_R) + C(nu)] u(t)'),
    'bin':(r'$\overline{\Delta A}(\tilde{\nu},t_i)=\frac{1}{\Delta t}\int_{t_i-\Delta t/2}^{t_i+\Delta t/2}\Delta A(\tilde{\nu},t)\,dt$',
        'Recorded bin mean equals the time integral over the bin divided by Delta t.'),
    'ifg':(r'$I(x,t)=\int S(\tilde{\nu},t)\cos(2\pi\tilde{\nu}x)\,d\tilde{\nu}$',
        'Interferogram I(x,t) is the cosine transform of single-beam spectrum S(nu,t).'),
    'shift':(r'$\delta x=2d,\qquad I(x+\delta x,t)\simeq\sum_{m=0}^{4}\frac{(\delta x)^m}{m!}\frac{\partial^m I(x,t)}{\partial x^m}$',
        'OPD displacement is twice mirror displacement, in matching length units. Shift is expanded through fourth order.'),
    'sampling':(r'$F_s=\frac{1}{\Delta x}=2B,\qquad \tilde{\nu}\in[B,2B]$',
        'Spatial sampling frequency Fs is 1/Delta x = 2B; desired band is B to 2B.'),
    'alias':(r'$q(\tilde{\nu})=\left|\left[(\tilde{\nu}+B)\;\mathrm{mod}\;2B\right]-B\right|,\qquad \tilde{\nu}_{\mathrm{display}}=2B-q$',
        'q(nu) = abs(((nu + B) modulo 2B) - B); displayed wavenumber is 2B - q.'),
    'leak':(r'$\Delta A_{\mathrm{obs}}=-\log_{10}\!\left[\frac{S_0\,10^{-\Delta A_{\mathrm{true}}}+L}{S_0+L}\right]$',
        'Observed Delta A = -log10[(S0 times 10 to minus true Delta A + leakage L)/(S0 + L)].'),
    'small':(r'$\Delta A\simeq-\frac{\Delta S}{\ln(10)\,S_0}\qquad (|\Delta S|\ll S_0)$',
        'For a small signal, Delta A approximately equals -Delta S divided by ln(10) S0.'),
    'period':(r'$T=\frac{1}{f},\qquad N_{\mathrm{cycles}}=f\,T_{\mathrm{window}},\qquad \Delta t_{\phi}=\frac{\Delta\phi}{360^{\circ}f}$',
        'Period is 1/f; cycle count is f times the time window; phase timing shift is Delta phi/(360 degrees times f).'),
    'steady_zero':(r'$\Delta A_{\mathrm{true}}=0\quad\Longrightarrow\quad\Delta A_{\mathrm{obs}}=-\log_{10}\!\left(\frac{S_0+L_{\mathrm{CW}}}{S_0+L_{\mathrm{CW}}}\right)=0$',
        'For zero true change, the same steady leakage in both records gives zero observed difference absorbance.'),
    'dilution':(r'$\Delta A_{\mathrm{obs}}\simeq\frac{S_0}{S_0+L_{\mathrm{CW}}}\,\Delta A_{\mathrm{true}}$',
        'For a small difference signal, the observed amplitude is scaled by S0 divided by S0 plus steady leakage.'),
    'demo_local':(r'$\delta I(x,t)\simeq 2d(t)\,\frac{\partial I(x+2b)}{\partial x}$',
        'A small mirror displacement d changes the AC detector signal by twice d times the local OPD derivative about common mirror bias b.'),
    'demo_real':(r'$\Delta A_b(t)=-\log_{10}\!\left[\frac{\cos\{\kappa[b+a\sin\theta(t)]\}}{\cos(\kappa b)}\right]$',
        'For fixed real readout and stationary biased reference, difference absorbance is minus log10 of cos(kappa times bias plus drive) divided by cos(kappa bias).'),
    'coadd':(r'$\Delta A_N=-\log_{10}\!\left[\frac{\frac{1}{N}\sum_{j=0}^{N-1}S_j}{S_{\mathrm{ref}}}\right]$',
        'Average the N detector or intensity records first, then form difference absorbance against the declared reference.'),
    'phase_factor':(r'$C_m=\frac{1}{N}\sum_{j=0}^{N-1}e^{im\phi_j},\qquad C_m^{(0,\pi)}=\frac{1+(-1)^m}{2}$',
        'Intensity harmonic m has phase-coherence factor C_m; a 0 and pi phase pair cancels odd orders and retains even orders.'),
}
NUMBERING=['chemical','bin','period','small','ifg','shift','demo_local','demo_real','coadd','phase_factor','sampling','alias','leak','steady_zero','dilution']

def ensure_assets(root,theme='light'):
    root=Path(root);folder=root/('theory_assets_dark' if theme=='dark' else 'theory_assets');manifest=folder/'equations.json'
    if manifest.exists():
        existing=json.loads(manifest.read_text(encoding='utf-8'))
        if set(existing)==set(EQUATIONS) and all((folder/d['file']).exists() and d.get('renderer_version')==4 and d.get('number')==NUMBERING.index(key)+1 for key,d in existing.items()):return existing
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.mathtext import math_to_image
    from matplotlib.font_manager import FontProperties
    from PIL import Image
    folder.mkdir(exist_ok=True)
    records={}
    for i,(key,(latex,plain)) in enumerate(EQUATIONS.items(),1):
        name=f'equation_{i:02}.png';path=folder/name
        with matplotlib.rc_context({'savefig.transparent':True,'savefig.facecolor':'none','figure.facecolor':'none','mathtext.fontset':'stix'}):
            color='#e4e9ef' if theme=='dark' else '#20242a'
            math_to_image(latex,str(path),prop=FontProperties(family='STIXGeneral',size=19),dpi=240,format='png',color=color)
            math_to_image(latex,str(path.with_suffix('.svg')),prop=FontProperties(family='STIXGeneral',size=19),dpi=240,format='svg',color=color)
        with Image.open(path) as im:w,h=im.size
        records[key]={'file':name,'width':w/2.5,'height':h/2.5,'number':NUMBERING.index(key)+1,'alt':plain,'latex':latex,'renderer_version':4,'theme':theme}
    manifest.write_text(json.dumps(records,indent=2),encoding='utf-8')
    return records

def math_text(text):
    # One pass prevents substitutions from modifying markup inserted earlier.
    symbols={'τH':'<i>τ</i><sub>H</sub>','τR':'<i>τ</i><sub>R</sub>',
        'βH':'<i>β</i><sub>H</sub>','βR':'<i>β</i><sub>R</sub>',
        'S₀':'<i>S</i><sub>0</sub>','S0':'<i>S</i><sub>0</sub>',
        'ΔAobs':'Δ<i>A</i><sub>obs</sub>','ΔAtrue':'Δ<i>A</i><sub>true</sub>',
        'LCW':'<i>L</i><sub>CW</sub>','νdisplay':'<i>ν̃</i><sub>display</sub>',
        'νlaser':'<i>ν̃</i><sub>laser</sub>','νH':'<i>ν̃</i><sub>H</sub>',
        'φH':'<i>φ</i><sub>H</sub>','IIR,pk':'<i>I</i><sub>IR,pk</sub>',
        'Fs':'<i>F</i><sub>s</sub>','IFGpeak':'IFG<sub>peak</sub>',
        'ΔAN':'Δ<i>A</i><sub>N</sub>','Sref':'<i>S</i><sub>ref</sub>',
        'φj':'<i>φ</i><sub>j</sub>','Cm':'<i>C</i><sub>m</sub>','δI':'δ<i>I</i>',
        'ΔA':'Δ<i>A</i>','ΔS':'Δ<i>S</i>','δx':'δ<i>x</i>','ν':'<i>ν̃</i>'}
    pattern='|'.join(re.escape(key) for key in sorted(symbols,key=len,reverse=True))
    text=re.sub(pattern,lambda match:symbols[match[0]],text)
    supers=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺','0123456789−+')
    subs=str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789')
    text=re.sub('[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+',lambda match:'<sup>'+match[0].translate(supers)+'</sup>',text)
    text=re.sub('[₀₁₂₃₄₅₆₇₈₉]+',lambda match:'<sub>'+match[0].translate(subs)+'</sub>',text)
    text=re.sub(r'10\^\(([^)]+)\)',r'10<sup>\1</sup>',text)
    return text


def inline(text):
    text=html.escape(text)
    text=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',r'<a href="\2">\1</a>',text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',text)
    text=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',text)
    def code(match):
        value=match[1]
        if any(token in value for token in ('Δ','ν','τ','θ','/','√','=','[B,2B]')) and '.py' not in value:
            return '<span class="math">'+value+'</span>'
        return '<code>'+value+'</code>'
    text=re.sub(r'`([^`]+)`',code,text)
    return math_text(text)

def headings(root):
    source=(Path(root)/'THEORY.md').read_text(encoding='utf-8')
    return [(line[3:],re.sub('[^a-z0-9]+','-',line[3:].lower()).strip('-')) for line in source.splitlines() if line.startswith('## ')]



def prepare_equation_blocks(source):
    """Render GitHub-native math with the same numbered assets offline.

    Match complete canonical expressions, including equation numbers, so a
    manuscript edit cannot silently leave a different equation in the app.
    """
    blocks = {
        latex.removeprefix('$').removesuffix('$') + rf'\tag{{{NUMBERING.index(key)+1}}}': key
        for key, (latex, _) in EQUATIONS.items()
    }
    def replace(match):
        expression = match[1].strip()
        if expression not in blocks:
            raise ValueError('Theory math block differs from the canonical numbered equation')
        return '[[equation:' + blocks[expression] + ']]'
    return re.sub(r'```math[ \t]*\r?\n(.*?)\r?\n```', replace, source, flags=re.S)


def build_html(root,font_px=20,content_width=1400,embedded=False,theme='dark'):
    root=Path(root);assets=ensure_assets(root,theme)
    dark=theme=='dark';fg='#dde3ea' if dark else '#20242a';bg='#1b2128' if dark else '#ffffff'
    muted='#aab8c4' if dark else '#526478';link='#85c5ff' if dark else '#166277'
    border='#465765' if dark else '#cbd3d8';cell='#26343e' if dark else '#e5eeea'
    def image_tag(relative,width,height,alt):
        original=Path(relative);dark_relative=(Path(original.parts[0]+'_dark').joinpath(*original.parts[1:])).as_posix()
        shown=dark_relative if dark and (root/dark_relative).exists() else relative
        return (f'<img src="{html.escape(shown,quote=True)}" width="{round(width)}" height="{round(height)}" '
            f'data-light-src="{html.escape(relative,quote=True)}" data-dark-src="{html.escape(dark_relative,quote=True)}" alt="{html.escape(alt,quote=True)}">')
    source=prepare_equation_blocks((root/'THEORY.md').read_text(encoding='utf-8'))
    pieces=[];paragraph=[];bullets=[];table=[]
    def equation(key):
        d=assets[key];factor=font_px/20
        width=d['width']*factor;height=d['height']*factor
        available=max(250,content_width-120)
        if width>available:height*=available/width;width=available
        return (f'<table class="equation" width="100%" cellpadding="8" cellspacing="0"><tr>'
            f'<td align="center">'+image_tag('theory_assets/'+d['file'],width,height,d['alt'])+'</td>'
            f'<td width="76" align="right" valign="middle" nowrap="nowrap" class="eqnumber">({NUMBERING.index(key)+1})</td></tr></table>')
    def para(text):
        match=re.fullmatch(r'\[\[equation:([a-z_]+)\]\]',text)
        if match:return equation(match[1])
        if text.startswith('`ΔA(ν,t) ='):
            return equation('chemical')+'<p class="caption">Here <em>u(t)</em> is the causal unit step: zero before the flash and unity afterwards. The offset is a spectral term, not a third resolved decay.</p>'
        if text.startswith('`q = abs('):return equation('alias')
        if text.startswith('`ΔAobs ='):return equation('leak')
        if text.startswith('`steady_zero`'):return equation('steady_zero')
        if text.startswith('`dilution`'):return equation('dilution')
        for key in ['demo_local','demo_real','coadd','phase_factor']:
            if text.startswith('`'+key+'`'):return equation(key)
        extras=''
        if 'Exponential and offset bases are averaged' in text:extras+=equation('bin')
        if text.startswith('At 840 Hz, the period'):extras+=equation('period')
        if text.startswith('The optical interferogram is represented'):
            text=text.replace('`I(x,t) = ∫ S(ν,t) cos(2πνx) dν`','the cosine transform in Eq. (5)')
            extras+=equation('ifg')+equation('shift')+'<p class="caption">In Eq. (6), <em>d</em> and <em>δx</em> use the same length unit. The implementation converts mirror displacement from nm to cm before evaluating the derivatives.</p>'
        if text.startswith('Optical folding occurs'):extras+=equation('sampling')
        if text.startswith('There is also a spatial-shape limitation'):extras+=equation('small')
        return '<p>'+inline(text)+'</p>'+extras
    def flush():
        if paragraph:pieces.append(para(' '.join(paragraph)));paragraph.clear()
        if bullets:pieces.append('<ul>'+''.join('<li>'+inline(s)+'</li>' for s in bullets)+'</ul>');bullets.clear()
        if table:
            rows=[]
            for i,row in enumerate(table):
                if re.fullmatch(r'[\s|:\-]+',row):continue
                cells=[s.strip() for s in row.strip('|').split('|')]
                tag='th' if not rows else 'td'
                rows.append('<tr>'+''.join(f'<{tag}>'+inline(s)+f'</{tag}>' for s in cells)+'</tr>')
            pieces.append('<table class="data" width="100%" cellpadding="9" cellspacing="0" border="1">'+''.join(rows)+'</table>');table.clear()
    section_headings=[]
    for line in source.splitlines():
        if line.startswith('# '):continue
        if line.startswith('## '):
            flush();title=line[3:];anchor=re.sub('[^a-z0-9]+','-',title.lower()).strip('-');section_headings.append((title,anchor))
            pieces.append(f'<h2 id="{anchor}"><a name="{anchor}"></a>'+inline(title)+'</h2>')
        elif line.startswith('- '):
            if paragraph or table:flush()
            bullets.append(line[2:])
        elif line.startswith('|'):
            if paragraph or bullets:flush()
            table.append(line)
        elif line.startswith('!['):
            flush();match=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line.strip())
            if match:
                from PIL import Image
                relative=match[2];path=root/relative
                if path.is_file():
                    with Image.open(path) as im:w,h=im.size
                    width=min(max(250,content_width-16),1100);height=width*h/w
                    pieces.append('<p align="center" class="figure">'+image_tag(relative,width,height,match[1])+'</p>')
        elif not line.strip():flush()
        else:
            if bullets or table:flush()
            # Numbered source lists are retained as ordinary paragraphs, with
            # readable spacing rather than nested implementation-oriented lists.
            paragraph.append(line.strip())
    flush()
    toc=''.join(f'<p><a href="#{a}">{html.escape(t)}</a></p>' for t,a in section_headings)
    contents='' if embedded else '<aside><strong>Contents</strong>'+toc+'</aside>'
    opening='' if embedded else '<div class="theory-shell">'+contents+'<main>'
    closing='' if embedded else '</main></div>'
    padding='0' if embedded else '28px 36px'
    family=serif_family()
    switch='' if embedded else '<div class="appearance"><button id="appearance-switch" onclick="toggleAppearance()">Switch to light mode</button></div>'
    script='' if embedded else '''<script>
function toggleAppearance(){const light=document.documentElement.dataset.theme!=='light';
document.documentElement.dataset.theme=light?'light':'dark';
document.querySelectorAll('img[data-light-src]').forEach(i=>i.src=light?i.dataset.lightSrc:i.dataset.darkSrc);
document.getElementById('appearance-switch').textContent=light?'Switch to dark mode':'Switch to light mode';}
</script>'''
    return f'''<!doctype html><html data-theme="{theme}"><head><meta charset="utf-8"><title>FringeScope theory and evidence</title>
<style>
body {{font-family:"{family}",Palatino,"STIXGeneral",Georgia,serif;font-size:{font_px}px;color:{fg};background:{bg};margin:0;padding:{padding};line-height:1.4;}}
.theory-shell {{display:grid;grid-template-columns:215px minmax(0,1fr);gap:32px;}}
aside {{font-family:Arial,sans-serif;font-size:14px;position:sticky;top:24px;align-self:start;}}
aside p {{font-size:14px;line-height:1.4;margin:12px 0;}} main {{min-width:0;}}
@media(max-width:1050px) {{.theory-shell {{display:block;}} aside {{position:static;border-bottom:1px solid #cbd3d8;margin-bottom:24px;}}}}
p,li {{font-size:{font_px}px;margin-top:6px;margin-bottom:12px;}}
h1 {{font-family:"{family}",serif;font-size:{round(font_px*1.8)}px;font-weight:bold;margin:0 0 16px;}}
h2 {{font-family:"{family}",serif;font-size:{round(font_px*1.28)}px;color:{fg};margin-top:22px;margin-bottom:12px;}}
.eyebrow {{font-family:"DejaVu Sans",sans-serif;font-size:{font_px-3}px;color:{'#9ccdbc' if dark else '#487368'};}}
.abstract {{font-size:{font_px}px;color:{muted};}}
.toc,.caption {{font-size:{font_px-2}px;color:{muted};}}
.equation {{margin-top:12px;margin-bottom:14px;border:0;background:{bg};}}
.figure {{line-height:1;margin-top:8px;margin-bottom:8px;}}
.eqnumber {{font-family:"{family}",serif;color:{muted};font-size:{font_px-1}px;}}
.math {{font-family:"{family}",serif;}} sub,sup {{font-size:75%;}} sub {{vertical-align:sub;}} sup {{vertical-align:super;}}
.data {{border-collapse:collapse;border-color:{border};font-size:{font_px-2}px;margin-top:14px;margin-bottom:16px;}}
th {{background:{cell};font-weight:650;}} td,th {{border-color:{border};}}
a {{color:{link};text-decoration:underline;}} code {{font-size:{font_px-1}px;color:{muted};}}
hr {{border:0;border-top:1px solid {border};}} img {{max-width:100%;height:auto;}}
.appearance {{text-align:right;margin-bottom:12px;}} button {{padding:8px 14px;background:{cell};color:{fg};border:1px solid {border};border-radius:4px;cursor:pointer;}}
html[data-theme="light"] body,html[data-theme="light"] .equation {{color:#20242a;background:#ffffff;}}
html[data-theme="light"] h2 {{color:#20242a;}} html[data-theme="light"] a {{color:#166277;}}
html[data-theme="light"] .eyebrow {{color:#487368;}}
html[data-theme="light"] .caption,html[data-theme="light"] .abstract,html[data-theme="light"] code,html[data-theme="light"] .eqnumber {{color:#526478;}}
html[data-theme="light"] th,html[data-theme="light"] button {{background:#e5eeea;color:#20242a;}}
</style></head><body>{switch}{opening}
<p class="eyebrow">FringeScope scientific notes</p>
<h1>Theory and evidence</h1>
<p class="abstract">A forward model for optical folding and oscillatory artifacts in time-resolved step-scan FTIR. Assumptions, synthetic demonstrations and limits on mechanism attribution are stated explicitly.</p>
<p class="caption">Displayed values are rounded for reading; calculations and exported settings retain their precision.</p><hr>
{''.join(pieces)}
<hr><p class="caption">Equations are rendered locally at high resolution; this reading copy requires no network connection. The complete scientific source remains in THEORY.md, with bibliographic records in REFERENCES.bib.</p>
{closing}{script}</body></html>'''

def main():
    root=Path(__file__).resolve().parent
    ensure_assets(root,'light');ensure_assets(root,'dark')
    (root/'THEORY.html').write_text(build_html(root),encoding='utf-8')
    print(json.dumps({'html':str(root/'THEORY.html'),'equations':len(EQUATIONS)}))

if __name__=='__main__':main()
