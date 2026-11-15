"""FTIR artifact forward models. Units: cm OPD, cm^-1, us, mirror nm, OD.

Independent implementation; no UFit code is imported or executed.
See THEORY.md for derivations, assumptions, and primary references.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from functools import lru_cache
import json, math
import numpy as np
from scipy.optimize import least_squares
from scipy.special import ndtr
from scipy.stats import exponnorm

ROOT=Path(__file__).resolve().parent
CHEMICAL_SUPPORT_CM1=(1120.,1950.)
REFERENCE_THRESHOLD_FRACTION=.01

@dataclass
class Settings:
    source: str='model'
    enabled: bool=True
    seed: int=20261114
    fold_width: float=1053.1957284666667
    n_opd: int=1024
    dt_us: float=6.
    heat_tau: float=12.159431012654633
    rp_tau: float=449.14283667622936
    heat_beta: float=1.
    rp_beta: float=1.
    heat_scale: float=1.
    rp_scale: float=1.
    offset_scale: float=1.
    globar: bool=False
    globar_fraction: float=.1
    globar_temp: float=1400.
    leak_center: float=3300.
    leak_width: float=550.
    blocking_od: float=0.
    leak_transient_ppm: float=0.
    laser: bool=False
    laser_route: str='bypass_scatter'
    laser_nm: float=532.
    pulse_fwhm_ns: float=6.
    reflection_ns: float=20.
    reflection_fraction: float=.3
    response_us: float=.15
    laser_area_us: float=.002
    laser_delay_us: float=0.
    laser_scatter: float=.3
    laser_blocking_od: float=0.
    hene: bool=False
    hene_nm: float=632.8
    hene_fraction: float=.0002
    hene_blocking_od: float=0.
    hene_route: str='interferometric'
    hene_phase_deg: float=0.
    recovery: bool=False
    recovery_fraction: float=.001
    recovery_us: float=15.
    wobble: bool=False
    mirror_nm: float=2.
    frequency_hz: float=840.
    phase_deg: float=-100.
    waveform: str='sine'
    second_ratio: float=.15754
    second_phase_deg: float=-99.39
    third_ratio: float=.06076
    third_phase_deg: float=-44.88
    chirp_hz_per_ms: float=0.
    envelope_slope: float=0.
    quadrature_slope: float=0.
    servo_fraction: float=0.
    servo_sharpness: float=12.
    phase_mode: str='locked'
    coadds: int=10
    repetition_hz: float=10.
    settle_ms: float=10.
    bias_nm: float=0.
    zpd: bool=False
    return_nm: float=2.
    jitter_nm: float=1.
    tilt: bool=False
    tilt_ppm: float=200.
    electrical: bool=False
    electrical_fraction: float=.0002
    electrical_frequency: float=840.
    electrical_phase_deg: float=0.
    electrical_pattern: str='zpd_local'
    noise: bool=False
    noise_fraction: float=1.e-6
    phase_readout: str='real'

def kww_basis(t,taus,betas,dt=6.):
    t=np.asarray(t,float)
    if dt>0 and np.all(np.asarray(betas)==1):
        lo=np.maximum(t-dt/2,0);hi=np.maximum(t+dt/2,0)
        return np.column_stack([a/dt*(np.exp(-lo/a)-np.exp(-hi/a)) for a in taus])
    nodes,weights=np.polynomial.legendre.leggauss(12)
    u=t[:,None]+dt/2*nodes if dt>0 else t[:,None]
    if dt<=0:weights=np.array([2.])
    return np.column_stack([((np.exp(-(np.maximum(u,0)/tau)**beta)*(u>=0))@weights/2) for tau,beta in zip(taus,betas)])

def fold_base(nu,B):
    """Unsigned alias q in [0,B], for spatial sample frequency Fs=2B."""
    return np.abs((np.asarray(nu)+B)%(2*B)-B)

def fold_display(nu,B):
    """Unfold into the chosen odd Nyquist zone [B,2B], descending display."""
    return 2*B-fold_base(nu,B)

def _interp(x,y,new,left=0.,right=0.):
    """Explicit paired reversal only for np.interp; output keeps new order."""
    if x[0]>x[-1]:x=x[::-1]; y=np.asarray(y)[...,::-1]
    if np.ndim(y)==1:return np.interp(new,x,y,left=left,right=right)
    return np.array([np.interp(new,x,row,left=left,right=right) for row in y])

def public_mode():
    path=ROOT/'release_config.json'
    return path.exists() and bool(json.loads(path.read_text(encoding='utf-8')).get('public_mode'))

def onset_basis(t,dt=6.):
    t=np.asarray(t)
    return (np.maximum(t+dt/2,0)-np.maximum(t-dt/2,0))/dt

def public_data():
    """Smooth Gaussian-band model informed by the designated best archive."""
    cfg=json.loads((ROOT/'synthetic_model.json').read_text(encoding='utf-8'))
    # Use the exact same endpoint expressions as the FFT display grid. Rounded
    # literals previously put one endpoint just outside interpolation support.
    band=Settings().fold_width
    nu=np.linspace(2*band,band,513)
    a=[]
    taper=np.clip((nu-1120)/35,0,1)*np.clip((1950-nu)/35,0,1)
    for key in ['heating','recombination','offset']:
        a.append(sum(b['amplitude_uOD']*1e-6*np.exp(-.5*((nu-b['center_cm1'])/b['sigma_cm1'])**2) for b in cfg['bands'][key])*taper)
    def g(c,w):return np.exp(-.5*((nu-c)/w)**2)
    # Assumed detector/filter envelope with broad absorption troughs. It is
    # intentionally analytic; no native/derived single-beam array is released.
    s=.08+1.15*g(1650,480)-.82*g(1655,43)-.43*g(1545,34)
    t=np.arange(590)*6-153
    X=np.column_stack([kww_basis(t,cfg['taus_us'],[1,1]),onset_basis(t)])
    return dict(nu=nu,t_us=t,s0=s,templates=np.array(a),measured=X@np.array(a))

@lru_cache(maxsize=8)
def load_data(key):
    if key=='public':return public_data()
    path=ROOT/'private_data'/(key+'.npz')
    if not path.exists():
        raise FileNotFoundError(f'{path.name} is not prepared. Run prepare_data.py, or select the public analytic template.')
    with np.load(path) as d:return {k:d[k] for k in d.files}

def available_sources():
    choices={'model':'Simulated PSI · 2 exponentials + offset'}
    if not public_mode() and (ROOT/'private_data/best.npz').exists():
        choices={'model':'Idealized signal based on designated best menB+PhQ',
                 'best_replay':'Measured best menB+PhQ · existing artifacts retained',
                 'oscillation_replay':'Measured Sep23 comparison · existing oscillation retained'}
    return choices

def build_truth(p):
    if public_mode() and p.source!='model':raise ValueError('Public release exposes simulated data only.')
    key=('best' if not public_mode() and (ROOT/'private_data/best.npz').exists() else 'public') if p.source=='model' else p.source.split('_')[0]
    d=load_data(key)
    B=p.fold_width
    q=np.arange(p.n_opd//2+1)*(2*B/p.n_opd)
    nu=2*B-q
    t=np.asarray(d['t_us'],float)
    # Detector timing is adjustable. Retain number of points and native onset
    # fraction (3 us after trigger for first postflash bin in supplied data).
    if p.dt_us!=6. and p.source in ('model','public'):
        t=(np.arange(len(t))-25.5)*p.dt_us
    if p.source in ('model','public'):
        a=_interp(d['nu'],d['templates'],nu)
        a=a*np.array([p.heat_scale,p.rp_scale,p.offset_scale])[:,None]
        X=np.column_stack([kww_basis(t,[p.heat_tau,p.rp_tau],[p.heat_beta,p.rp_beta],p.dt_us),onset_basis(t,p.dt_us)])
        truth=X@a
    else:
        truth=_interp(d['nu'],d['measured'],nu)
        a=None
    s0=_interp(d['nu'],d['s0'],nu)
    # The synthetic chemical templates have declared finite support. The
    # assumed reference covers the complete sampled IR band. Preserve zero or
    # nonpositive reference values: the explicit mask handles undefined ratios.
    return nu,t,truth,s0,a

def mirror_waveform(t_us,p,step_phase=0.):
    """Declared drive hypothesis, not inferred/measured mirror displacement."""
    ts=np.asarray(t_us)*1e-6
    theta=2*np.pi*(p.frequency_hz*ts+.5*p.chirp_hz_per_ms*1000*ts**2)+np.deg2rad(p.phase_deg)
    theta=np.asarray(theta)[...,None]+np.asarray(step_phase)
    v=((np.asarray(t_us)-1701.)/3354.)[...,None]
    value=np.sin(theta)
    if p.waveform!='sine':
        value+=p.second_ratio*np.sin(2*theta+np.deg2rad(p.second_phase_deg))
        if p.waveform in ('harmonic3','servo','envelope'):
            value+=p.third_ratio*np.sin(3*theta+np.deg2rad(p.third_phase_deg))
    value=(1+p.envelope_slope*v)*value+p.quadrature_slope*v*np.cos(theta)
    if p.waveform=='servo':value+=p.servo_fraction*np.tanh(p.servo_sharpness*np.cos(theta))
    return value

def _exgauss(t,sigma,tau,kind):
    if tau<=1e-8:
        return ndtr(t/sigma) if kind=='cdf' else np.exp(-.5*(t/sigma)**2)/(np.sqrt(2*np.pi)*sigma)
    return getattr(exponnorm,kind)(t,tau/sigma,loc=0,scale=sigma)

def laser_response(t,p,kind='pdf'):
    """Unit-area Gaussian convolved with optical tail and detector response."""
    t=np.asarray(t)-p.laser_delay_us
    sigma=max(p.pulse_fwhm_ns,0.01)*1e-3/2.354820045
    td=max(p.response_us,0.)
    tr=max(p.reflection_ns*1e-3,0.)
    direct=_exgauss(t,sigma,td,kind)
    if tr<=1e-8:echo=direct
    elif td<=1e-8:echo=_exgauss(t,sigma,tr,kind)
    else:
        if abs(td-tr)<1e-5*max(td,tr):tr=td*1.00002
        echo=(td*direct-tr*_exgauss(t,sigma,tr,kind))/(td-tr)
    return (1-p.reflection_fraction)*direct+p.reflection_fraction*echo

def laser_bins(t,p):
    return (laser_response(np.asarray(t)+p.dt_us/2,p,'cdf')-laser_response(np.asarray(t)-p.dt_us/2,p,'cdf'))/p.dt_us

def _deposit(q,v,B,n):
    # Linear deposition conserves integrated discrete power, resolves off-grid
    # alias location to one bin; it is not a measured OPUS instrument line shape.
    z=np.asarray(q)/(2*B/n)
    lo=np.floor(z).astype(int); frac=z-lo
    lo=np.clip(lo,0,n//2); hi=np.minimum(lo+1,n//2)
    out=np.zeros(n//2+1,dtype=complex)
    np.add.at(out,lo,v*(1-frac)); np.add.at(out,hi,v*frac)
    return out

def leak_spectra(p):
    """Planck radiance x assumed Gaussian transmission x flat responsivity.

    Returns physical source grid and 5 folded derivative spectra. Changing
    an unknown leak filter or detector response changes the predicted ghosts.
    """
    v=np.arange(2.,10000.,2.)
    radiance=v**3/np.expm1(1.438776877*v/p.globar_temp)
    optical=np.exp(-.5*((v-p.leak_center)/max(p.leak_width,2.))**2)
    optical[(v>=p.fold_width)&(v<=2*p.fold_width)]=0.
    source=radiance*optical
    q=fold_base(v,p.fold_width)
    signed=(v+p.fold_width)%(2*p.fold_width)-p.fold_width
    direction=np.where(signed>=0,1.,-1.)
    folded=[_deposit(q,source*(1j*direction*2*np.pi*v)**m,p.fold_width,p.n_opd) for m in range(5)]
    scale=p.globar_fraction*10.**(-p.blocking_od)/max(np.max(folded[0].real),1e-30)
    return v,source*scale,[a*scale for a in folded]

def _derivatives(spectrum,nu,n,axis=-1):
    return [np.fft.irfft(spectrum*((-1j*2*np.pi*nu)**m),n=n,axis=axis) for m in range(5)]

def _shifted(derivatives,delta):
    out=np.broadcast_to(derivatives[0],np.broadcast_shapes(np.shape(derivatives[0]),np.shape(delta))).copy()
    for m in range(1,5):out+=derivatives[m]*np.power(delta,m)/math.factorial(m)
    return out

def _readout(i,mode):
    ft=np.fft.rfft(i,axis=-1)
    return np.abs(ft) if mode=='magnitude' else ft.real


def continuous_hene(x_cm,delta_cm,p,ir_ifg_peak):
    """CW detector-equivalent IFG, present before/after the flash and in S0.

    The OPD-modulated branch is evaluated exactly at the physical wavelength,
    including mirror displacement, rather than Taylor expanded after aliasing.
    A uniform direct bypass has no wavelength-dependent spatial carrier.
    """
    shape=np.broadcast_shapes(np.shape(x_cm),np.shape(delta_cm))
    if not p.enabled or not p.hene or p.hene_fraction==0:return np.zeros(shape)
    if p.hene_nm<=0:raise ValueError('HeNe wavelength must be positive')
    level=p.hene_fraction*10**(-p.hene_blocking_od)*ir_ifg_peak
    if p.hene_route=='direct':return np.full(shape,level)
    if p.hene_route!='interferometric':raise ValueError('Unknown HeNe optical path')
    phase=2*np.pi*(1e7/p.hene_nm)*(np.asarray(x_cm)+np.asarray(delta_cm))+np.deg2rad(p.hene_phase_deg)
    return level*(1+np.cos(phase))

def simulate(p=None):
    p=p or Settings()
    if p.n_opd<256 or p.n_opd%2:raise ValueError('n_opd must be even and >=256')
    if p.fold_width<=0 or p.dt_us<=0:raise ValueError('Positive folding width and time bin required')
    if p.source.endswith('replay') and p.dt_us!=6.:
        raise ValueError('Measured replay retains its native 6 us time spacing; set Time bin to 6 us.')
    nu,t,truth,s0,truth_das=build_truth(p)
    n=p.n_opd; B=p.fold_width; dx=1/(2*B)
    x=np.fft.fftfreq(n)*n*dx
    rng=np.random.default_rng(p.seed)
    valid=np.isfinite(s0)&(s0>REFERENCE_THRESHOLD_FRACTION*np.max(s0))
    on=p.enabled
    if p.globar and on:
        lv,ls,leak=leak_spectra(p)
    else:
        lv=np.array([0.,10000.]);ls=np.zeros(2);leak=[np.zeros_like(s0,dtype=complex) for _ in range(5)]
    L=leak[0].real
    spec=s0[None,:]*10**(-truth)
    refd=_derivatives(s0,nu,n)
    signald=_derivatives(spec,nu,n)
    leak_change=(p.leak_transient_ppm*1e-6*kww_basis(t,[p.heat_tau],[p.heat_beta],p.dt_us)[:,0]) if on else np.zeros(len(t))
    for m in range(5):
        li=np.fft.irfft(leak[m],n=n)
        refd[m]+=li
        signald[m]+=li[None,:]*(1+leak_change[:,None])
    # Mirror displacement -> OPD displacement = 2 d. Common bias affects both
    # records; differential return error appears only after the trigger.
    common=2*p.bias_nm*1e-7 if on else 0.
    ir_peak=float(np.max(np.abs(np.fft.irfft(s0,n=n))))
    hene_refi=continuous_hene(x,common,p,ir_peak)
    refi=_shifted(refd,common)+hene_refi
    after=(t>=0).astype(float)
    jitter=rng.normal(0,p.jitter_nm,n) if p.zpd and on else np.zeros(n)
    delta0=common+after[:,None]*2e-7*((p.return_nm if p.zpd and on else 0.)+jitter[None,:])
    displacement=delta0.copy()+np.zeros((len(t),n))
    if p.wobble and on:
        coadds=max(1,int(p.coadds))
        wave=2*np.pi*p.frequency_hz*t*1e-6+np.deg2rad(p.phase_deg)
        signal_i=np.zeros((len(t),n)); displacement=np.zeros_like(signal_i)
        free_reference=np.zeros(n);free_hene_reference=np.zeros(n);pre=t<0
        hene_signali=np.zeros_like(signal_i)
        # The hypothetical scan visits OPD monotonically; FFT storage wraps x.
        step_number=np.argsort(np.argsort(x))
        for j in range(coadds):
            if p.phase_mode=='random':phase=rng.uniform(0,2*np.pi,n)
            elif p.phase_mode=='free':phase=2*np.pi*p.frequency_hz*(step_number*(coadds/p.repetition_hz+p.settle_ms/1000)+j/p.repetition_hz)
            else:phase=np.zeros(n)
            gate=np.ones_like(after) if p.phase_mode=='free' else after
            delta=delta0+2e-7*p.mirror_nm*mirror_waveform(t,p,phase[None,:])*gate[:,None]
            cw=continuous_hene(x,delta,p,ir_peak)
            signal_i+=(_shifted(signald,delta)+cw)/coadds
            hene_signali+=cw/coadds
            displacement+=delta/coadds
            if p.phase_mode=='free' and pre.any():
                free_reference+=(_shifted(refd,delta[pre])+cw[pre]).mean(axis=0)/coadds
                free_hene_reference+=cw[pre].mean(axis=0)/coadds
        if p.phase_mode=='free' and pre.any():
            refi=free_reference;hene_refi=free_hene_reference
    else:
        hene_signali=continuous_hene(x,delta0,p,ir_peak)
        signal_i=_shifted(signald,delta0)+hene_signali
    peak=float(np.max(np.abs(refi)))
    if p.tilt and on:
        gain=1+p.tilt_ppm*1e-6*np.sin(2*np.pi*p.frequency_hz*t*1e-6+np.deg2rad(p.phase_deg))*after
        signal_i*=gain[:,None]
        hene_signali*=gain[:,None]
    response=laser_bins(t,p)
    laser_i=np.zeros_like(signal_i)
    if p.laser and on:
        if p.laser_route=='interferometric':pattern=1+np.cos(2*np.pi*(1e7/p.laser_nm)*x)
        elif p.laser_route=='bypass_scatter':pattern=np.maximum(0.,1+p.laser_scatter*rng.normal(size=n))
        else:pattern=np.ones(n)
        laser_i=p.laser_area_us*10**(-p.laser_blocking_od)*peak*response[:,None]*pattern[None,:]
        signal_i+=laser_i
    if p.recovery and on:
        # Independent assumed electronic overload/recovery channel, not optical
        # path broadening. Local coupling is explicitly hypothetical.
        envelope=np.exp(-np.maximum(t,0)/p.recovery_us)*after
        pattern=np.exp(-.5*(x/(2*dx))**2)
        signal_i+=p.recovery_fraction*peak*envelope[:,None]*pattern
    if p.electrical and on:
        phase=2*np.pi*p.electrical_frequency*t*1e-6+np.deg2rad(p.electrical_phase_deg)
        if p.electrical_pattern=='zpd_local':pattern=np.exp(-.5*(x/(.5*dx))**2)
        elif p.electrical_pattern=='random_steps':pattern=rng.normal(size=n)
        else:pattern=np.ones(n)
        signal_i+=p.electrical_fraction*peak*np.sin(phase)[:,None]*after[:,None]*pattern
    if p.noise and on:
        signal_i+=rng.normal(0,p.noise_fraction*peak,signal_i.shape)
    ref=_readout(refi,p.phase_readout)
    measured_s=_readout(signal_i,p.phase_readout)
    ok=(ref>0)&(measured_s>0)
    observed=np.full_like(measured_s,np.nan)
    # Divide only positive pairs; never substitute a floor for missing light.
    ref_grid=np.broadcast_to(ref,measured_s.shape)
    observed[ok]=-np.log10(measured_s[ok]/ref_grid[ok])
    observed[:,~valid]=np.nan
    truth[:,~valid]=np.nan
    warnings=[]
    if on and max(p.frequency_hz if p.wobble or p.tilt else 0,p.electrical_frequency if p.electrical else 0)*p.dt_us*1e-6>.02:
        warnings.append('Oscillatory motion/pickup is evaluated at bin centers; this frequency × bin width needs a finer bin or explicit within-bin response integration.')
    if not np.all(ok[:,valid]):warnings.append('Nonpositive reconstructed intensity: affected bins are masked, not clipped into absorbance.')
    if p.source.endswith('replay'):warnings.append('Measured replay retains existing artifacts; baseline S0 and phase are reconstructed, not raw time-resolved interferograms.')
    if p.source in ('model','best_replay') and not public_mode() and (ROOT/'private_data/best.npz').exists():warnings.append('Best menB has no single beam: FRL S0 is an explicit proxy for artifact amplitudes.')
    if p.wobble and p.waveform!='sine':warnings.append('Composite waveform is a declared motion hypothesis; archive intensity harmonics do not measure mirror displacement.')
    if p.bias_nm or (p.wobble and on) or (p.zpd and on):
        maxphase=np.max(np.abs(displacement))*2*np.pi*max(nu.max(),p.leak_center+4*p.leak_width if p.globar else 0)
        if maxphase>.25:warnings.append(f'Maximum estimated displacement phase {maxphase:.2f} rad: fourth-order shift expansion may require convergence checking.')
    if p.recovery and on:warnings.append('Overload recovery is an independently assumed response, not predicted from pulse energy or detector calibration.')
    if p.laser and p.laser_route!='interferometric' and on:warnings.append('Bypass laser: the optical wavelength does not set an in-band alias; step-dependent coupling, if selected, sets the artifact shape.')
    if p.hene and on:
        warnings.append('HeNe leakage is continuous and included in both reference and signal. A steady leak alone does not create a flash transient; visible sensitivity and optical coupling are assumed.')
    roi=valid&(nu>=1200)&(nu<=1900)
    rms=float(np.sqrt(np.nanmean((observed[:,roi]-truth[:,roi])**2)))
    full_rms=float(np.sqrt(np.nanmean((observed[:,valid]-truth[:,valid])**2)))
    return dict(nu=nu,t_us=t,ideal=truth,observed=observed,difference=observed-truth,s0=s0,ref=ref,signal=measured_s,valid=valid,
        truth_das=truth_das,x_cm=x,reference_ifg=refi,signal_ifg=signal_i,displacement_cm=displacement,laser_response=response,
        hene_reference_ifg=hene_refi,hene_reference_spectrum=_readout(hene_refi,p.phase_readout),
        hene_signal_spectrum=_readout(hene_signali,p.phase_readout),laser_signal_spectrum=_readout(laser_i,p.phase_readout),
        hene_alias_cm1=float(fold_display(1e7/p.hene_nm,B)),
        leak_nu=lv,leak_source=ls,folded_leak=L,warnings=warnings,artifact_rms_OD=rms,
        artifact_rms_full_OD=full_rms,display_band_cm1=[float(nu.min()),float(nu.max())],
        chemical_support_cm1=list(CHEMICAL_SUPPORT_CM1),reference_threshold_fraction=REFERENCE_THRESHOLD_FRACTION,
        settings=asdict(p),
        laser_alias_cm1=float(fold_display(1e7/p.laser_nm,B)),dx_um=dx*1e4)

def fit_das(result,p,free=False,start=0.,stop=3378.,low=1200.,high=1900.,offset=True):
    """Own unweighted variable projection; signed DAS, optional constant.

    No SEM/confidence bands are asserted. Correlated artifacts invalidate naive
    independent-noise intervals. Fixed-basis DAS are explicitly projections.
    """
    t=result['t_us'];nu=result['nu'];Y=result['observed']
    kt=(t>=start)&(t<=stop)
    kv=result['valid']&(nu>=low)&(nu<=high)&np.all(np.isfinite(Y[kt]),axis=0)
    if kt.sum()<8 or kv.sum()<3:raise ValueError('Fit window needs >=8 time bins and >=3 finite spectral bins')
    tau0=np.array([p.heat_tau,p.rp_tau]);beta=[p.heat_beta,p.rp_beta]
    yy=Y[kt][:,kv]
    def projection(tau,values):
        X=kww_basis(t[kt],tau,beta,p.dt_us)
        if offset:X=np.column_stack([X,np.ones(len(X))])
        A=np.linalg.lstsq(X,values,rcond=None)[0]
        return X,A
    def residual(z):
        X,A=projection(np.exp(z),yy)
        return ((X@A-yy)*1e5).ravel()
    opt=None
    if free:
        opt=least_squares(residual,np.log(tau0),bounds=(np.log([.5,25]),np.log([100,20000])),max_nfev=120,ftol=1e-8,xtol=1e-8,gtol=1e-8)
        tau=np.exp(opt.x)
    else:tau=tau0
    # Fit the same basis at all valid channels, even beyond optimization ROI.
    allok=result['valid']&np.all(np.isfinite(Y[kt]),axis=0)
    X,A=projection(tau,Y[kt][:,allok])
    das=np.full((2+int(offset),len(nu)),np.nan);das[:,allok]=A
    reconstruction=kww_basis(t,tau,beta,p.dt_us)@np.nan_to_num(das[:2])
    if offset:reconstruction+=onset_basis(t,p.dt_us)[:,None]*np.nan_to_num(das[2])
    residuals=Y-reconstruction
    notes=[]
    if free:
        if np.any(np.isclose(tau,[.5,25],rtol=.001)) or np.any(np.isclose(tau,[100,20000],rtol=.001)):
            notes.append('At least one fitted lifetime is at a bound; do not interpret it as a resolved physical lifetime.')
        if abs(np.log(tau[0]/tau[1]))<.1:
            notes.append('Fitted kinetic components are nearly coincident; their separate DAS are not resolved.')
        if np.any(tau>stop-start):notes.append('A fitted lifetime exceeds the fitting interval and is not independently resolved by this window.')
    return dict(taus=tau,betas=beta,das=das,reconstruction=reconstruction,residual=residuals,notes=notes,
        rms=float(np.sqrt(np.mean(residuals[kt][:,kv]**2))),condition=float(np.linalg.cond(X)),
        fit_mode='free lifetimes, fixed beta' if free else 'fixed kinetic basis (linear projection)',
        window={'start_us':start,'stop_us':stop,'low_cm1':low,'high_cm1':high,'constant':offset},
        converged=True if opt is None else bool(opt.success),nfev=0 if opt is None else int(opt.nfev))

def export_result(result,directory):
    """Always creates a new directory. Existing results cannot be overwritten."""
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    arrays={k:v for k,v in result.items() if isinstance(v,np.ndarray)}
    np.savez_compressed(directory/'simulation.npz',**arrays)
    meta={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}
    meta['units']={'wavenumber':'cm^-1','time':'us','OPD':'cm','absorbance':'OD','single_beam':'relative arbitrary units'}
    meta['spectral_axis_order']='descending'
    meta['signal_convention']='DeltaA = -log10(S/S0)' if 't_us' in result else 'A = -log10(sample/reference)'
    if 't_us' in result:
        # UFit rejects missing values. Keep full arrays/masks in NPZ, and export
        # only finite valid spectral rows to the interoperable DPT.
        keep=result['valid']&np.all(np.isfinite(result['observed']),axis=0)
        np.savetxt(directory/'simulated_descending.dpt',np.column_stack([result['nu'][keep],result['observed'][:,keep].T]),delimiter=',',fmt='%.10g',header='First column wavenumber cm-1; remaining columns DeltaA. Finite valid channels only. Time axis is in time_us.csv; set DPT time origin and spacing from that file.',comments='# ')
        np.savetxt(directory/'time_us.csv',result['t_us'],delimiter=',',header='time_us')
        np.savetxt(directory/'exported_spectral_mask.csv',keep.astype(int),fmt='%d',header='mask_in_full_NPZ_spectral_order')
        meta['DPT_export']={'retained_channels':int(keep.sum()),'excluded_channels':int((~keep).sum()),'criterion':'valid reference mask AND finite at all times; full grid remains in NPZ','first_time_us':float(result['t_us'][0]),'spacing_us':float(np.median(np.diff(result['t_us'])))}
    else:
        np.savetxt(directory/'static_absorbance.csv',np.column_stack([result['nu'],result['ideal'],result['observed'],result['difference']]),delimiter=',',header='wavenumber_cm-1,ideal_OD,simulated_OD,artifact_OD')
    (directory/'settings_and_provenance.json').write_text(json.dumps(meta,indent=2,default=lambda a:np.asarray(a).tolist()),encoding='utf-8')
    return directory
