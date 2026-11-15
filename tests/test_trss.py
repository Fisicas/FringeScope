from dataclasses import replace
import numpy as np
import pytest
import ftir_sim as core
from ftir_sim import Settings,simulate,fit_das,fold_display,laser_bins,laser_response,mirror_waveform,export_result

def zero(**kw):return Settings(heat_scale=0,rp_scale=0,offset_scale=0,**kw)

def test_default_plain_exponentials_and_offset():
    p=Settings();r=simulate(p);f=fit_das(r,p)
    assert p.heat_beta==p.rp_beta==1
    assert r['truth_das'].shape[0]==3 and f['das'].shape[0]==3
    assert r['artifact_rms_OD']<1e-12 and f['rms']<1e-12
    assert np.all(np.diff(r['nu'])<0)

def test_offset_is_constant_and_causal():
    r=simulate(Settings(heat_scale=0,rp_scale=0));v=r['valid'];t=r['t_us']
    np.testing.assert_allclose(r['ideal'][t<0][:,v],0,atol=1e-15)
    np.testing.assert_allclose(r['ideal'][-1,v],r['ideal'][100,v],atol=1e-15)

def test_exact_exponential_bin_average():
    t=np.array([-3.,3.,9.]);tau=12
    expected=[0,tau/6*(1-np.exp(-6/tau)),tau/6*(np.exp(-6/tau)-np.exp(-12/tau))]
    np.testing.assert_allclose(core.kww_basis(t,[tau],[1],6)[:,0],expected,atol=1e-14)

def test_optical_alias_and_532():
    B=Settings().fold_width;x=np.arange(1024)/(2*B)
    for v in [700,1650,3300,1e7/532]:
        np.testing.assert_allclose(np.cos(2*np.pi*v*x),np.cos(2*np.pi*fold_display(v,B)*x),atol=2e-11)
    assert fold_display(1e7/532,B)==pytest.approx(1945.86082573634)

def test_master_disables_everything():
    r=simulate(Settings(enabled=False,globar=True,laser=True,wobble=True,zpd=True,electrical=True,bias_nm=25))
    assert r['artifact_rms_OD']<1e-12

def test_stable_globar_no_false_transient():
    r=simulate(zero(globar=True));assert np.nanmax(abs(r['observed']))<1e-12

def test_globar_exact_ratio_and_blocking():
    p=Settings(globar=True);r=simulate(p);s=r['s0'];L=r['folded_leak'];v=r['valid']
    expected=-np.log10((s[None,:]*10**(-r['ideal'])+L)/(s+L))
    np.testing.assert_allclose(r['observed'][:,v],expected[:,v],atol=1e-12)
    assert simulate(replace(p,blocking_od=6))['artifact_rms_OD']<r['artifact_rms_OD']*2e-6

def test_bypass_does_not_fold_at_optical_wavelength():
    p=Settings(laser=True,laser_route='bypass_uniform');r=simulate(p)
    assert r['artifact_rms_OD']<1e-12
    assert simulate(replace(p,laser_route='interferometric'))['artifact_rms_OD']>1e-9

def test_pulse_area_and_bins():
    p=Settings();t=np.linspace(-.2,10,60001)
    assert np.trapezoid(laser_response(t,p),t)==pytest.approx(1,abs=1e-7)
    bins=np.arange(-9,75,6.);assert 6*np.sum(laser_bins(bins,p))==pytest.approx(1,abs=1e-10)
    interior=replace(p,laser_delay_us=.5)
    assert np.linalg.norm(laser_bins(bins,interior)-laser_bins(bins,replace(interior,pulse_fwhm_ns=30)))<1e-8

def test_seed_and_free_running_baseline():
    p=Settings(wobble=True,phase_mode='random');a=simulate(p);b=simulate(p)
    np.testing.assert_array_equal(a['observed'],b['observed'])
    r=simulate(zero(wobble=True,phase_mode='free'));pre=r['t_us']<0
    assert np.max(abs(r['displacement_cm'][pre]))>1e-8
    np.testing.assert_allclose(r['signal'][pre].mean(0),r['ref'],atol=1e-12)

def test_mirror_bias_f_vs_2f():
    p=zero(wobble=True,phase_deg=0);r=simulate(p);t=r['t_us'];k=t>0;j=np.argmin(abs(r['nu']-1697))
    X=np.column_stack([np.ones(k.sum())]+[fun(2*np.pi*f*t[k]*1e-6) for f in [840,1680] for fun in [np.sin,np.cos]])
    a=np.linalg.lstsq(X,r['observed'][k,j],rcond=None)[0]
    assert np.linalg.norm(a[3:])>100*np.linalg.norm(a[1:3])
    r=simulate(replace(p,bias_nm=25));a=np.linalg.lstsq(X,r['observed'][k,j],rcond=None)[0]
    assert np.linalg.norm(a[1:3])>5*np.linalg.norm(a[3:])

def test_harmonic_composition():
    p=Settings(waveform='harmonic3',phase_deg=12,second_ratio=.2,third_ratio=.1,second_phase_deg=30,third_phase_deg=-20)
    t=np.linspace(0,3000,501);theta=2*np.pi*p.frequency_hz*t*1e-6+np.deg2rad(12)
    expected=np.sin(theta)+.2*np.sin(2*theta+np.deg2rad(30))+.1*np.sin(3*theta-np.deg2rad(20))
    np.testing.assert_allclose(mirror_waveform(t,p).ravel(),expected,atol=1e-12)

def test_lifetime_recovery_with_offset():
    truth=Settings(heat_tau=18,rp_tau=550);r=simulate(truth)
    f=fit_das(r,replace(truth,heat_tau=10,rp_tau=300),True)
    np.testing.assert_allclose(f['taus'],[18,550],rtol=1e-4)
    assert f['converged'] and f['rms']<1e-10

def test_public_has_one_source_and_forbids_replay(monkeypatch):
    monkeypatch.setattr(core,'public_mode',lambda:True)
    assert list(core.available_sources())==['model']
    with pytest.raises(ValueError):simulate(Settings(source='best_replay'))
    assert simulate()['truth_das'].shape[0]==3

def test_export_finite_descending_no_overwrite(tmp_path):
    dest=tmp_path/'run';export_result(simulate(),dest)
    with pytest.raises(FileExistsError):export_result(simulate(),dest)
    a=np.loadtxt(dest/'simulated_descending.dpt',delimiter=',')
    assert np.all(np.isfinite(a)) and np.all(np.diff(a[:,0])<0)
