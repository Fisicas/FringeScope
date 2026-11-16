"""Regenerate the two synthetic example slices without overwriting prior outputs."""
from pathlib import Path
import argparse
from dataclasses import asdict
import hashlib
import json
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'desktop'))
import numpy as np
import scipy
from ftir_sim import Settings, simulate


def generate(output):
    p = Settings(seed=20261114)
    r = simulate(p)
    t, nu = r['t_us'], r['nu']
    spectrum = np.array([np.interp(100., t, r['ideal'][:, j]) for j in range(len(nu))])
    j = int(np.argmin(abs(nu - 1697.)))
    output.mkdir(parents=True, exist_ok=False)
    np.savetxt(output/'synthetic_ideal_spectrum_100us.csv', np.column_stack([nu, spectrum]), delimiter=',', header='wavenumber_cm-1,DeltaA_OD', comments='')
    np.savetxt(output/'synthetic_ideal_kinetics.csv', np.column_stack([t, r['ideal'][:, j]]), delimiter=',', header='time_us,DeltaA_OD', comments='')
    meta = dict(version='0.11.0', signal='synthetic analytic PSI-inspired difference model', settings=asdict(p),
                spectrum_time_us=100., spectrum_processing='Linear interpolation between native 99 and 105 us bin centers; no smoothing/baseline correction/normalization',
                kinetic_requested_cm1=1697., kinetic_actual_cm1=float(nu[j]), kinetic_processing='Nearest native channel, no spectral interpolation',
                wavenumber_order='descending', amplitude_units='OD', matrix_axis_order=['time', 'wavenumber'], matrix_shape=list(r['ideal'].shape),
                native_time_us=[float(t[0]),float(t[-1])], native_time_step_us=float(p.dt_us), native_wavenumber_cm1=[float(nu[0]),float(nu[-1])],
                generator='tools/generate_examples.py', environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
                scientific_inputs_sha256={name:hashlib.sha256((ROOT/'desktop'/name).read_bytes()).hexdigest() for name in ['ftir_sim.py','synthetic_model.json','waveform_defaults.json']})
    (output/'settings.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8',newline='\n')
    return meta


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(generate(parser.parse_args().output),indent=2))
