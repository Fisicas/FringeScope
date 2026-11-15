"""Descriptive oscillation comparison, not a mechanical diagnosis."""
import numpy as np
from scipy.optimize import minimize_scalar
from ftir_sim import load_data

def oscillation_fit(nu,t,y,s0,f=840.,scan=False,exclude_spike=True):
    mask=(t>=24)&(t<=3378)
    # A single known spike is omitted only for the Sep23 comparison dataset.
    if exclude_spike:mask &= np.abs(t-2709)>3.01
    channels=(nu>=1200)&(nu<=1950)&np.all(np.isfinite(y[mask]),axis=0)
    tt=t[mask];v=(tt-tt.mean())/np.ptp(tt)
    yy=y[mask][:,channels]
    def design(f):return np.column_stack([v**j for j in range(4)]+[np.cos(2*np.pi*f*tt*1e-6),np.sin(2*np.pi*f*tt*1e-6)])
    def cost(f):
        X=design(f);a=np.linalg.lstsq(X,yy,rcond=None)[0]
        return np.sum((X@a-yy)**2)
    if scan:
        opt=minimize_scalar(cost,bounds=(650,1100),method='bounded',options={'xatol':.05})
        f=float(opt.x)
    X=design(f);a=np.linalg.lstsq(X,yy,rcond=None)[0]
    c=a[-2]-1j*a[-1]
    amplitude=np.abs(c)
    ph=np.angle(c)
    meanphasor=np.sum(c)
    relative_phase=np.rad2deg(np.angle(c*np.exp(-1j*np.angle(meanphasor))))
    # Small-signal relation only; stored sample S0 has arbitrary median scale.
    signed=amplitude*np.cos(np.angle(c)-np.angle(meanphasor))
    ds=-np.log(10)*s0[channels]*signed
    shape={}
    for name,template in {'constant_DeltaA':np.ones(len(signed)),'inverse_S0':1/s0[channels]}.items():
        scale=template@signed/(template@template)
        shape[name]=float(1-np.sum((signed-scale*template)**2)/np.sum(signed**2))
    return dict(nu=nu[channels],frequency_hz=f,amplitude_OD=amplitude,signed_OD=signed,relative_phase_deg=relative_phase,
                deltaS=ds,shape_uncentered_R2=shape,time_points=int(mask.sum()),periods=float(np.ptp(tt)*f*1e-6),
                exclusions='24-3378 us; cubic nuisance baseline; Sep23 t=2709 us excluded' if exclude_spike else '24-3378 us; cubic nuisance baseline; no spike exclusion')

def real_oscillation(scan=True,f=840.):
    d=load_data('oscillation')
    return oscillation_fit(d['nu'],d['t_us'],d['measured'],d['s0'],f,scan)
