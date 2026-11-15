// FringeScope Web: Explore workspace. Display logic follows plots.py and app.py;
// every simulated/fitted array is computed by ftir_sim.py in the worker.
/* global Plotly */
const CONFIG = JSON.parse(document.getElementById('fs-config').textContent);
const SPEC = CONFIG.controls;
const TIPS = CONFIG.tips;
const SOURCES = CONFIG.sources; // [[key, label, setting, tip], ...]
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const touchFirst = window.matchMedia('(pointer: coarse)').matches;

// ---------- formatting (display_format.number) ----------
function number(value, scientific = true) {
  value = Number(value);
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return '0';
  if (scientific && (Math.abs(value) < .01 || Math.abs(value) >= 1e5)) {
    let [m, e] = value.toExponential(2).split('e');
    m = m.replace(/0+$/, '').replace(/\.$/, '');
    return m + 'e' + parseInt(e, 10);
  }
  const r = value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  return r === '-0' ? '0' : r;
}
const f1 = v => Number(v).toFixed(1);
const f2 = v => Number(v).toFixed(2);

// ---------- state ----------
const state = {
  controls: {}, wn: SPEC.selection.wavenumber, time: SPEC.selection.time_us,
  view: 'explore', diagnostic: 'interferograms', panel: 'spectrum', mode: 'select',
  result: null, meta: null, cache: {}, seq: 0, running: false, again: false, againFree: false,
  tour: { step: -1, saved: null }, uirev: 1, ready: false,
  computePromise: null, committedControls: null, lastError: null, exporting: false,
};
const controlSpecs = {};
function walk(section, fn) {
  if (section.toggle) fn({ key: section.toggle, type: 'toggle', value: false });
  (section.controls || []).forEach(fn);
  (section.details || []).concat(section.subsections || []).forEach(s => walk(s, fn));
}
SPEC.sections.forEach(s => walk(s, c => { controlSpecs[c.key] = c; state.controls[c.key] = c.value; }));

// ---------- engine client ----------
const engine = {
  worker: null, id: 0, pending: new Map(),
  start() {
    this.worker = new Worker(`js/worker.js?v=${CONFIG.manifest.build}`, { type: 'module' });
    this.worker.onmessage = e => {
      const m = e.data;
      if (m.type === 'progress') return loading.step(m.stage, m.detail);
      const p = this.pending.get(m.id); if (!p) return;
      this.pending.delete(m.id);
      m.ok ? p.resolve(m.value) : p.reject(new Error(m.error));
    };
    this.worker.onerror = e => {
      const error = new Error(e.message || 'The compute worker could not start.');
      for (const p of this.pending.values()) p.reject(error);
      this.pending.clear(); state.ready = false; loading.fail(error.message);
    };
    const base = new URL('.', location.href).href;
    return this.call('init', { base, manifest: CONFIG.manifest });
  },
  call(cmd, payload = {}, transfer = []) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage(Object.assign({ id, cmd }, payload), transfer);
    });
  },
};

// ---------- loading panel ----------
const loading = {
  el: null, stages: ['Downloading the Python runtime', 'Loading NumPy and SciPy', 'Starting the FringeScope engine', 'Computing the ideal signal'],
  show() {
    this.el = $('#loading');
    this.el.hidden = false;
    this.el.innerHTML = `<div><strong>Preparing the live simulator</strong>
      <ol>${this.stages.map(s => `<li>${s}</li>`).join('')}</ol>
      <p class="note">The first visit downloads about 20 MB (Python, NumPy and SciPy compiled to WebAssembly); your browser caches it afterwards. All calculations run on this device.</p></div>`;
    this.step(0);
  },
  step(i) {
    if (!this.el) return;
    $$('li', this.el).forEach((li, k) => { li.className = k < i ? 'done' : k === i ? 'active' : ''; });
    setEngine('loading', this.stages[i] + '…');
  },
  hide() { if (this.el) this.el.hidden = true; },
  fail(message) {
    setEngine('error', 'Engine unavailable');
    if (!this.el) return;
    this.el.hidden = false;
    this.el.innerHTML = `<div><p class="error"><strong>The live simulator could not start.</strong><br>${escapeHtml(message)}</p>
      <p class="note">It needs a current browser with WebAssembly and module workers, and access to cdn.jsdelivr.net for the pinned Python runtime. The <a href="theory.html">theory</a> and <a href="demonstrations.html">demonstrations</a> work without it.</p>
      <button class="btn" onclick="location.reload()">Retry</button></div>`;
  },
};
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function setEngine(kind, text) { const e = $('#engine'); e.dataset.state = kind; $('#engine-text').textContent = text; }

// ---------- controls UI ----------
function helpButton(key, text) {
  if (!text) return '';
  return `<button type="button" class="help-btn" aria-expanded="false" aria-controls="help-${key}" aria-label="About this control">?</button>`;
}
function fieldHtml(c) {
  const tip = c.help || TIPS[c.key] || '';
  const id = `c-${c.key}`;
  const show = c.show_if ? ` data-show-if="${c.show_if[0]}=${c.show_if[1]}"` : '';
  let input;
  if (c.type === 'select') input = `<select id="${id}" data-key="${c.key}">${c.items.map(([v, t]) => `<option value="${v}">${escapeHtml(t)}</option>`).join('')}</select>`;
  else if (c.type === 'checkbox') {
    return `<div class="field check"${show}><input type="checkbox" id="${id}" data-key="${c.key}"><label for="${id}">${escapeHtml(c.label)}</label>${helpButton(c.key, tip)}
      <p class="help-text" id="help-${c.key}" hidden>${escapeHtml(tip)}</p></div>`;
  } else input = `<input type="number" id="${id}" data-key="${c.key}" min="${c.min}" max="${c.max}" step="${c.step}" inputmode="decimal">`;
  return `<div class="field"${show}><label for="${id}">${escapeHtml(c.label)}</label>${input}${helpButton(c.key, tip)}
    <p class="help-text" id="help-${c.key}" hidden>${escapeHtml(tip)}</p></div>`;
}
function sectionHtml(s, cls = 'section') {
  const toggle = s.toggle ? `<label class="toggle-label"><input type="checkbox" data-key="${s.toggle}" aria-label="${escapeHtml(s.title)} on/off"> On</label>` : '';
  const tip = s.toggle ? (SOURCES.find(x => x[2] === s.toggle) || [])[3] || TIPS[s.toggle] : '';
  const body = (s.controls || []).map(fieldHtml).join('')
    + (s.details || []).map(d => sectionHtml(d, 'sub')).join('')
    + (s.subsections || []).map(d => sectionHtml(d, 'sub')).join('')
    + (s.refit ? '<div class="field-wide"><button type="button" class="btn" id="refit">Refit the two lifetimes</button><p class="note">Unweighted variable projection with signed amplitudes and β = 1. Convergence does not establish a physical assignment or uncertainty.</p></div>' : '');
  return `<details class="${cls}" data-section="${s.toggle || ''}"><summary><span class="title">${escapeHtml(s.title)}</span>${toggle}</summary>
    <div class="section-body">${tip ? `<p class="note">${escapeHtml(tip)}</p>` : ''}${body}</div></details>`;
}
function buildControls() {
  $('#control-sections').innerHTML = SPEC.sections.map(s => sectionHtml(s)).join('');
  $$('#control-sections [data-key]').forEach(el => {
    const key = el.dataset.key;
    const handler = () => readControl(el, key);
    el.addEventListener(el.type === 'number' ? 'input' : 'change', handler);
    if (el.type === 'number') el.addEventListener('change', () => { readControl(el, key, true); });
    if (el.closest('summary')) el.addEventListener('click', e => e.stopPropagation());
  });
  $$('#control-sections .help-btn').forEach(b => b.addEventListener('click', () => {
    const p = document.getElementById(b.getAttribute('aria-controls'));
    const open = b.getAttribute('aria-expanded') !== 'true';
    b.setAttribute('aria-expanded', String(open)); p.hidden = !open;
  }));
  $('#refit').addEventListener('click', () => recompute(true));
  syncControls();
}
function readControl(el, key, finished = false) {
  const c = controlSpecs[key];
  let value;
  if (el.type === 'checkbox') value = el.checked;
  else if (el.tagName === 'SELECT') value = el.value;
  else {
    value = parseFloat(el.value);
    if (!Number.isFinite(value)) { if (finished) setInput(el, state.controls[key], c); return; }
    value = Math.min(c.max, Math.max(c.min, value));
    if (c.type === 'integer') value = Math.round(value);
    if (finished) setInput(el, value, c);
  }
  state.controls[key] = value;
  if (c.type === 'toggle') { sourceToggled(key, value); return; }
  updateVisibility();
  schedule();
}
function setInput(el, value, c) {
  if (el.type === 'checkbox') el.checked = !!value;
  else if (el.tagName === 'SELECT') el.value = value;
  else el.value = c && c.type === 'integer' ? String(value) : number(value);
}
function syncControls() {
  $$('#control-sections [data-key]').forEach(el => setInput(el, state.controls[el.dataset.key], controlSpecs[el.dataset.key]));
  updateVisibility(); syncSourceButtons();
}
function updateVisibility() {
  $$('[data-show-if]').forEach(el => { const [k, v] = el.dataset.showIf.split('='); el.hidden = state.controls[k] !== v; });
}
function syncSourceButtons() {
  $$('.source-toggle').forEach(b => {
    const on = !!state.controls[b.dataset.setting];
    b.setAttribute('aria-pressed', String(on));
    $('.state', b).textContent = on ? 'On' : 'Off';
  });
}
function sourceToggled(key, on) {
  const section = $(`details[data-section="${key}"]`);
  if (section && on) section.open = true;
  syncSourceButtons();
  schedule();
}
function setControl(key, value) {
  const c = controlSpecs[key];
  if (!c) return;
  if (c.type === 'number' || c.type === 'integer') value = Math.min(c.max, Math.max(c.min, Number(value)));
  state.controls[key] = value;
}

// ---------- compute scheduling (latest request wins) ----------
let timer = null;
function schedule() { syncSourceButtons(); clearTimeout(timer); timer = setTimeout(() => recompute(false), 250); }
function recompute(free = false) {
  clearTimeout(timer); timer = null;
  if (!state.ready) return Promise.resolve(false);
  state.again = true; state.againFree = state.againFree || free;
  if (state.computePromise) return state.computePromise;
  state.computePromise = drainComputations();
  return state.computePromise;
}
async function drainComputations() {
  state.running = true;
  try {
    while (state.again) {
      const free = state.againFree; state.again = false; state.againFree = false;
      const seq = ++state.seq, controls = Object.assign({}, state.controls), t0 = performance.now();
      setEngine('busy', free ? 'Refitting lifetimes…' : 'Computing…');
      try {
        const value = await engine.call('compute', { controls, free });
        if (state.again) continue;
        state.result = wrap(value.arrays); state.meta = value.meta; state.cache = {}; state.resultSeq = seq;
        state.committedControls = JSON.stringify(controls); state.lastError = null;
        state.lastMs = performance.now() - t0;
        await render();
        setEngine('ready', `Ready · last calculation ${(state.lastMs / 1000).toFixed(2)} s`);
      } catch (error) {
        state.lastError = error.message;
        $('#warnings').textContent = `Configuration error: ${error.message}. Previous result remains displayed.`;
        setEngine('error', 'Settings invalid · previous result displayed');
      }
    }
    return state.lastError === null;
  } finally { state.running = false; state.computePromise = null; }
}
function lockWorkspace(locked) {
  const main = $('#main'); main.inert = locked; main.setAttribute('aria-busy', String(locked));
  $('#theme-button').disabled = locked;
}
async function settleWorkspace() {
  if (timer !== null || state.computePromise || JSON.stringify(state.controls) !== state.committedControls) {
    await (state.computePromise || recompute(false));
  }
  if (state.lastError) throw new Error(state.lastError);
  // Include queued crosshair paints before taking a scientific/figure snapshot.
  await new Promise(resolve => requestAnimationFrame(resolve));
  await rendering;
  if (!state.result || JSON.stringify(state.controls) !== state.committedControls) throw new Error('Wait for a valid committed result');
}
function wrap(arrays) {
  const out = {};
  for (const [k, a] of Object.entries(arrays)) {
    const rows = a.shape.length === 2 ? a.shape[0] : 1, cols = a.shape.length === 2 ? a.shape[1] : a.shape[0];
    out[k] = { data: a.data, rows, cols, shape: a.shape,
      row(i) { return a.data.subarray(i * cols, (i + 1) * cols); },
      col(j) { const o = new Float64Array(rows); for (let i = 0; i < rows; i++) o[i] = a.data[i * cols + j]; return o; } };
  }
  return out;
}
async function viewData(name, params) {
  const key = name + JSON.stringify(params || {});
  if (!state.cache[key]) {
    const seq = state.resultSeq;
    const value = await engine.call('view', { name, params, resultId: state.meta.result_id });
    if (seq !== state.resultSeq) throw new Error('stale');
    state.cache[key] = { meta: value.meta, a: wrap(value.arrays) };
  }
  return state.cache[key];
}

// ---------- selection helpers ----------
function nearest(arr, v) { let best = 0, d = Infinity; for (let i = 0; i < arr.length; i++) { const e = Math.abs(arr[i] - v); if (e < d) { d = e; best = i; } } return best; }
function channel() { return nearest(state.result.nu.data, state.wn); }
function timeIndex() { return nearest(state.result.t_us.data, state.time); }
function interpRow(m, t, q) { // plots.selected_spectrum
  const n = t.length; let k = 1; while (k < n - 1 && t[k] < q) k++;
  const fr = (q - t[k - 1]) / (t[k] - t[k - 1]);
  const a = m.row(k - 1), b = m.row(k), out = new Float64Array(a.length);
  for (let i = 0; i < a.length; i++) out[i] = (1 - fr) * a[i] + fr * b[i];
  return { values: out, fraction: fr };
}
const scale = (arr, s = 1e6) => Float64Array.from(arr, v => v * s);
function isNative() { const t = state.result.t_us.data; return Math.abs(t[timeIndex()] - state.time) < 1e-8; }
function bandHigh() { return state.result.nu.data[0]; }
function bandLow() { const n = state.result.nu.data; return n[n.length - 1]; }

// ---------- theme-aware plot styling (ui_theme.style_figure) ----------
function palette() {
  const dark = FringeScopeTheme.get() === 'dark';
  return dark ? {
    dark, bg: '#13171c', text: '#dde3ea', muted: '#a4b0bb', grid: 'rgba(82,96,107,.45)', axis: '#52606b',
    ideal: '#6cc58a', sim: '#ff7a66', heat: '#6fa8ff', rp: '#f2b24c', mix: '#b8a0cf', fit: '#b9c4ce', gray: '#b9c4ce', zero: 'rgba(142,154,168,.6)', guide: '#f2b24c', alias: '#b8a0cf',
    cmap: [[0, '#6fa8ff'], [0.5, '#13171c'], [1, '#ff7a66']], legend: 'rgba(19,23,28,.78)',
  } : {
    dark, bg: '#ffffff', text: '#24323e', muted: '#526574', grid: 'rgba(182,198,208,.6)', axis: '#b6c6d0',
    ideal: '#278b72', sim: '#d65d3f', heat: '#268bd2', rp: '#df8a25', mix: '#79627e', fit: '#303945', gray: '#808080', zero: 'rgba(0,0,0,.4)', guide: '#f2b24c', alias: '#6c6175',
    cmap: [[0, '#053061'], [.1, '#2166ac'], [.2, '#4393c3'], [.3, '#92c5de'], [.4, '#d1e5f0'], [.5, '#f7f7f7'], [.6, '#fddbc7'], [.7, '#f4a582'], [.8, '#d6604d'], [.9, '#b2182b'], [1, '#67001f']],
    legend: 'rgba(255,255,255,.85)',
  };
}
function axis(title, P, extra = {}) {
  return Object.assign({ title: { text: title, font: { size: 11.5 } }, gridcolor: P.grid, linecolor: P.axis, zerolinecolor: P.grid, tickcolor: P.axis,
    tickfont: { size: 10.5, color: P.muted }, showline: true, mirror: false, ticks: 'outside', ticklen: 4, automargin: true, exponentformat: 'power' }, extra);
}
function layout(title, xTitle, yTitle, P, extra = {}) {
  const narrow = window.innerWidth < 520;
  return Object.assign({
    title: { text: `<b>${title}</b>`, x: 0.01, xanchor: 'left', y: 0.985, yanchor: 'top', font: { size: narrow ? 12 : 13, color: P.text } },
    paper_bgcolor: P.bg, plot_bgcolor: P.bg, font: { color: P.text, family: 'system-ui, -apple-system, "Segoe UI", Roboto, "DejaVu Sans", sans-serif', size: 11 },
    margin: { l: 58, r: 12, t: 38, b: 44 }, xaxis: axis(xTitle, P), yaxis: axis(yTitle, P),
    showlegend: true, legend: { x: 1, xanchor: 'right', y: 1, yanchor: 'top', bgcolor: P.legend, bordercolor: P.axis, borderwidth: 1, font: { size: narrow ? 9 : 10 } },
    hovermode: state.mode === 'zoom' ? 'closest' : false, dragmode: state.mode === 'zoom' ? 'zoom' : false,
    uirevision: state.uirev, shapes: [], annotations: [],
  }, extra);
}
function spectralAxis(P, title = 'Wavenumber (cm⁻¹)') { return axis(title, P, { range: [bandHigh(), bandLow()], autorange: false }); }
function vline(x, P, dash = 'dot', color, width = 1, yref = 'paper') { return { type: 'line', xref: 'x', yref, x0: x, x1: x, y0: 0, y1: 1, line: { color: color || P.guide, width, dash } }; }
function hline(y, P, dash = 'solid', color, width = .8) { return { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: y, y1: y, line: { color: color || P.zero, width, dash } }; }
function line(x, y, name, color, extra = {}) { return Object.assign({ type: 'scatter', mode: 'lines', x, y, name, line: { color, width: 1.4 }, hovertemplate: '%{x:.2f}, %{y:.3g}<extra>' + name + '</extra>' }, extra); }
function plotConfig() {
  return { responsive: true, displaylogo: false, displayModeBar: state.mode === 'zoom', scrollZoom: state.mode === 'zoom', doubleClick: 'reset',
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d'], toImageButtonOptions: { format: 'png', scale: 2, filename: 'FringeScope_panel' } };
}
function heatmap(nu, t, m, keep, limit, P, name = 'µOD') {
  const x = keep.map(j => nu[j]);
  const z = new Array(m.rows);
  for (let i = 0; i < m.rows; i++) { const r = m.row(i), out = new Array(keep.length); for (let k = 0; k < keep.length; k++) { const v = r[keep[k]]; out[k] = Number.isFinite(v) ? v * 1e6 : null; } z[i] = out; }
  return { type: 'heatmap', x, y: Array.from(t), z, zmin: -limit, zmax: limit, colorscale: P.cmap, zsmooth: false,
    colorbar: { title: { text: name, side: 'right' }, thickness: 11, len: .92, tickfont: { size: 10, color: P.muted }, outlinewidth: 0 },
    hovertemplate: '%{x:.2f} cm⁻¹<br>%{y:.1f} µs<br>%{z:.3g} µOD<extra></extra>', showlegend: false };
}
function validKeep() {
  if (state.result._keep) return state.result._keep;
  const v = state.result.valid.data, keep = [];
  for (let j = 0; j < v.length; j++) if (v[j]) keep.push(j);
  return (state.result._keep = keep);
}

// ---------- plot cards ----------
function cards(container, names, cls = '') {
  container.className = 'plot-grid ' + cls;
  container.innerHTML = names.map(n => `<div class="plot-card${n.tall ? ' tall' : ''}" data-card="${n.id}" ${n.panel ? `data-panel="${n.panel}"` : ''}><div class="plot" id="plot-${n.id}" role="img" aria-label="${escapeHtml(n.label)}"></div></div>`).join('');
}
async function draw(id, data, lay, selector) {
  const gd = document.getElementById('plot-' + id);
  if (!gd) return;
  await Plotly.react(gd, data, lay, plotConfig());
  if (selector) attachSelector(gd, selector); else detachSelector(gd);
}

// ---------- Explore view ----------
function exploreFigures() {
  const r = state.result, m = state.meta, P = palette();
  const nu = r.nu.data, t = r.t_us.data, j = channel(), actual = nu[j];
  const spectrum = interpRow(r.ideal, t, state.time), observed = interpRow(r.observed, t, state.time);
  const interpolated = spectrum.fraction > 1e-8 && spectrum.fraction < 1 - 1e-8;
  const figs = {};
  if (!state.result._contour) state.result._contour = heatmap(nu, t, r.observed, validKeep(), m.contour_limit_uOD, P);
  const hm = Object.assign({}, state.result._contour, { colorscale: P.cmap, colorbar: Object.assign({}, state.result._contour.colorbar, { tickfont: { size: 10, color: P.muted } }) });
  figs.contour = [[hm], layout('ΔA · clean-reference color scale', 'Wavenumber (cm⁻¹)', 'Time after flash (µs)', P, {
    xaxis: spectralAxis(P), showlegend: false, margin: { l: 58, r: 6, t: 38, b: 44 },
    shapes: [hline(0, P, 'solid', P.zero), vline(actual, P, 'dash', P.guide, 1.2), hline(state.time, P, 'dash', P.guide, 1.2)] })];
  const st = [line(nu, scale(spectrum.values), 'Artifact-free PSI ΔA', P.ideal, { line: { color: P.ideal, width: 2.4 } }),
    line(nu, scale(observed.values), 'Effects applied', P.sim, { line: { color: P.sim, width: 1.2 } })];
  const sshapes = [hline(0, P), vline(actual, P, 'dot')];
  const sann = [];
  if (m.laser_interferometric) {
    sshapes.push(vline(m.laser_alias_cm1, P, 'dot', P.alias));
    sann.push({ x: m.laser_alias_cm1, y: .03, xref: 'x', yref: 'paper', text: 'Laser alias', textangle: -90, showarrow: false, xanchor: 'right', yanchor: 'bottom', font: { size: 10, color: P.alias } });
  }
  figs.spectrum = [st, layout(`Spectrum · ${f1(state.time)} µs${interpolated ? ' (interpolated)' : ''}`, 'Wavenumber (cm⁻¹)', 'ΔA (µOD)', P, { xaxis: spectralAxis(P), shapes: sshapes, annotations: sann })];
  const kt = [line(t, scale(r.ideal.col(j)), 'Artifact-free PSI ΔA', P.ideal, { line: { color: P.ideal, width: 2.4 } }),
    line(t, scale(r.observed.col(j)), 'Effects applied', P.sim, { line: { color: P.sim, width: 1.1 } }),
    line(t, scale(r.reconstruction.col(j)), m.offset ? '2exp + offset projection' : '2exp projection', P.fit, { line: { color: P.fit, width: 1.1, dash: 'dash' } })];
  figs.kinetics = [kt, layout(`Kinetics · ${number(actual)} cm⁻¹`, 'Time after flash (µs)', 'ΔA (µOD)', P, { shapes: [hline(0, P), vline(0, P, 'solid', P.zero, .7), vline(state.time, P, 'dot')] })];
  figs.das = [dasTraces(P), layout('DAS and offset · signed amplitudes', 'Wavenumber (cm⁻¹)', 'Amplitude at t = 0 (µOD)', P, {
    xaxis: spectralAxis(P), shapes: [hline(0, P), vline(actual, P, 'dot')], ...dasLegend(P) })];
  return figs;
}
function dasLegend(P) {
  // Six entries cover the curves on narrow screens; place them below the axes there.
  if (window.innerWidth >= 1100) return { legend: { x: 1, xanchor: 'right', y: 1, yanchor: 'top', bgcolor: P.legend, bordercolor: P.axis, borderwidth: 1, font: { size: 9 } } };
  return { legend: { orientation: 'h', x: 0, xanchor: 'left', y: -0.22, yanchor: 'top', bgcolor: 'rgba(0,0,0,0)', font: { size: 9.5 } }, margin: { l: 58, r: 12, t: 38, b: 112 } };
}
function dasTraces(P) {
  const r = state.result, m = state.meta, nu = r.nu.data, out = [];
  const truth = r.truth_das, das = r.das;
  [[P.heat, 'Input heating-like DAS'], [P.rp, 'Input recombination DAS']].forEach(([c, n], i) => out.push(line(nu, scale(truth.row(i)), n, c, { line: { color: c, width: 2.6 }, opacity: .5 })));
  if (truth.rows > 2) out.push(line(nu, scale(truth.row(2)), 'Unresolved residual + heating-like offset', P.mix, { line: { color: P.mix, width: 2.6 }, opacity: .6 }));
  [P.heat, P.rp].forEach((c, i) => out.push(line(nu, scale(das.row(i)), `Projected ${f2(m.taus[i])} µs`, c, { line: { color: c, width: 1.2, dash: 'dash' } })));
  if (das.rows > 2) out.push(line(nu, scale(das.row(2)), 'Fitted constant', P.gray, { line: { color: P.gray, width: 1.2 } }));
  return out;
}
async function renderExplore(onlySelection = false) {
  const figs = exploreFigures();
  if (!onlySelection) {
    await draw('contour', ...figs.contour, 'contour');
  } else {
    const gd = document.getElementById('plot-contour');
    if (gd && gd.data) await Plotly.relayout(gd, { shapes: figs.contour[1].shapes });
  }
  await Promise.all([draw('spectrum', ...figs.spectrum, 'spectral'), draw('kinetics', ...figs.kinetics, 'time'), draw('das', ...figs.das, 'spectral')]);
}

// ---------- secondary views ----------
async function renderCompare() {
  const { meta, a } = await viewData('compare');
  const r = state.result, P = palette(), nu = r.nu.data, t = r.t_us.data, keep = validKeep();
  const titles = ['Clean reference', 'Effects applied · same scale', 'Artifact · own color scale'];
  const mats = [r.ideal, r.observed, a.difference];
  await Promise.all(mats.map((m, i) => draw('cmp' + i, [heatmap(nu, t, m, keep, meta.limits[i], P)],
    layout(titles[i], 'Wavenumber (cm⁻¹)', 'Time after flash (µs)', P, { xaxis: spectralAxis(P), showlegend: false, shapes: [hline(0, P)] }), 'contour')));
}
async function renderDas() {
  const { meta, a } = await viewData('das');
  const r = state.result, P = palette(), nu = r.nu.data, t = r.t_us.data;
  await draw('d0', dasTraces(P), layout('DAS and offset · signed amplitudes', 'Wavenumber (cm⁻¹)', 'Amplitude at t = 0 (µOD)', P, { xaxis: spectralAxis(P), shapes: [hline(0, P)], ...dasLegend(P) }), 'spectral');
  await draw('d1', [heatmap(nu, t, a.residual, validKeep(), meta.residual_limit, P)], layout('Residual from 2exp + offset model', 'Wavenumber (cm⁻¹)', 'Time after flash (µs)', P, { xaxis: spectralAxis(P), showlegend: false, shapes: [hline(0, P)] }), 'contour');
  const colors = ['#dc6654', '#28876a', '#337fba', '#c58a24'];
  await draw('d2', meta.trace_index.map((j, k) => line(t, scale(r.observed.col(j)), `${number(nu[j])} cm⁻¹`, colors[k])), layout('Selected kinetic traces', 'Time (µs)', 'ΔA (µOD)', P), 'time');
  await draw('d3', [line(t, a.residual_rms_uOD.data, 'Residual RMS', P.sim)], layout(`Fit RMS = ${number(meta.fit_rms_uOD)} µOD · basis condition = ${number(meta.condition)}`, 'Time (µs)', 'Residual RMS (µOD)', P, { showlegend: false }), 'time');
}
async function renderOptical() {
  const { meta, a } = await viewData('optical');
  const r = state.result, P = palette(), nu = r.nu.data, t = r.t_us.data, j = channel();
  await draw('o0', [line(nu, a.s0.data, 'Ideal IR reference', P.ideal), line(nu, a.ref.data, 'Reference with selected effects', P.sim)],
    layout('Reference intensity', 'Wavenumber (cm⁻¹)', 'Relative single-beam units', P, { xaxis: spectralAxis(P) }), 'spectral');
  const laser = interpRow(a.laser_signal_spectrum, t, state.time).values;
  await draw('o1', [line(nu, a.folded_leak.data, 'Globar leakage', P.rp), line(nu, laser, `532 nm at ${number(state.time)} µs`, P.sim)],
    layout('Isolated optical readouts · actual amplitudes', 'Wavenumber (cm⁻¹)', 'Relative single-beam units', P, { xaxis: spectralAxis(P) }), 'spectral');
  const s0j = a.s0.data[j], ideal = r.ideal.col(j), sig = a.signal.col(j), refj = a.ref.data[j];
  await draw('o2', [line(t, Float64Array.from(ideal, v => s0j * (Math.pow(10, -v) - 1)), 'Ideal chemical ΔS', P.ideal), line(t, Float64Array.from(sig, v => v - refj), 'Total signal − reference', P.sim)],
    layout(`Intensity change · ${number(nu[j])} cm⁻¹`, 'Time after flash (µs)', 'Relative intensity change', P, { shapes: [vline(state.time, P, 'dot')] }), 'time');
  const jl = meta.laser_index;
  await draw('o3', [line(t, a.laser_signal_spectrum.col(jl), `Actinic at ${f2(nu[jl])} cm⁻¹`, P.sim)],
    layout('Flash pickup · acquired bin means', 'Time after flash (µs)', 'Isolated single-beam readout', P, { shapes: [vline(0, P, 'solid', P.zero, .7)] }), 'time');
}
async function renderInterferograms() {
  const { a } = await viewData('interferograms');
  const r = state.result, P = palette(), x = a.x_um.data, i = timeIndex(), t = r.t_us.data, nu = r.nu.data;
  const sig = a.signal_ifg.row(i), ref = a.reference_ifg.data;
  await draw('i0', [line(x, ref, 'Reference', P.ideal, { line: { color: P.ideal, width: 2 } }), line(x, sig, 'Selected time', P.sim, { line: { color: P.sim, width: 1 } })],
    layout('Reconstructed interferogram · near ZPD', 'OPD (µm)', 'IFG (relative units)', P, { xaxis: axis('OPD (µm)', P, { range: [-100, 100], autorange: false }) }));
  await draw('i1', [line(x, Float64Array.from(sig, (v, k) => v - ref[k]), 'ΔIFG', P.sim)],
    layout(`Interferogram change · ${f1(t[i])} µs`, 'OPD (µm)', 'ΔIFG (relative units)', P, { showlegend: false, xaxis: axis('OPD (µm)', P, { range: [-150, 150], autorange: false }) }));
  const colors = ['#dc6654', '#28876a', '#337fba'];
  await draw('i2', [0, 1, 2].map(k => line(t, a.displacement_nm.row(k), `OPD index ${[0, 1, 3][k]}`, colors[k])),
    layout('Mean mirror displacement · OPD = 2 × mirror motion', 'Time (µs)', 'Mirror displacement (nm)', P, { shapes: [vline(state.time, P, 'dot')] }), 'time');
  const s = a.signal.row(i), refs = a.ref.data;
  await draw('i3', [line(nu, Float64Array.from(s, (v, k) => v - refs[k]), 'ΔS', P.sim), line(nu, a.s0.data, 'S₀', P.gray, { opacity: .55 })],
    layout('Intensity domain · distinguish additive and gain artifacts', 'Wavenumber (cm⁻¹)', 'Relative single-beam units', P, { xaxis: spectralAxis(P) }), 'spectral');
}
async function renderWaveform() {
  const { meta, a } = await viewData('waveform');
  const r = state.result, P = palette(), t = r.t_us.data, nu = r.nu.data, j = channel();
  await draw('w0', [line(t, a.drive_nm.data, 'Declared mirror drive', P.sim)], layout('Drive hypothesis · not a measured displacement', 'Time after flash (µs)', 'Mirror displacement (nm)', P), 'time');
  await draw('w1', [line(t, scale(a.difference.col(j)), `Artifact at ${f2(nu[j])} cm⁻¹`, P.heat)],
    layout(`Carrier ${number(meta.frequency_hz)} Hz · ${f2(meta.cycles)} cycles in 3.38 ms; readout can generate harmonics`, 'Time after flash (µs)', 'Artifact ΔA (µOD)', P, { shapes: [vline(state.time, P, 'dot')] }), 'time');
}
async function renderOptics() {
  const { meta, a } = await viewData('optics');
  const r = state.result, P = palette(), m = state.meta;
  await draw('p0', [line(a.leak_nu.data, a.leak_source.data, 'Assumed out-of-band source', P.sim)], layout('Assumed out-of-band globar spectrum', 'True wavenumber (cm⁻¹)', 'Weighted spectral intensity', P, {
    xaxis: axis('True wavenumber (cm⁻¹)', P, { range: [6000, 0], autorange: false }),
    shapes: [{ type: 'rect', xref: 'x', yref: 'paper', x0: meta.fold_width, x1: 2 * meta.fold_width, y0: 0, y1: 1, fillcolor: P.ideal, opacity: .12, line: { width: 0 } }],
    annotations: [{ x: 1.5 * meta.fold_width, y: .97, xref: 'x', yref: 'paper', text: 'Desired physical band', showarrow: false, font: { size: 10, color: P.muted } }] }));
  await draw('p1', [line(a.fold_v.data, a.fold_alias.data, 'Alias map', P.heat, { showlegend: false }),
    { type: 'scatter', mode: 'markers', x: [meta.laser_cm1], y: [m.laser_alias_cm1], marker: { color: P.sim, size: 9 }, name: `${number(meta.laser_nm)} nm`, showlegend: false }],
    layout(`Alias map · ΔOPD = ${number(m.dx_um)} µm`, 'True wavenumber (cm⁻¹)', 'Displayed alias (cm⁻¹)', P, { showlegend: false,
      annotations: [{ x: meta.laser_cm1, y: m.laser_alias_cm1, ax: -90, ay: -40, text: `${number(meta.laser_nm)} nm → ${f2(m.laser_alias_cm1)} cm⁻¹<br>ONLY if OPD-modulated`, font: { size: 10, color: P.text }, arrowcolor: P.sim, showarrow: true }] }));
  await draw('p2', [line(r.nu.data, a.s0.data, 'In-band S₀', P.ideal), line(r.nu.data, a.folded_leak.data, 'Folded constant leak L', P.sim)],
    layout('Constant leakage changes the denominator', 'Wavenumber (cm⁻¹)', 'Relative single-beam units', P, { xaxis: spectralAxis(P) }), 'spectral');
  await draw('p3', [line(a.early_us.data, a.early_response.data, 'Optical pulse ⊗ assumed detector response', P.heat),
    Object.assign(line(a.bin_t.data, a.bin_response.data, `${number(meta.dt_us)} µs bin mean`, P.sim), { line: { color: P.sim, shape: 'hvh', width: 1.4 }, yaxis: 'y2' })],
    layout('Laser response · normalized area = 1', 'Time (µs)', 'Response (µs⁻¹)', P, { yaxis2: axis(`${number(meta.dt_us)} µs bin mean (µs⁻¹)`, P, { overlaying: 'y', side: 'right', showgrid: false }), margin: { l: 58, r: 58, t: 38, b: 44 } }));
  await draw('p4', [line(a.inset_ns.data, a.inset_response.data, 'Optical waveform only', P.rp)], layout('Optical waveform only (no detector response)', 'Time (ns)', 'Response (ns⁻¹)', P, { showlegend: false }));
}

// ---------- view switching ----------
const VIEWS = {
  explore: { label: 'Explore' }, compare: { label: 'Compare' }, das: { label: 'DAS and offset' },
  optical: { label: 'Optical contributions' }, diagnostics: { label: 'Diagnostics' },
};
function buildView() {
  const container = $('#plots');
  $('#diag-row').hidden = state.view !== 'diagnostics';
  if (state.view === 'explore') {
    cards(container, [{ id: 'contour', label: 'Contour of simulated ΔA versus wavenumber and time', tall: true }, { id: 'spectrum', label: 'Spectrum at the selected time', panel: 'spectrum' },
      { id: 'kinetics', label: 'Kinetics at the selected wavenumber', panel: 'kinetics' }, { id: 'das', label: 'Decay-associated spectra', panel: 'das' }], 'explore-grid');
    const sw = document.createElement('div');
    sw.className = 'panel-switch'; sw.setAttribute('role', 'tablist'); sw.setAttribute('aria-label', 'Linked panel');
    sw.innerHTML = [['spectrum', 'Spectrum'], ['kinetics', 'Kinetics'], ['das', 'DAS']].map(([k, l]) => `<button type="button" role="tab" data-panel="${k}">${l}</button>`).join('');
    container.firstElementChild.after(sw);
    $$('button', sw).forEach(b => b.addEventListener('click', () => showPanel(b.dataset.panel)));
    showPanel(state.panel, false);
  } else if (state.view === 'compare') cards(container, [0, 1, 2].map(i => ({ id: 'cmp' + i, label: ['Clean reference contour', 'Effects-applied contour', 'Artifact contour'][i], tall: true })), 'three');
  else if (state.view === 'das') cards(container, [0, 1, 2, 3].map(i => ({ id: 'd' + i, label: ['DAS', 'Residual contour', 'Selected kinetic traces', 'Residual RMS'][i] })));
  else if (state.view === 'optical') cards(container, [0, 1, 2, 3].map(i => ({ id: 'o' + i, label: ['Reference intensity', 'Isolated optical readouts', 'Intensity change', 'Flash pickup'][i] })));
  else if (state.diagnostic === 'interferograms') cards(container, [0, 1, 2, 3].map(i => ({ id: 'i' + i, label: ['Interferogram near ZPD', 'Interferogram change', 'Mirror displacement', 'Intensity domain change'][i] })));
  else if (state.diagnostic === 'waveform') cards(container, [0, 1].map(i => ({ id: 'w' + i, label: ['Declared mirror drive', 'Artifact at selected wavenumber'][i] })));
  else cards(container, [0, 1, 2, 3, 4].map(i => ({ id: 'p' + i, label: ['Out-of-band source', 'Alias map', 'Leakage and reference', 'Laser response', 'Optical waveform'][i] })));
  markTour();
}
function showPanel(panel, redraw = true) {
  state.panel = panel;
  $$('.panel-switch button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.panel === panel)));
  $$('#plots .plot-card[data-panel]').forEach(c => c.classList.toggle('shown', c.dataset.panel === panel));
  if (redraw) { const gd = document.getElementById('plot-' + panel); if (gd && gd.data) Plotly.Plots.resize(gd).then(() => positionOverlay(gd)); }
}
let rendering = Promise.resolve();
function render(rebuild = true) {
  if (!state.result) return;
  updateStatus();
  rendering = rendering.then(async () => {
    try {
      if (rebuild) buildView();
      if (state.view === 'explore') await renderExplore();
      else if (state.view === 'compare') await renderCompare();
      else if (state.view === 'das') await renderDas();
      else if (state.view === 'optical') await renderOptical();
      else if (state.diagnostic === 'interferograms') await renderInterferograms();
      else if (state.diagnostic === 'waveform') await renderWaveform();
      else await renderOptics();
    } catch (error) { if (error.message !== 'stale') { $('#warnings').textContent = String(error.message || error); console.error(error); } }
  });
  return rendering;
}
let selectionFrame = 0;
function selectionChanged() {
  updateSelectionLabel();
  if (!state.result) return;
  cancelAnimationFrame(selectionFrame);
  selectionFrame = requestAnimationFrame(() => {
    if (state.view === 'explore') { rendering = rendering.then(() => renderExplore(true)).catch(console.error); }
    else if (['optical', 'diagnostics'].includes(state.view)) render(false);
  });
}

// ---------- status ----------
function updateStatus() {
  const m = state.meta;
  const active = m.active.length ? 'Active: ' + m.active.join(', ') : 'Ideal simulated signal · all artifact sources off';
  $('#status').innerHTML = `<div>${escapeHtml(active)} &nbsp;|&nbsp; Artifact RMS: ${number(m.artifact_rms_full_uOD)} µOD (full band)</div>
    <div class="line2">2 exponentials + ${m.offset ? 'offset' : 'no offset'} · τ = ${number(m.taus[0])}, ${number(m.taus[1])} µs · fit RMS = ${number(m.fit_rms_uOD)} µOD${m.fit_mode.startsWith('free') ? ` · free fit${m.converged ? '' : ' (not converged)'}` : ''}</div>`;
  $('#warnings').textContent = m.warnings.concat(m.notes).join(' ');
  updateSelectionLabel();
}
function updateSelectionLabel() {
  if (!state.result) return;
  const r = state.result, j = channel(), i = timeIndex();
  $('#sel-label').textContent = `Selected: ${number(r.nu.data[j])} cm⁻¹ · ${number(state.time)} µs · ${isNative() ? 'native time bin' : 'linear time interpolation'}   |   Full band ${number(bandHigh())}–${number(bandLow())} cm⁻¹`;
  const wn = $('#sel-wn'), tm = $('#sel-time');
  if (document.activeElement !== wn) wn.value = number(state.wn);
  if (document.activeElement !== tm) tm.value = number(state.time);
  $('#time-slider').value = i;
  $('#wn-slider').value = j; // left = high wavenumber, matching the descending plots
  $('#time-slider').setAttribute('aria-valuetext', `${number(r.t_us.data[i])} µs`);
  $('#wn-slider').setAttribute('aria-valuetext', `${number(r.nu.data[j])} cm⁻¹`);
}

// ---------- contour / plot selection overlays ----------
function plotArea(gd) {
  const drag = gd.querySelector('.nsewdrag');
  if (!drag) return null;
  const a = drag.getBoundingClientRect(), c = gd.parentElement.getBoundingClientRect();
  return { left: a.left - c.left, top: a.top - c.top, width: a.width, height: a.height };
}
function positionOverlay(gd) {
  const ov = gd._fsOverlay; if (!ov) return;
  const box = plotArea(gd);
  ov.hidden = state.mode !== 'select' || !box;
  if (!box) return;
  Object.assign(ov.style, { left: box.left + 'px', top: box.top + 'px', width: box.width + 'px', height: box.height + 'px' });
}
function detachSelector(gd) { if (gd._fsOverlay) { gd._fsOverlay.remove(); gd._fsOverlay = null; } }
function attachSelector(gd, kind) {
  if (!gd._fsOverlay) {
    const ov = document.createElement('div');
    ov.className = 'overlay';
    ov.setAttribute('aria-hidden', 'true');
    gd.parentElement.appendChild(ov);
    gd._fsOverlay = ov;
    bindGestures(ov, gd);
    gd.on('plotly_afterplot', () => positionOverlay(gd));
  }
  gd._fsKind = kind;
  positionOverlay(gd);
}
function pick(gd, clientX, clientY) {
  const ov = gd._fsOverlay, rect = ov.getBoundingClientRect(), fl = gd._fullLayout;
  const px = Math.min(Math.max(clientX - rect.left, 0), rect.width), py = Math.min(Math.max(clientY - rect.top, 0), rect.height);
  const xr = fl.xaxis.range, yr = fl.yaxis.range;
  const x = xr[0] + (px / rect.width) * (xr[1] - xr[0]);
  const y = yr[1] - (py / rect.height) * (yr[1] - yr[0]);
  const r = state.result, kind = gd._fsKind;
  if (kind === 'contour' || kind === 'spectral') state.wn = r.nu.data[nearest(r.nu.data, x)];
  if (kind === 'contour') state.time = r.t_us.data[nearest(r.t_us.data, y)];
  if (kind === 'time') state.time = r.t_us.data[nearest(r.t_us.data, x)];
  selectionChanged();
}
function bindGestures(ov, gd) {
  // Mouse/pen: press selects, drag moves the crosshair.
  ov.addEventListener('pointerdown', e => {
    if (e.pointerType === 'touch') return;
    ov.setPointerCapture(e.pointerId); ov._drag = true; pick(gd, e.clientX, e.clientY);
  });
  ov.addEventListener('pointermove', e => { if (e.pointerType !== 'touch' && ov._drag) pick(gd, e.clientX, e.clientY); });
  ov.addEventListener('pointerup', e => { ov._drag = false; });
  // Touch: tap selects; press-and-hold then drag moves the crosshair; a swipe scrolls the page.
  let start = null, hold = null, dragging = false;
  ov.addEventListener('touchstart', e => {
    if (e.touches.length !== 1) { clearTimeout(hold); start = null; return; }
    const tch = e.touches[0]; start = { x: tch.clientX, y: tch.clientY, t: performance.now() }; dragging = false;
    clearTimeout(hold);
    hold = setTimeout(() => { dragging = true; ov.classList.add('dragging'); if (navigator.vibrate) navigator.vibrate(8); pick(gd, start.x, start.y); }, 280);
  }, { passive: true });
  ov.addEventListener('touchmove', e => {
    if (!start) return;
    const tch = e.touches[0];
    if (dragging) { e.preventDefault(); pick(gd, tch.clientX, tch.clientY); return; }
    if (Math.hypot(tch.clientX - start.x, tch.clientY - start.y) > 9) { clearTimeout(hold); start = null; }
  }, { passive: false });
  ov.addEventListener('touchend', e => {
    clearTimeout(hold);
    if (start && !dragging && performance.now() - start.t < 600) { e.preventDefault(); pick(gd, start.x, start.y); }
    dragging = false; start = null; ov.classList.remove('dragging');
  });
  ov.addEventListener('touchcancel', () => { clearTimeout(hold); dragging = false; start = null; ov.classList.remove('dragging'); });
}
function setMode(mode) {
  state.mode = mode;
  $$('.mode-switch button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  $('#mode-hint').textContent = mode === 'select'
    ? (touchFirst ? 'Tap a plot to select. Press and hold, then drag, to move the crosshair. Swipe to scroll.' : 'Click or drag on a plot to select time and wavenumber.')
    : 'Zoom / pan: drag to zoom, double-tap or Reset view to restore. Selection is paused.';
  render(false);
}

// ---------- guided tour (app.MainWindow.advance_tour, with a coach panel) ----------
// The controls applied at each step equal the desktop sequence; Back replays the
// same forward sequence from the tour defaults, so every step is reproducible.
const TOUR = CONFIG.tour; // generated from tour.py, shared with the desktop application
const GUIDE = TOUR.steps;
const EXPLORE_CARDS = ['contour', 'spectrum', 'kinetics', 'das'];
function setHint(html) { $('#hint').innerHTML = html; const b = $('#hint-tour'); if (b) b.addEventListener('click', () => gotoTourStep(0)); }
const DEFAULT_HINT = (touchFirst ? 'Switch a source on below. Tap the contour to choose a spectrum and kinetic trace.' : 'Switch a source on below. Click or drag the contour to choose a spectrum and kinetic trace.')
  + ' New users can start with the <button type="button" class="linklike" id="hint-tour">guided tour</button>.';
function tourDefaults() {
  for (const key of Object.keys(state.controls)) if (key in CONFIG.settings_defaults) setControl(key, CONFIG.settings_defaults[key]);
  Object.entries(TOUR.base).forEach(([key, v]) => setControl(key, v));
}
function applyTourStep(k) {
  tourDefaults();
  for (let i = 0; i <= k; i++) { TOUR.off.forEach(key => setControl(key, false)); Object.entries(GUIDE[i].controls).forEach(([key, v]) => setControl(key, v)); }
  state.wn = TOUR.wavenumber; state.time = GUIDE[k].time_us;
}
function cardView(target) { return EXPLORE_CARDS.includes(target) ? 'explore' : /^o\d$/.test(target) ? 'optical' : null; }
function tourTarget(target) {
  if (target.startsWith('source:')) return $(`.source-toggle[data-setting="${target.slice(7)}"]`);
  return $(`#plots .plot-card[data-card="${target}"]`);
}
function markTour() {
  $$('[data-tour-mark]').forEach(el => { el.removeAttribute('data-tour-mark'); el.classList.remove('tour-mark'); });
  const T = state.tour; if (T.step < 0) return;
  const look = GUIDE[T.step].look;
  look.forEach((item, n) => {
    const el = tourTarget(item.target);
    if (el) { el.dataset.tourMark = n + 1; el.classList.add('tour-mark'); }
    const view = cardView(item.target);
    if (view && view !== state.view) { const tab = $(`.view-tabs button[data-view="${view}"]`); if (tab && !tab.dataset.tourMark) tab.dataset.tourMark = n + 1; }
  });
  $$('.panel-switch button').forEach(b => { const n = look.findIndex(item => item.target === b.dataset.panel); if (n >= 0) b.dataset.tourMark = n + 1; });
}
function pulse(el) {
  $$('.tour-focus').forEach(x => x.classList.remove('tour-focus'));
  if (el) el.classList.add('tour-focus');
}
async function focusTourTarget(target) {
  const view = cardView(target);
  if (view && view !== state.view) { state.view = view; syncTabs(); await render(); }
  const el = tourTarget(target);
  if (!el) return;
  const sw = $('.panel-switch');
  if (el.dataset.panel && sw && getComputedStyle(sw).display !== 'none') showPanel(el.dataset.panel);
  if (window.innerWidth < 1100) collapseCoach(true);
  el.scrollIntoView({ behavior: 'auto', block: 'center' });
  pulse(el);
}
function collapseCoach(collapsed) {
  $('#coach').classList.toggle('collapsed', collapsed);
  $('#coach-min').setAttribute('aria-expanded', String(!collapsed));
  $('#coach-min').textContent = collapsed ? 'Show' : 'Hide';
}
function renderCoach() {
  const T = state.tour, active = T.step >= 0;
  $('#coach').hidden = !active; document.body.classList.toggle('touring', active);
  $('#tour-button').textContent = active ? 'End tour' : 'Guided tour';
  $('#tour-button').setAttribute('aria-pressed', String(active));
  if (!active) { markTour(); return; }
  const g = GUIDE[T.step], n = GUIDE.length;
  $('#coach-step').textContent = `Guided tour · step ${T.step + 1} of ${n}`;
  $('#coach-title').textContent = g.title;
  $('#coach-changed').textContent = g.changed;
  $('#coach-look').innerHTML = g.look.map((item, i) => `<li><button type="button" class="look" data-target="${item.target}"><span class="num">${i + 1}</span><span>${escapeHtml(item.text)}</span></button></li>`).join('');
  $$('#coach-look .look').forEach(b => b.addEventListener('click', () => focusTourTarget(b.dataset.target)));
  $('#coach-back').disabled = T.step === 0;
  $('#coach-next').textContent = `${g.next} →`;
  setHint(`Guided tour, step ${T.step + 1} of ${n}: read the tour panel, look at the numbered plots, then press “${escapeHtml(g.next)}”.`);
  markTour();
}
let tourBusy = false;
async function gotoTourStep(k) {
  const T = state.tour;
  if (!state.ready || k < 0 || tourBusy || state.exporting) return;
  if (k >= GUIDE.length) return finishTour(true);
  tourBusy = true; lockWorkspace(true);
  try {
    await settleWorkspace();
    if (T.step < 0) {
      const saved = { controls: Object.assign({}, state.controls), wn: state.wn, time: state.time,
        view: state.view, diagnostic: state.diagnostic, panel: state.panel,
        result: state.result, meta: state.meta, cache: state.cache, committedControls: state.committedControls };
      await engine.call('save-session', { resultId: saved.meta.result_id }); T.saved = saved;
    }
    T.step = k; applyTourStep(k); syncControls(); openControls(false, false);
    state.view = 'explore'; state.panel = 'spectrum'; syncTabs(); renderCoach(); collapseCoach(false);
    await recompute(false);
    if (GUIDE[k].alias && state.meta) { state.wn = state.meta.laser_alias_cm1; selectionChanged(); }
    markTour();
    (window.innerWidth < 1100 ? $('#plots') : $('.views')).scrollIntoView({ behavior: 'auto', block: 'start' });
  } catch (error) { $('#warnings').textContent = `Tour could not advance: ${error.message}`; }
  finally { tourBusy = false; lockWorkspace(false); }
  $('#coach-title').focus({ preventScroll: true });
}
async function finishTour(completed) {
  const T = state.tour, s = T.saved;
  if (T.step < 0 || !s || tourBusy || state.exporting) return;
  tourBusy = true; lockWorkspace(true);
  try {
    clearTimeout(timer); timer = null;
    if (state.computePromise) await state.computePromise;
    await rendering;
    const restored = await engine.call('restore-session');
    if (restored.resultId !== s.meta.result_id) throw new Error('Tour snapshot mismatch');
    state.controls = s.controls; state.wn = s.wn; state.time = s.time;
    state.result = s.result; state.meta = s.meta; state.cache = s.cache;
    state.committedControls = s.committedControls; state.lastError = null; state.resultSeq = ++state.seq;
    T.step = -1; T.saved = null;
    syncControls(); state.view = s.view; state.diagnostic = s.diagnostic; state.panel = s.panel; syncTabs(); renderCoach();
    setHint((completed ? 'Tour finished. ' : 'Tour ended. ') + 'Your previous controls, selections and exact fit are restored. '
      + '<a href="demonstrations.html">Demonstrations</a> has fixed lessons on harmonics and coaddition; <a href="theory.html">Theory</a> has the derivations. <button type="button" class="linklike" id="hint-tour">Restart the tour</button>.');
    await render(); setEngine('ready', 'Ready · previous fit restored');
  } catch (error) { $('#warnings').textContent = `Tour restore failed: ${error.message}`; }
  finally { tourBusy = false; lockWorkspace(false); }
  $('#tour-button').focus({ preventScroll: true });
}
function advanceTour() { return state.tour.step < 0 ? gotoTourStep(0) : finishTour(false); }
function resetIdeal() {
  ['wobble', 'globar', 'laser', 'electrical', 'zpd'].forEach(k => setControl(k, false));
  syncControls(); $('#controls').scrollTop = 0; recompute(false);
}

// ---------- export ----------
async function exportRun() {
  if (!state.result || state.exporting || tourBusy) return;
  state.exporting = true; lockWorkspace(true);
  const button = $('#export-button'); button.disabled = true;
  setEngine('busy', 'Preparing export…');
  try {
    await settleWorkspace();
    const resultId = state.meta.result_id;
    const figures = {};
    const theme = FringeScopeTheme.get();
    for (const gd of $$('#plots .plot')) {
      if (!gd.data || !gd.offsetWidth) continue;
      const url = await Plotly.toImage(gd, { format: 'png', scale: 2, width: gd.offsetWidth, height: gd.offsetHeight });
      const bin = atob(url.split(',')[1]); const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      figures[`screen_${theme}_${gd.id.replace('plot-', '')}.png`] = bytes;
    }
    const now = new Date(), p = (n, w = 2) => String(n).padStart(w, '0');
    const stamp = `${now.getFullYear()}${p(now.getMonth() + 1)}${p(now.getDate())}_${p(now.getHours())}${p(now.getMinutes())}${p(now.getSeconds())}_${p(now.getMilliseconds() * 1000, 6)}`;
    const info = { expected_result_id: resultId, stamp, wavenumber: state.wn, time_us: state.time, version: CONFIG.version, theme, view: state.view === 'diagnostics' ? `diagnostics:${state.diagnostic}` : state.view, kernel_sha256: CONFIG.manifest.kernel };
    const value = await engine.call('export', { info, figures }, Object.values(figures).map(b => b.buffer));
    const url = URL.createObjectURL(new Blob([value.bytes], { type: 'application/zip' }));
    const a = document.createElement('a'); a.href = url; a.download = value.name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    setEngine('ready', `Exported ${value.name}`);
  } catch (error) { $('#warnings').textContent = `Export failed: ${error.message}`; setEngine('ready', 'Ready'); }
  finally { state.exporting = false; lockWorkspace(false); button.disabled = false; button.focus({ preventScroll: true }); }
}

// ---------- wiring ----------
function syncTabs() {
  $$('.view-tabs button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.view === state.view)));
  $('#diagnostic').value = state.diagnostic;
}
function openControls(open, focus = true) {
  const panel = $('#controls'), scrim = $('#scrim');
  panel.classList.toggle('open', open); scrim.hidden = !open;
  $('#controls-button').setAttribute('aria-expanded', String(open));
  if (open && focus) $('#controls-close').focus();
}
function init() {
  buildControls();
  $('#sources').innerHTML = SOURCES.map(([key, label, setting]) => `<button type="button" class="source-toggle" data-setting="${setting}" aria-pressed="false">${escapeHtml(label)}<span class="state">Off</span></button>`).join('');
  $$('.source-toggle').forEach(b => b.addEventListener('click', () => {
    const k = b.dataset.setting; state.controls[k] = !state.controls[k];
    syncControls(); sourceToggled(k, state.controls[k]); clearTimeout(timer); recompute(false);
  }));
  $('#view-tabs').innerHTML = Object.entries(VIEWS).map(([k, v]) => `<button type="button" role="tab" data-view="${k}" aria-selected="false">${v.label}</button>`).join('');
  $$('.view-tabs button').forEach(b => b.addEventListener('click', () => { state.view = b.dataset.view; syncTabs(); render(); }));
  $('#diagnostic').addEventListener('change', e => { state.diagnostic = e.target.value; render(); });
  $$('.mode-switch button').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
  $('#reset-view').addEventListener('click', () => { state.uirev += 1; if (state.result) state.result._contour = null; render(false); });
  $('#reset-ideal').addEventListener('click', resetIdeal);
  $('#tour-button').addEventListener('click', advanceTour);
  $('#export-button').addEventListener('click', exportRun);
  $('#controls-button').addEventListener('click', () => openControls(true));
  $('#controls-close').addEventListener('click', () => openControls(false));
  $('#scrim').addEventListener('click', () => openControls(false));
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if ($('#controls').classList.contains('open')) openControls(false);
    else if (state.tour.step >= 0 && !e.target.closest('input, select')) finishTour(false);
  });
  $('#sel-wn').addEventListener('change', e => { const v = parseFloat(e.target.value); if (Number.isFinite(v)) state.wn = Math.min(bandHigh(), Math.max(bandLow(), v)); selectionChanged(); });
  $('#sel-time').addEventListener('change', e => { const v = parseFloat(e.target.value); if (Number.isFinite(v)) state.time = Math.min(SPEC.selection.time_max, Math.max(SPEC.selection.time_min, v)); selectionChanged(); });
  $('#time-slider').addEventListener('input', e => { if (state.result) { state.time = state.result.t_us.data[+e.target.value]; selectionChanged(); } });
  $('#wn-slider').addEventListener('input', e => { if (state.result) { state.wn = state.result.nu.data[+e.target.value]; selectionChanged(); } });
  document.addEventListener('fringescope-theme', () => { if (state.result) { state.result._contour = null; render(false); } });
  window.addEventListener('resize', () => $$('#plots .plot').forEach(gd => positionOverlay(gd)));
  setHint(DEFAULT_HINT); setMode('select'); syncTabs();
  $('#coach-next').addEventListener('click', () => gotoTourStep(state.tour.step + 1));
  $('#coach-back').addEventListener('click', () => gotoTourStep(state.tour.step - 1));
  $('#coach-exit').addEventListener('click', () => finishTour(false));
  $('#coach-min').addEventListener('click', () => collapseCoach(!$('#coach').classList.contains('collapsed')));
  loading.show();
  engine.start().then(async () => {
    loading.step(3); state.ready = true;
    await recompute(false);
    loading.hide();
    const m = /^#tour(?:-(\d))?$/.exec(location.hash);
    if (m) gotoTourStep(m[1] ? Math.min(GUIDE.length, Math.max(1, +m[1])) - 1 : 0);
  }).catch(error => loading.fail(error.message));
}
document.addEventListener('DOMContentLoaded', init);
