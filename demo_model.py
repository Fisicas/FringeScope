"""Original, deterministic TRSS lessons inspired by Roedig & Siebert (1999).

Independent exact uniform-displacement calculation, not a reproduction of the
paper's data and not the production fourth-order OPD-dependent shift engine.
Units: physical wavenumber cm^-1, mirror nm, OPD cm, acquisition time us, OD.
"""
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
import numpy as np
from ftir_sim import Settings, build_truth


@dataclass(frozen=True)
class DemoSettings:
    frequency_hz: float = 840.
    amplitude_nm: float = 2.
    common_bias_nm: float = 25.
    phase_deg: float = -100.
    dt_us: float = 6.
    duration_us: float = 3378.
    selected_cm1: float = 1697.
    spectrum_us: float = 100.
    electrical_fraction: float = .0002
    repetition_hz: float = 10.
    detuned_repetition_hz: float = 10.01
    demonstration_coadds: int = 8
    harmonic_samples: int = 2048


REFERENCE = {
    'citation': 'Rödig, C.; Siebert, F. Applied Spectroscopy 53, 893–901 (1999)',
    'doi': 'https://doi.org/10.1366/0003702991947595',
    'scope': 'Figs. 3–9; phase-correlated averaging on printed pp. 897–898. Original simulations, not digitized data.',
    'paper_drive': 'Imposed ±4 nm at 50 Hz; distinct from this illustrative 2 nm at 840 Hz.',
}


def drive(time_us, p, phases=(0.,)):
    """Mirror displacement about the common bias; no gating in baseline lessons."""
    theta = 2*np.pi*p.frequency_hz*np.asarray(time_us)*1e-6 + np.deg2rad(p.phase_deg)
    return p.amplitude_nm*np.sin(theta[:, None]+np.asarray(phases)[None, :])


def averaged_intensity(spectrum, nu, drive_nm, bias_nm):
    """Real spectral readout after coadding detector records, for uniform OPD phase.

    At the native odd-zone grid cos(2*pi*nu*x) = cos(2*pi*q*x),
    q = 2B-nu. A uniform shift multiplies the complex coefficient by
    exp(-i*2*pi*nu*delta_OPD); its fixed-real readout is the cosine below.
    DC/Nyquist endpoint coefficients are real as required by irfft/rfft.
    """
    motion = np.asarray(drive_nm, float)
    if motion.ndim == 1: motion = motion[:, None]
    phase = 2*np.pi*np.asarray(nu)[None, None, :]*2e-7*(bias_nm+motion[:, :, None])
    return np.asarray(spectrum)*np.cos(phase).mean(axis=1)


def absorbance(signal, reference):
    """No floors: invalid ratios remain NaN and are identified by a mask."""
    reference = np.broadcast_to(reference, np.shape(signal))
    valid = (signal > 0) & (reference > 0)
    out = np.full(np.shape(signal), np.nan)
    out[valid] = -np.log10(np.asarray(signal)[valid]/reference[valid])
    return out


def interferogram(spectrum, nu, x_cm, derivative=0):
    """Continuous analytic AC interferogram, using real-FFT endpoint weights.

    Only the interferometrically modulated component is represented, not total
    detector DC. Continuous curves are analytic evaluations, not resampled data.
    """
    n = 2*(len(nu)-1)
    weights = np.full(len(nu), 2./n); weights[[0,-1]] = 1./n
    k = 2*np.pi*np.asarray(nu)
    phase = np.asarray(x_cm)[..., None]*k
    return (np.cos(phase+derivative*np.pi/2)*k**derivative)@(np.asarray(spectrum)*weights)


def shot_phases(count, frequency_hz, repetition_hz=None, paired=False):
    if count < 1: raise ValueError('At least one record is required')
    if paired: return np.pi*(np.arange(count) % 2)
    if repetition_hz is None or repetition_hz <= 0: raise ValueError('Positive repetition rate required')
    return np.remainder(2*np.pi*frequency_hz*np.arange(count)/repetition_hz, 2*np.pi)


def coherence(phases, order):
    """Intensity harmonic transfer |mean exp(i*m*phase)|, not OD attenuation."""
    return float(abs(np.exp(1j*order*np.asarray(phases)).mean()))


def harmonic_amplitudes(values, count=4):
    """One exact cycle, uniformly sampled without endpoint; exclude DC only."""
    values = np.asarray(values)
    return 2*abs(np.fft.rfft(values, axis=0)[1:count+1])/len(values)


@lru_cache(maxsize=1)
def build_demonstrations(p=DemoSettings()):
    settings = Settings()
    nu, chem_t, truth, s0, components = build_truth(settings)
    n = settings.n_opd; dx = 1/(2*settings.fold_width)
    x = np.fft.fftfreq(n)*n*dx
    t = np.arange(round(p.duration_us/p.dt_us)+1)*p.dt_us
    motion = drive(t, p)
    k = 2*np.pi*nu*2e-7
    ref = s0*np.cos(k*p.common_bias_nm)
    mirror_s = averaged_intensity(s0, nu, motion, p.common_bias_nm)
    mirror_a = absorbance(mirror_s, ref)
    peak = float(interferogram(s0, nu, 0.))
    # An explicitly assumed, ZPD-local detector coupling. Uniform pickup across
    # all OPD steps has a different spectrum; this is not a universal noise model.
    coupling = np.exp(-.5*(x/(.5*dx))**2)
    electrical_ifg = p.electrical_fraction*peak*np.sin(
        2*np.pi*p.frequency_hz*t*1e-6+np.deg2rad(p.phase_deg))[:, None]*coupling
    electrical_ds = np.fft.rfft(electrical_ifg, axis=-1).real
    electrical_a = absorbance(ref+electrical_ds, ref)
    indices = np.array([0, -1, 1, 8, 32]) % n
    selected_x = x[indices]
    common = 2e-7*p.common_bias_nm
    trace_ref = interferogram(s0, nu, selected_x+common)
    detector_change = interferogram(s0, nu, selected_x[None, :]+common+motion*2e-7)-trace_ref
    local_slope = interferogram(s0, nu, selected_x+common, derivative=1)
    linear_change = motion*2e-7*local_slope
    continuous_x = np.linspace(-170, 170, 6001)*1e-4
    continuous_ifg = interferogram(s0, nu, continuous_x+common)
    continuous_slope = interferogram(s0, nu, continuous_x+common, derivative=1)
    # Parity is measured over exactly one drive cycle, rather than an FFT of
    # the short 2.84-cycle display record with leakage between frequency bins.
    cycle_t = np.arange(p.harmonic_samples)/p.harmonic_samples/p.frequency_hz*1e6
    cycle_drive = drive(cycle_t, p)
    j = int(np.argmin(abs(nu-p.selected_cm1))); selected_nu = nu[j:j+1]
    harmonic = {}; temporal = {}
    for name, bias in [('Zero bias', 0.), ('Common bias', p.common_bias_nm)]:
        denominator = np.cos(2*np.pi*selected_nu*2e-7*bias)
        one_cycle = absorbance(averaged_intensity(np.ones(1), selected_nu, cycle_drive, bias), denominator)[:,0]
        harmonic[name] = harmonic_amplitudes(one_cycle)
        temporal[name] = absorbance(averaged_intensity(np.ones(1), selected_nu, motion, bias), denominator)[:,0]
    # Chemical signal: same native bin-averaged truth as the main application.
    # Motion is sampled at bin centers and switches on at the flash, as in its
    # locked preset. This is distinct from the ungated, unexcited baseline lesson.
    chem_drive = drive(chem_t, p)*(chem_t[:,None] >= 0)
    chem_s = s0[None,:]*10**(-truth)
    chemical_with_mirror = absorbance(averaged_intensity(chem_s,nu,chem_drive,p.common_bias_nm),ref)
    counts = np.arange(1,33)
    phase_sets = {
        '10 Hz repetition': lambda count: shot_phases(count,p.frequency_hz,p.repetition_hz),
        '10.01 Hz repetition': lambda count: shot_phases(count,p.frequency_hz,p.detuned_repetition_hz),
        '180° pairs': lambda count: shot_phases(count,p.frequency_hz,paired=True),
    }
    transfers = {}; averaged_traces = {}; averaged_harmonics = {}
    denominator = np.cos(2*np.pi*selected_nu*2e-7*p.common_bias_nm)
    for label, phases in phase_sets.items():
        transfers[label] = np.array([[coherence(phases(count),m) for count in counts] for m in [1,2]])
        actual = phases(p.demonstration_coadds)
        averaged_traces[label] = absorbance(averaged_intensity(np.ones(1),selected_nu,drive(t,p,actual),p.common_bias_nm),denominator)[:,0]
        one_cycle = absorbance(averaged_intensity(np.ones(1),selected_nu,drive(cycle_t,p,actual),p.common_bias_nm),denominator)[:,0]
        averaged_harmonics[label] = harmonic_amplitudes(one_cycle)
    assert np.isfinite(mirror_a).all() and np.isfinite(electrical_a).all()
    assert np.isfinite(chemical_with_mirror).all()
    return dict(settings=asdict(p), reference=REFERENCE, nu=nu, time_us=t, s0=s0,
        reference_spectrum=ref, mirror_OD=mirror_a, electrical_OD=electrical_a,
        electrical_pattern=coupling,electrical_delta_s=electrical_ds,
        x_cm=x,selected_x_cm=selected_x,selected_opd_indices=indices,
        ir_ifg_peak=peak,detector_change=detector_change,linear_change=linear_change,
        trace_reference=trace_ref,local_slope=local_slope,continuous_x_cm=continuous_x,
        continuous_ifg=continuous_ifg,continuous_slope=continuous_slope,
        harmonic_amplitudes_OD=harmonic,harmonic_traces_OD=temporal,
        selected_actual_cm1=float(nu[j]),selected_channel=j,cycle_time_us=cycle_t,
        chemical_time_us=chem_t,chemical_clean_OD=truth,chemical_mirror_OD=chemical_with_mirror,
        coadd_counts=counts,coherence=transfers,averaged_traces_OD=averaged_traces,
        averaged_harmonics_OD=averaged_harmonics)


def metrics(data):
    p = data['settings']; pairs = data['averaged_harmonics_OD']['180° pairs']
    return dict(settings=p,reference=REFERENCE,
        assumptions=[
            'All figures are synthetic; no measured arrays, smoothing, baseline subtraction or per-trace normalization.',
            'Fixed-real spectral readout; exact uniform-displacement cosine, not production fourth-order shifts.',
            'Stationary reference at the same common bias; baseline time zero is an acquisition origin, not a flash.',
            'Motion and electrical pickup are evaluated at 6 us bin centers; within-bin dynamics are not integrated.',
            'Chemical lesson uses native 6 us bin-averaged chemical bases and bin-center, flash-gated motion.',
            'Coherent phase across OPD is imposed to isolate shot timing. No free-running step-phase schedule or random noise is added.',
            'Average intensity before logarithm. Coherence factors refer to intensity harmonics, not a universal OD attenuation.',
            'AC detector component only; total unmodulated detector DC is not represented.',
            'Electrical coupling is an assumed Gaussian localized about ZPD, width one half of an OPD step.',
        ],selected_actual_cm1=data['selected_actual_cm1'],spectral_axis='descending',
        full_band_cm1=[float(data['nu'].max()),float(data['nu'].min())],
        baseline_time_us=[float(data['time_us'][0]),float(data['time_us'][-1])],
        selected_OPD_um=(data['selected_x_cm']*1e4).tolist(),
        harmonic_amplitudes_uOD={key:(value*1e6).tolist() for key,value in data['harmonic_amplitudes_OD'].items()},
        paired_OD_f_amplitude_uOD=float(pairs[0]*1e6),paired_OD_2f_amplitude_uOD=float(pairs[1]*1e6),
        zero_bias_f_to_2f=float(data['harmonic_amplitudes_OD']['Zero bias'][0]/data['harmonic_amplitudes_OD']['Zero bias'][1]),
        common_bias_f_to_2f=float(data['harmonic_amplitudes_OD']['Common bias'][0]/data['harmonic_amplitudes_OD']['Common bias'][1]),
        coadd_coherence_at_N8={key:value[:,p['demonstration_coadds']-1].tolist() for key,value in data['coherence'].items()},
        roundoff_policy='Harmonic amplitudes remain unrounded in numerical exports; figures mark values below 1e-6 uOD as below display floor.')
