"""Build the static FringeScope Web site into web/site (standard library only).

Sources of truth stay in desktop/: THEORY.md, TUTORIAL.md,
MODEL_ASSUMPTIONS.md, REFERENCES.bib, ui_help.py, tour.py, ftir_sim.py and the
synthetic model JSON. They are rendered or copied byte-for-byte; the
build manifest records SHA-256 for every published file.

    python -X utf8 web/build_web.py
"""
from __future__ import annotations
import ast, hashlib, html, json, re, shutil, struct, sys
from pathlib import Path

WEB = Path(__file__).resolve().parent
REPOSITORY = WEB.parent
ROOT = REPOSITORY/'desktop'
SITE = WEB/'site'
SRC = WEB/'src'
sys.path.insert(0, str(ROOT))
import build_theory as BT  # noqa: E402  (stdlib + paper_style only)
import branding  # noqa: E402
import ui_help  # noqa: E402
import tour  # noqa: E402  (guided-tour steps shared with the desktop application)

VERSION = branding.VERSION
REPO = json.loads((ROOT/'release_config.json').read_text(encoding='utf-8'))['repository_url']
PAGES_URL = 'https://Fisicas.github.io/FringeScope/'
PYODIDE = '314.0.8'
PLOTLY = 'vendor/plotly-cartesian-4.3.0.min.js'
KERNEL = ['ftir_sim.py', 'synthetic_model.json', 'release_config.json', 'THEORY.md', 'REFERENCES.bib', 'MODEL_ASSUMPTIONS.md']
NAV = [('index.html', 'Explore'), ('demonstrations.html', 'Demonstrations'), ('theory.html', 'Theory'),
       ('tutorial.html', 'Tutorial'), ('cite.html', 'Download / Cite')]
IMAGE_DIRS = ['theory_assets', 'demonstration_assets', 'evidence_assets', 'model_assets']


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_size(path: Path):
    with open(path, 'rb') as f:
        head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n': raise ValueError(f'{path} is not a PNG')
    return struct.unpack('>II', head[16:24])


def settings_defaults():
    """Settings() dataclass defaults, read with ast so the build needs no NumPy."""
    tree = ast.parse((ROOT/'ftir_sim.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'Settings':
            return {item.target.id: ast.literal_eval(item.value) for item in node.body if isinstance(item, ast.AnnAssign)}
    raise RuntimeError('Settings dataclass not found')


def slug(title):
    return re.sub('[^a-z0-9]+', '-', title.lower()).strip('-')


def inline(text):
    return BT.inline(text)


# ---------------------------------------------------------------- page shell
def page(filename, title, description, body, build, scripts='', head=''):
    current = ' aria-current="page"'
    nav = ''.join(f'<a href="{href}"{current if href == filename else ""}>{label}</a>' for href, label in NAV)
    return f'''<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#1d242c">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:image" content="img/social_card.png">
<link rel="icon" type="image/png" sizes="32x32" href="img/fringescope_32.png">
<link rel="icon" type="image/svg+xml" href="img/fringescope.svg">
<link rel="apple-touch-icon" href="img/fringescope_256.png">
<link rel="stylesheet" href="css/site.css?v={build}">
<script>try{{var t=localStorage.getItem('fringescope-theme');if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
{head}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="index.html"><img src="img/fringescope_64.png" width="34" height="34" alt=""><span><span class="brand-name">FringeScope</span><span class="brand-sub">Time-resolved step-scan FTIR artifact simulator</span></span></a>
    <button class="icon-button" id="menu-button" aria-controls="site-nav" aria-expanded="false" aria-label="Menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
    <nav class="site-nav" id="site-nav" aria-label="Main">{nav}</nav>
    <button class="icon-button" id="theme-button" aria-label="Switch to light mode"></button>
  </div>
</header>
{body}
<footer class="site-footer"><div class="inner">
  <span>FringeScope {VERSION} · web preview build <code>{build}</code></span>
  <span>All displayed spectra are simulated.</span>
  <a href="cite.html#license">MIT license and notices</a>
  <a href="cite.html#privacy">Privacy</a>
  <a href="{REPO}">Source repository</a>
</div></footer>
<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true" aria-label="Enlarged figure">
  <div class="lb-bar"><span class="lb-title"></span><button class="btn" data-action="fit">Fit to screen</button><button class="btn" data-action="close">Close</button></div>
  <div class="lb-scroll"><img alt=""></div>
</div>
<script src="js/common.js?v={build}"></script>
{scripts}
</body>
</html>
'''


def themed_img(rel, alt, width=None, height=None, cls='', zoom=None, lazy=True, style=''):
    rel = Path(rel)
    light = 'img/'+rel.as_posix()
    dark_rel = Path(rel.parts[0]+'_dark').joinpath(*rel.parts[1:])
    dark = 'img/'+dark_rel.as_posix() if (ROOT/dark_rel).exists() else light
    size = f' width="{round(width)}" height="{round(height)}"' if width else ''
    z = f' data-zoom="{html.escape(zoom, quote=True)}"' if zoom else ''
    c = f' class="{cls}"' if cls else ''
    loading = ' loading="lazy"' if lazy else ''
    st = f' style="{style}"' if style else ''
    return (f'<img src="{dark}" data-dark-src="{dark}" data-light-src="{light}"{size}{c}{z}{st} '
            f'alt="{html.escape(alt, quote=True)}"{loading} decoding="async">')


# ---------------------------------------------------------------- markdown
def equation(key, assets):
    d = assets[key]; factor = .85
    w = d['width']*factor
    # Scale down to fit a phone, but never below 80 %; wider equations scroll sideways.
    img = themed_img('theory_assets/'+Path(d['file']).with_suffix('.svg').name, d['alt'], w, d['height']*factor, lazy=False, style=f'min-width:{round(.8*w)}px')
    return (f'<div class="equation" id="eq-{d["number"]}" role="group" aria-label="Equation {d["number"]}">'
            f'<div class="eq-body">{img}</div><span class="eq-number">({d["number"]})</span></div>')


def render_markdown(text, assets=None, figure_prefix=''):
    """Small renderer for this repository's Markdown subset. Returns (html, headings, figures)."""
    text = BT.prepare_equation_blocks(text)
    out, para, bullets, ordered, headings, figures = [], [], [], [], [], {}
    pending_figure = None
    lines = text.splitlines()

    def flush():
        nonlocal pending_figure
        if para:
            joined = ' '.join(para); para.clear()
            m = re.fullmatch(r'\[\[equation:([a-z_]+)\]\]', joined)
            if m and assets: out.append(equation(m[1], assets))
            elif pending_figure is not None and joined.startswith('**Figure'):
                pending_figure['caption'] = joined
                out[pending_figure['index']] = figure_html(pending_figure)
                figures[pending_figure['src']] = pending_figure
                pending_figure = None
            else:
                out.append('<p>'+inline(joined)+'</p>')
        if bullets: out.append('<ul>'+''.join(f'<li>{inline(b)}</li>' for b in bullets)+'</ul>'); bullets.clear()
        if ordered: out.append('<ol>'+''.join(f'<li>{inline(b)}</li>' for b in ordered)+'</ol>'); ordered.clear()

    for line in lines:
        s = line.strip()
        if line.startswith('# '): flush(); continue
        if line.startswith('## '):
            flush(); title = line[3:].strip(); anchor = slug(title); headings.append((title, anchor))
            out.append(f'<h2 id="{anchor}">{inline(title)}<a class="anchor" href="#{anchor}" aria-label="Link to this section">#</a></h2>')
        elif s.startswith('!['):
            flush(); m = re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m:
                pending_figure = {'alt': m[1], 'src': m[2], 'caption': '', 'index': len(out)}
                out.append(figure_html(pending_figure))
        elif s.startswith('- '):
            if para or ordered: flush()
            bullets.append(s[2:])
        elif re.match(r'^\d+\. ', s):
            if para or bullets: flush()
            ordered.append(re.sub(r'^\d+\. ', '', s))
        elif not s: flush()
        else:
            if bullets or ordered: flush()
            para.append(s)
    flush()
    return '\n'.join(out), headings, figures


def figure_html(f):
    path = ROOT/f['src']
    w, h = png_size(path)
    caption = inline(f['caption']) if f['caption'] else html.escape(f['alt'])
    label = re.match(r'\*\*(Figure \d+)\.\*\*', f['caption'] or '')
    zoom = (label[1]+' · ' if label else '')+f['alt']
    dark = Path(Path(f['src']).parts[0]+'_dark').joinpath(*Path(f['src']).parts[1:])
    return (f'<figure class="fig">'+themed_img(f['src'], f['alt'], w, h, zoom=zoom)+
            f'<figcaption>{caption}</figcaption><div class="fig-actions"><a href="img/{f["src"]}" data-light-href="img/{f["src"]}" '
            f'data-dark-href="img/{dark.as_posix() if (ROOT/dark).exists() else f["src"]}">Open full-size image</a></div></figure>')


def bib_entries():
    text = (ROOT/'REFERENCES.bib').read_text(encoding='utf-8')
    entries = []
    for m in re.finditer(r'@(\w+)\{([^,]+),(.*?)\n\}', text, re.S):
        fields = {k.lower(): v.strip().strip('{}') for k, v in re.findall(r'(\w+)=\{((?:[^{}]|\{[^{}]*\})*)\}', m[3])}
        fields['type'] = m[1]; fields['key'] = m[2]
        entries.append(fields)
    return entries


def reference_html(e):
    authors = e.get('author', '').replace('{', '').replace('}', '').replace(' and ', '; ')
    parts = [html.escape(authors)+(f' ({e["year"]})' if e.get('year') else '')+'.', f'<cite>{html.escape(e.get("title", ""))}</cite>.']
    venue = e.get('journal') or e.get('school') or ''
    if venue: parts.append(html.escape(venue)+(f' <b>{e["volume"]}</b>' if e.get('volume') else '')+(f', {e["pages"].replace("--", "–")}' if e.get('pages') else '')+'.')
    if e.get('doi'): parts.append(f'<a href="https://doi.org/{html.escape(e["doi"])}">doi:{html.escape(e["doi"])}</a>')
    elif e.get('url'): parts.append(f'<a href="{html.escape(e["url"])}">{html.escape(e["url"])}</a>')
    if e.get('note'): parts.append(f'<span class="note">{html.escape(e["note"])}</span>')
    return '<li id="ref-'+html.escape(e['key'])+'">'+' '.join(parts)+'</li>'


def article(headings, body, title, tagline, infobox=''):
    toc = ''.join(f'<li><a href="#{a}">{inline(t)}</a></li>' for t, a in headings)
    return f'''<main id="main" class="page">
<details class="toc-mobile"><summary>☰ Contents</summary><ol>{toc}</ol></details>
<div class="article-shell">
  <nav class="toc" aria-label="Contents"><h2>Contents</h2><ol>{toc}</ol><p><a class="back-top" href="#main">↑ Back to top</a></p></nav>
  <article class="prose">
    <h1>{html.escape(title)}</h1>
    <p class="tagline">{tagline}</p>
    {infobox}
    {body}
    <p><a class="back-top" href="#main">↑ Back to top</a></p>
  </article>
</div>
</main>'''


def tour_cta(lead='Guided tour.'):
    return ('<div class="tour-cta"><p><b>'+lead+'</b> The guided tour runs the simulator in your browser and changes one source at a time, '
            'in four steps. Your own settings are restored when it ends.</p>'
            '<p><a class="btn primary" href="index.html#tour">Start the guided tour</a></p></div>')


def tour_guide():
    return tour.as_json()['steps']


# ---------------------------------------------------------------- pages
def theory_page(build, assets):
    source = (ROOT/'THEORY.md').read_text(encoding='utf-8')
    body, headings, figures = render_markdown(source, assets)
    lead_match = re.search(r'^# .*?\n\n(.*?)\n\n', source, re.S)
    lead = lead_match[1].strip() if lead_match else ''
    body = body.replace('<p>'+inline(lead)+'</p>', '', 1)
    model, model_headings, _ = render_markdown((ROOT/'MODEL_ASSUMPTIONS.md').read_text(encoding='utf-8'))
    model_title = 'Model assumptions and provenance'
    headings.append((model_title, slug(model_title)))
    body += f'\n<h2 id="{slug(model_title)}">{model_title}<a class="anchor" href="#{slug(model_title)}" aria-label="Link to this section">#</a></h2>\n'+model
    headings.append(('References', 'references'))
    body += '\n<h2 id="references">References<a class="anchor" href="#references" aria-label="Link to this section">#</a></h2>\n<ol class="references">'+''.join(reference_html(e) for e in bib_entries())+'</ol>'
    headings.append(('See also', 'see-also'))
    body += ('\n<h2 id="see-also">See also<a class="anchor" href="#see-also" aria-label="Link to this section">#</a></h2><ul>'
             '<li><a href="index.html">Explore the live simulator</a>: the same engine with linked contour, spectrum, kinetics and DAS views.</li>'
             '<li><a href="demonstrations.html">Demonstrations</a>: the fixed lessons behind Figures 1, 2, 3 and 5.</li>'
             '<li><a href="tutorial.html">Guided tutorial</a>: ideal → mirror → globar → actinic leakage.</li>'
             f'<li><a href="{REPO}">Source repository</a>: desktop/THEORY.md is the source of this page.</li></ul>')
    infobox = f'''<table class="infobox" aria-label="Summary">
  <caption>FringeScope</caption>
  <tr><td colspan="2"><img src="img/fringescope_256.png" alt="FringeScope magnifying-lens logo" width="92" height="92"></td></tr>
  <tr><th scope="row">Type</th><td>Forward simulator of time-resolved step-scan FTIR artifacts</td></tr>
  <tr><th scope="row">Signal</th><td>Synthetic PSI-inspired ΔA: two bin-averaged exponentials plus a causal residual</td></tr>
  <tr><th scope="row">Spectral grid</th><td>513 channels, ≈ 2106.39–1053.20 cm⁻¹, descending</td></tr>
  <tr><th scope="row">Time grid</th><td>590 bins of 6 µs, −153 to 3381 µs</td></tr>
  <tr><th scope="row">Artifacts</th><td>Mirror motion, globar leakage, 532 nm actinic pickup, electrical pickup, return mismatch</td></tr>
  <tr><th scope="row">Version</th><td>{VERSION}</td></tr>
  <tr><th scope="row">License</th><td>MIT</td></tr>
</table>'''
    tag = 'From the FringeScope scientific notes. All displayed spectra are simulated; equations and figures are generated from the repository.'
    lead_html = f'<p class="lead">{inline(lead)}</p>' if lead else ''
    hatnote = ('<p class="hatnote">New to step-scan artifacts? <a href="index.html#tour">Take the four-step guided tour</a> '
               'in the live simulator, or read the <a href="tutorial.html">tutorial</a>.</p>')
    marker = '<h2 id="guided-tutorial">'
    if marker in body:
        k = body.index('</h2>', body.index(marker))+len('</h2>')
        body = body[:k]+tour_cta()+body[k:]
    content = article(headings, hatnote+lead_html+infobox+body, 'Theory and evidence', tag)
    desc = 'How mirror motion, optical folding, continuous leakage and pulsed pickup create artifacts in time-resolved step-scan FTIR: equations, assumptions, evidence and limits.'
    return page('theory.html', 'Theory and evidence · FringeScope', desc, content, build), figures


DEMOS = [
    ('opd_detector_traces', 'OPD detector traces', 'demonstration_assets/opd_detector_traces.png'),
    ('mirror_harmonics_psi', 'Mirror harmonics and PSI', 'demonstration_assets/mirror_harmonics_psi.png'),
    ('coaddition_phase', 'Coaddition and phase', 'demonstration_assets/coaddition_phase.png'),
    ('artifact_baselines', 'Artifact-only baselines', 'demonstration_assets/artifact_baselines.png'),
]


def demonstrations_page(build, figures):
    blocks, headings = [], []
    for key, title, src in DEMOS:
        caption = figures.get(src, {}).get('caption', '')
        w, h = png_size(ROOT/src)
        anchor = slug(title); headings.append((title, anchor))
        dark = src.replace('demonstration_assets/', 'demonstration_assets_dark/')
        blocks.append(f'<h2 id="{anchor}">{html.escape(title)}<a class="anchor" href="#{anchor}" aria-label="Link to this section">#</a></h2>'
                      f'<figure class="fig">{themed_img(src, title, w, h, zoom=title)}<figcaption>{inline(caption)}</figcaption>'
                      f'<div class="fig-actions"><a href="img/{src}" data-light-href="img/{src}" data-dark-href="img/{dark}">Open full-size image</a></div></figure>')
    headings.append(('Reproducing these figures', 'reproduce'))
    body = ('<div class="notice"><strong>Precomputed lessons.</strong> These four figures are fixed, explicitly stated acquisitions rendered by '
            '<code>build_demos.py</code> from the same synthetic PSI generator used in Explore. They are independent of the Explore controls and '
            'contain no experimental arrays. Settings, units and offsets are written in each figure.</div>'
            '<p>The lessons are original simulations inspired by detector-position, artifact-baseline and phase-correlated averaging experiments in '
            '<a href="https://doi.org/10.1366/0003702991947595">Rödig and Siebert (1999)</a>. They are not reproductions of that paper\'s data. '
            'Tap or click a figure to enlarge it.</p>'+''.join(blocks)+
            '<h2 id="reproduce">Reproducing these figures<a class="anchor" href="#reproduce" aria-label="Link to this section">#</a></h2>'
            '<p>Run <code>python -X utf8 build_demos.py</code> in the repository to regenerate the light and dark figures and '
            '<a href="img/demonstration_assets/metrics.json">metrics.json</a>. The desktop application shows the same lessons under <b>Demonstrations</b> '
            'and can export their numerical arrays.</p>')
    content = article(headings, body, 'Demonstrations', 'Fixed synthetic lessons on mirror motion, harmonics, electrical pickup and coherent averaging.')
    return page('demonstrations.html', 'Demonstrations · FringeScope', 'Original synthetic step-scan FTIR lessons: OPD detector traces, artifact baselines, mirror harmonics and coaddition phase.', content, build)


def tutorial_page(build):
    desktop, _, _ = render_markdown((ROOT/'TUTORIAL.md').read_text(encoding='utf-8'))
    def h2(title, anchor):
        return f'<h2 id="{anchor}">{title}<a class="anchor" href="#{anchor}" aria-label="Link to this section">#</a></h2>'
    how = ('<ol class="how">'
           '<li><b>Start.</b> Press <b>Start the guided tour</b> here, or <b>Guided tour</b> in the Explore toolbar. '
           'A tour panel opens: beside the plots on a computer, at the bottom of the screen on a phone or tablet.</li>'
           '<li><b>Read the step.</b> Each step says <em>what changed</em> and lists numbered things to look at. '
           'The same numbers appear on the plots, the source buttons and the view tabs. Tap or click an item to jump to it.</li>'
           '<li><b>Continue.</b> Press the highlighted <b>Next</b> button at the bottom of the panel. <b>Back</b> returns to the previous step. '
           'On a phone, <b>Hide</b> folds the panel away so you can see more of the plot.</li>'
           '<li><b>Leave at any time.</b> <b>End tour</b> (in the panel or the toolbar) or the Esc key ends the tour. Finishing or ending restores your previous controls and selections.</li>'
           '</ol>')
    steps = []
    for n, g in enumerate(tour_guide(), 1):
        look = ''.join(f'<li>{html.escape(item["text"])}</li>' for item in g['look'])
        steps.append(f'<section class="tour-step"><h3 id="step-{n}">Step {n}: {html.escape(g["title"])}</h3>'
                     f'<p><b>What changed.</b> {html.escape(g["changed"])}</p><p><b>Where to look</b></p><ol>{look}</ol>'
                     f'<p><a href="index.html#tour-{n}">Open step {n} in Explore</a></p></section>')
    headings = [('How the tour works', 'how'), ('The four steps', 'steps'), ('Desktop application', 'desktop')]
    body = (tour_cta()+h2('How the tour works', 'how')+how+h2('The four steps', 'steps')+''.join(steps)+
            h2('Desktop application', 'desktop')+
            '<p>The Windows application runs the same four steps from <b>Guided tour</b> in its header; each press advances one step. '
            'Its notes, from <code>TUTORIAL.md</code>:</p>'+desktop)
    content = article(headings, body, 'Guided tutorial', 'Ideal → mirror → globar → actinic pickup, one source at a time, with your settings restored at the end.')
    return page('tutorial.html', 'Tutorial · FringeScope', 'A step-by-step guided tour of FringeScope: ideal signal, mirror motion, globar leakage and actinic pickup.', content, build)


def cite_page(build):
    bibtex = (f'@software{{FringeScope,\n  author  = {{Nelson, Michael Raymond}},\n  title   = {{FringeScope: Time-resolved step-scan FTIR artifact simulator}},\n'
              f'  version = {{{VERSION}}},\n  url     = {{{REPO}}},\n  license = {{MIT}}\n}}')
    refs = ''.join(reference_html(e) for e in bib_entries())
    headings = [('Desktop application', 'desktop'), ('Cite FringeScope', 'cite'), ('License', 'license'), ('Web edition: how it runs', 'web-edition'),
                ('Privacy', 'privacy'), ('Primary references', 'references')]
    body = f'''
<h2 id="desktop">Desktop application<a class="anchor" href="#desktop" aria-label="Link to this section">#</a></h2>
<p>The Windows application is the reference edition. It runs offline and includes the same engine, the demonstrations with numerical export, and the offline theory reader.</p>
<div class="card-grid">
  <div class="card"><h3>Windows installer</h3><p>Per-user installer, no administrator rights required. Version {VERSION}.</p><p><a class="btn primary" href="{REPO}/releases">GitHub Releases</a></p><p class="note">Release assets appear here after publication. The installer is currently unsigned.</p></div>
  <div class="card"><h3>Portable ZIP</h3><p>Standalone folder: keep <code>FringeScope.exe</code> beside its <code>_internal</code> folder.</p><p><a class="btn" href="{REPO}/releases">GitHub Releases</a></p></div>
  <div class="card"><h3>Source</h3><p>Python 3.12 with pinned NumPy, SciPy, Matplotlib and PySide6. Includes tests and figure generators.</p><p><a class="btn" href="{REPO}">Repository</a></p></div>
</div>
<h2 id="cite">Cite FringeScope<a class="anchor" href="#cite" aria-label="Link to this section">#</a></h2>
<p>Cite the version you used, and cite the primary spectroscopy papers for scientific claims. No software DOI has been assigned yet.</p>
<pre class="cite">Nelson, M. R. FringeScope: Time-resolved step-scan FTIR artifact simulator (version {VERSION}) [Computer software]. {REPO}</pre>
<pre class="cite">{html.escape(bibtex)}</pre>
<p>Machine-readable metadata: <code>CITATION.cff</code> in the repository.</p>
<h2 id="license">License<a class="anchor" href="#license" aria-label="Link to this section">#</a></h2>
<p>Original FringeScope code, documentation and synthetic model inputs: MIT license, Copyright (c) 2026 Michael Raymond Nelson. Third-party components keep their own licenses:</p>
<ul>
<li><b>Plotly.js</b> 4.3.0 (cartesian bundle), MIT; served from this site. <a href="vendor/PLOTLY_LICENSE.txt">License text</a>.</li>
<li><b>Pyodide</b> {PYODIDE} (MPL-2.0), with CPython, NumPy, SciPy and OpenBLAS under their own licenses, is loaded at run time from <a href="https://cdn.jsdelivr.net/pyodide/v{PYODIDE}/full/">jsDelivr</a>; this site does not redistribute it.</li>
<li>The desktop application's notices are in <code>desktop/THIRD_PARTY_NOTICES.md</code> and <code>desktop/licenses/</code> in the repository.</li>
</ul>
<h2 id="web-edition">Web edition: how it runs<a class="anchor" href="#web-edition" aria-label="Link to this section">#</a></h2>
<p>Explore runs the repository's <code>ftir_sim.py</code> unchanged under Pyodide {PYODIDE} in a background Web Worker. The engine files are checked against SHA-256 values in the <a href="build_manifest.json">build manifest</a> before use. NumPy and SciPy versions in the browser can differ slightly from the desktop's pinned versions; the <a href="validate.html">numerical self-check</a> compares browser results with native desktop fixtures on your own device.</p>
<p>Demonstrations and figures on the theory page are precomputed by the repository's figure scripts. Exports from Explore are generated by the desktop <code>export_result</code> function inside the worker and include the browser runtime versions.</p>
<h2 id="privacy">Privacy<a class="anchor" href="#privacy" aria-label="Link to this section">#</a></h2>
<p>There is no account, upload, analytics or cookie. Calculations run on your device. The site stores only your light/dark choice in your browser's local storage. As with any web page, the hosting service (GitHub Pages) and the runtime CDN (jsDelivr) receive standard request information such as IP address and browser user agent, under their own policies.</p>
<h2 id="references">Primary references<a class="anchor" href="#references" aria-label="Link to this section">#</a></h2>
<ol class="references">{refs}</ol>'''
    content = article(headings, body, 'Download and cite', f'FringeScope {VERSION} · MIT license')
    return page('cite.html', 'Download and cite · FringeScope', 'Download the FringeScope desktop application, cite the software and read the license, privacy and web-runtime notes.', content, build)


def explore_page(build, config):
    body = (SRC/'explore.html').read_text(encoding='utf-8')
    data = json.dumps(config, ensure_ascii=False).replace('</', '<\\/')
    scripts = (f'<script id="fs-config" type="application/json">{data}</script>\n'
               f'<script src="{PLOTLY}"></script>\n<script type="module" src="js/explore.js?v={build}"></script>')
    head = f'<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>'
    return page('index.html', 'FringeScope · step-scan FTIR artifact simulator',
                'Interactive browser simulator of mirror motion, optical folding, globar leakage and actinic pickup artifacts in time-resolved step-scan FTIR. Runs on your device.',
                body, build, scripts, head)


def validate_page(build, config):
    body = (SRC/'validate.html').read_text(encoding='utf-8')
    data = json.dumps({'manifest': config['manifest']}).replace('</', '<\\/')
    scripts = f'<script id="fs-config" type="application/json">{data}</script>\n<script type="module" src="js/validate.js?v={build}"></script>'
    return page('validate.html', 'Numerical self-check · FringeScope', 'Compare the browser engine with native desktop fixtures on this device.', body, build, scripts)


# ---------------------------------------------------------------- build
def main():
    if SITE.exists(): shutil.rmtree(SITE)
    for d in ['css', 'js', 'py', 'img', 'vendor']: (SITE/d).mkdir(parents=True)
    # Engine and model files: byte-for-byte copies.
    kernel = {}
    for name in KERNEL:
        data = (ROOT/name).read_bytes(); (SITE/'py'/name).write_bytes(data); kernel[name] = sha(data)
    data = (WEB/'web_kernel.py').read_bytes(); (SITE/'py'/'web_kernel.py').write_bytes(data); kernel['web_kernel.py'] = sha(data)
    shutil.copy2(SRC/'css'/'site.css', SITE/'css'/'site.css')
    for js in (SRC/'js').glob('*.js'): shutil.copy2(js, SITE/'js'/js.name)
    for f in (WEB/'vendor').iterdir(): shutil.copy2(f, SITE/'vendor'/f.name)
    if (SRC/'parity_fixtures.json').exists(): shutil.copy2(SRC/'parity_fixtures.json', SITE/'parity_fixtures.json')
    for d in IMAGE_DIRS:
        for variant in [d, d+'_dark']:
            if not (ROOT/variant).exists(): continue
            (SITE/'img'/variant).mkdir()
            for f in (ROOT/variant).iterdir():
                if f.suffix.lower() in ('.png', '.svg', '.json') and f.name != 'equations.json': shutil.copy2(f, SITE/'img'/variant/f.name)
    for name in ['fringescope.svg', 'fringescope_32.png', 'fringescope_64.png', 'fringescope_256.png', 'social_card.png']:
        shutil.copy2(ROOT/'assets'/name, SITE/'img'/name)
    (SITE/'.nojekyll').write_bytes(b'')
    # Build identity covers every input that changes behavior.
    digest = hashlib.sha256()
    inputs = list((SITE/'py').iterdir())+list((SITE/'js').iterdir())+[SITE/'css'/'site.css', SRC/'explore.html', SRC/'controls.json', ROOT/'tour.py', ROOT/'ui_help.py', Path(__file__).resolve()]
    for path in sorted(inputs, key=lambda p: (p.parent.name, p.name)):
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    build = digest.hexdigest()[:12]
    spec = json.loads((SRC/'controls.json').read_text(encoding='utf-8'))
    spec.pop('_comment', None)
    defaults = settings_defaults()
    config = dict(version=VERSION, controls=spec, tips=ui_help.TIPS, tour=tour.as_json(),
                  sources=[[k, label, setting, tip] for k, (label, setting, tip) in ui_help.SOURCES.items()],
                  settings_defaults=defaults, manifest=dict(build=build, kernel=kernel, pyodide=PYODIDE))
    assets = json.loads((ROOT/'theory_assets'/'equations.json').read_text(encoding='utf-8'))
    theory, figures = theory_page(build, assets)
    pages = {'index.html': explore_page(build, config), 'theory.html': theory, 'demonstrations.html': demonstrations_page(build, figures),
             'tutorial.html': tutorial_page(build), 'cite.html': cite_page(build), 'validate.html': validate_page(build, config)}
    for name, text in pages.items(): (SITE/name).write_text(text, encoding='utf-8')
    (SITE/'404.html').write_text(page('404.html', 'Not found · FringeScope', 'Page not found.',
        '<main id="main" class="page"><article class="prose"><h1>Page not found</h1><p><a href="index.html">Open FringeScope</a></p></article></main>', build), encoding='utf-8')
    files = {p.relative_to(SITE).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
             for p in sorted(SITE.rglob('*')) if p.is_file()}
    manifest = dict(application='FringeScope Web (preview)', version=VERSION, build=build, pyodide=PYODIDE,
                    note='Engine files under py/ are byte-identical copies of the desktop/ source files listed in kernel_sources.',
                    kernel_sources={k: v for k, v in kernel.items()}, files=files)
    (SITE/'build_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    total = sum(v['bytes'] for v in files.values())
    print(json.dumps({'site': str(SITE), 'build': build, 'files': len(files), 'bytes': total}))


if __name__ == '__main__':
    main()
