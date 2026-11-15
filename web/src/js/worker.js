// FringeScope Web compute worker (module worker).
// Runs the repository's own ftir_sim.py under a pinned Pyodide runtime. The
// interface thread never blocks on NumPy/SciPy work.
const PYODIDE_VERSION = '314.0.8';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const HOME = '/home/pyodide/fringescope';

let py = null, kernel = null, runtime = null, ready = null;

function progress(stage, detail) { self.postMessage({ type: 'progress', stage, detail }); }

async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function init(base, manifest) {
  progress(0, 'Downloading the Python runtime');
  const { loadPyodide } = await import(PYODIDE_URL + 'pyodide.mjs');
  py = await loadPyodide({ indexURL: PYODIDE_URL });
  progress(1, 'Loading NumPy and SciPy');
  await py.loadPackage(['numpy', 'scipy'], { messageCallback: () => {}, errorCallback: m => console.warn(m) });
  progress(2, 'Starting the FringeScope engine');
  py.FS.mkdirTree(HOME);
  const hashes = {};
  for (const [name, expected] of Object.entries(manifest.kernel)) {
    const response = await fetch(`${base}py/${name}?v=${manifest.build}`, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Could not load ${name} (${response.status})`);
    const bytes = new Uint8Array(await response.arrayBuffer());
    const digest = await sha256(bytes);
    // Never combine a stale cached model/settings file with a new engine.
    if (digest !== expected) throw new Error(`${name} does not match this build (cached copy?). Reload the page.`);
    hashes[name] = digest;
    py.FS.writeFile(`${HOME}/${name}`, bytes);
  }
  py.runPython(`import sys\nsys.path.insert(0, '${HOME}')\nimport web_kernel`);
  kernel = py.pyimport('web_kernel');
  runtime = Object.assign({ pyodide: PYODIDE_VERSION, build: manifest.build }, JSON.parse(kernel.runtime_versions()));
  if (!runtime.public_mode) throw new Error('release_config.json must declare public_mode for the web edition.');
  return { runtime, hashes };
}

function unpack(tuple) {
  // (meta_json, {name: ndarray float64}) -> plain JS with transferable buffers.
  const meta = JSON.parse(tuple.get(0));
  const dict = tuple.get(1);
  const arrays = {}, transfer = [];
  for (const key of dict.keys()) {
    const proxy = dict.get(key);
    const buffer = proxy.getBuffer('f64');
    try {
      const data = buffer.data.slice();
      arrays[key] = { shape: buffer.shape.slice(), data };
      transfer.push(data.buffer);
    } finally { buffer.release(); proxy.destroy(); }
  }
  dict.destroy(); tuple.destroy();
  return { meta, arrays, transfer };
}

async function handle(msg) {
  const { cmd } = msg;
  if (cmd === 'init') {
    ready = ready || init(msg.base, msg.manifest);
    return { value: await ready };
  }
  await ready;
  if (cmd === 'compute') {
    const out = unpack(kernel.compute(JSON.stringify(msg.controls), !!msg.free));
    return { value: { meta: out.meta, arrays: out.arrays }, transfer: out.transfer };
  }
  if (cmd === 'save-session') return { value: { resultId: kernel.save_session(msg.resultId) } };
  if (cmd === 'restore-session') return { value: { resultId: kernel.restore_session() } };
  if (cmd === 'view') {
    if (msg.resultId !== undefined) kernel.check_result(msg.resultId);
    const out = unpack(kernel.view(msg.name, JSON.stringify(msg.params || {})));
    return { value: { meta: out.meta, arrays: out.arrays }, transfer: out.transfer };
  }
  if (cmd === 'export') {
    kernel.check_result(msg.info.expected_result_id);
    const dir = '/tmp/fringescope_figures';
    try { py.FS.mkdirTree(dir); for (const f of py.FS.readdir(dir)) if (!f.startsWith('.')) py.FS.unlink(`${dir}/${f}`); } catch (e) { /* new folder */ }
    for (const [name, bytes] of Object.entries(msg.figures || {})) py.FS.writeFile(`${dir}/${name.replace(/[^A-Za-z0-9_.-]/g, '_')}`, bytes);
    const info = Object.assign({}, msg.info, { runtime });
    const result = kernel.export_zip(JSON.stringify(info), dir);
    const name = result.get(0);
    const proxy = result.get(1);
    const bytes = proxy.toJs();
    proxy.destroy(); result.destroy();
    return { value: { name, bytes }, transfer: [bytes.buffer] };
  }
  throw new Error(`Unknown command ${cmd}`);
}

self.onmessage = async (event) => {
  const msg = event.data;
  try {
    const { value, transfer } = await handle(msg);
    self.postMessage({ type: 'result', id: msg.id, ok: true, value }, transfer || []);
  } catch (error) {
    self.postMessage({ type: 'result', id: msg.id, ok: false, error: String(error && error.message || error) });
  }
};
