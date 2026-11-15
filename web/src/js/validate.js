// Browser-versus-native parity check for FringeScope Web.
const CONFIG = JSON.parse(document.getElementById('fs-config').textContent);
// Fixed-basis projections are deterministic linear algebra: round-off only.
// Free refits stop an iterative optimizer; ulp-level differences in its path move
// lifetimes by ~1e-9 (relative) and DAS by ~1e-9 OD, so their DAS tolerance is wider.
const TOL = { delta: 1e-10, das: 1e-10, dasFree: 1e-8, tau: 1e-6 };
const $ = s => document.querySelector(s);
let worker, id = 0; const pending = new Map();

function call(cmd, payload = {}) {
  const n = ++id;
  return new Promise((resolve, reject) => { pending.set(n, { resolve, reject }); worker.postMessage(Object.assign({ id: n, cmd }, payload)); });
}
function startWorker() {
  worker = new Worker(`js/worker.js?v=${CONFIG.manifest.build}`, { type: 'module' });
  worker.onmessage = e => {
    const m = e.data;
    if (m.type === 'progress') { $('#progress').textContent = m.detail + '…'; return; }
    const p = pending.get(m.id); if (!p) return; pending.delete(m.id);
    m.ok ? p.resolve(m.value) : p.reject(new Error(m.error));
  };
  return call('init', { base: new URL('.', location.href).href, manifest: CONFIG.manifest });
}
function maxDiff(a, b) {
  let worst = 0, mask = true;
  for (let i = 0; i < b.length; i++) {
    const x = a[i], y = b[i];
    const fx = Number.isFinite(x), fy = y !== null;
    if (fx !== fy) { mask = false; continue; }
    if (fx) worst = Math.max(worst, Math.abs(x - y));
  }
  return { worst, mask };
}
function fmt(v) { return v === 0 ? '0' : v.toExponential(2); }

async function run() {
  $('#run').disabled = true;
  const fixtures = await (await fetch(`parity_fixtures.json?v=${CONFIG.manifest.build}`)).json();
  const init = await startWorker();
  const rt = init.runtime;
  $('#env').textContent = `Browser: ${navigator.userAgent}\nScreen: ${screen.width}×${screen.height} CSS px, devicePixelRatio ${devicePixelRatio}\n` +
    `Browser runtime: Pyodide ${rt.pyodide}, Python ${rt.python}, NumPy ${rt.numpy}, SciPy ${rt.scipy}, build ${rt.build}\n` +
    `Native fixtures: ${fixtures.platform}, Python ${fixtures.python}, NumPy ${fixtures.numpy}, SciPy ${fixtures.scipy}`;
  const body = $('#results tbody'); $('#results').hidden = false; body.innerHTML = '';
  let passed = 0;
  for (const [k, sc] of fixtures.scenarios.entries()) {
    $('#progress').textContent = `Scenario ${k + 1} of ${fixtures.scenarios.length}: ${sc.name}`;
    const t0 = performance.now();
    const value = await call('compute', { controls: sc.controls, free: sc.free });
    const seconds = (performance.now() - t0) / 1000;
    const A = value.arrays, cols = A.observed.shape[1], rowsN = A.observed.shape[0];
    const obs = A.observed.data, rec = A.reconstruction.data, das = A.das.data;
    let worst = 0, mask = true, dasWorst = 0;
    sc.rows.forEach((i, r) => { const d = maxDiff(obs.subarray(i * cols, (i + 1) * cols), sc.observed_rows[r]); worst = Math.max(worst, d.worst); mask = mask && d.mask; });
    sc.cols.forEach((j, c) => {
      const hasRec = c < sc.reconstruction_cols.length;
      const col = new Float64Array(rowsN), rcol = new Float64Array(rowsN);
      for (let i = 0; i < rowsN; i++) { col[i] = obs[i * cols + j]; rcol[i] = rec[i * cols + j]; }
      const d = maxDiff(col, sc.observed_cols[c]); worst = Math.max(worst, d.worst); mask = mask && d.mask;
      if (hasRec) { const e = maxDiff(rcol, sc.reconstruction_cols[c]); worst = Math.max(worst, e.worst); mask = mask && e.mask; }
    });
    sc.das.forEach((row, r) => { const d = maxDiff(das.subarray(r * cols, (r + 1) * cols), row); dasWorst = Math.max(dasWorst, d.worst); mask = mask && d.mask; });
    let nanCount = 0;
    for (let i = 0; i < obs.length; i++) if (!Number.isFinite(obs[i])) nanCount++;
    const masked = [];
    for (let j = 0; j < cols; j++) { let all = true; for (let i = 0; i < rowsN; i++) if (Number.isFinite(obs[i * cols + j])) { all = false; break; } if (all) masked.push(j); }
    if (nanCount !== sc.nan_count || masked.length !== sc.nan_columns.length || masked.some((v, i) => v !== sc.nan_columns[i])) mask = false;
    const tauRel = Math.max(...value.meta.taus.map((v, i) => Math.abs(v - sc.taus[i]) / Math.abs(sc.taus[i])));
    const ok = mask && worst <= TOL.delta && dasWorst <= (sc.free ? TOL.dasFree : TOL.das) && tauRel <= TOL.tau;
    if (ok) passed++;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${sc.name}</td><td>${mask ? 'identical' : '<b>differs</b>'}</td><td>${fmt(worst)}</td><td>${fmt(dasWorst)}</td><td>${fmt(tauRel)}</td><td>${seconds.toFixed(2)}</td><td>${ok ? '✔ pass' : '<b>✘ check</b>'}</td>`;
    body.appendChild(tr);
  }
  const all = passed === fixtures.scenarios.length;
  $('#summary').innerHTML = `<div class="notice"><strong>${passed} of ${fixtures.scenarios.length} scenarios passed.</strong> ${all ? 'The browser engine reproduces the native desktop results within the stated tolerances on this device.' : 'Some scenarios exceed the stated tolerances; see the table. Please report the environment text below.'}</div>`;
  $('#progress').textContent = 'Done.';
  window.FRINGESCOPE_PARITY = { passed, total: fixtures.scenarios.length, rows: [...body.querySelectorAll('tr')].map(r => [...r.children].map(c => c.textContent)) };
}
document.getElementById('run').addEventListener('click', () => run().catch(e => { $('#progress').textContent = 'Failed: ' + e.message; $('#run').disabled = false; }));
