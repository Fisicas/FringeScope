from dataclasses import replace
import numpy as np
import pytest
from ftir_sim import Settings,simulate,continuous_hene,fold_display


def test_steady_hene_is_in_reference_and_every_time_bin():
    p=Settings(hene=True,heat_scale=0,rp_scale=0,offset_scale=0)
    r=simulate(p)
    assert np.max(abs(r['hene_reference_spectrum']))>1e-3
    np.testing.assert_allclose(r['hene_signal_spectrum'],np.broadcast_to(r['hene_reference_spectrum'],r['signal'].shape),atol=1e-14)
    np.testing.assert_allclose(r['observed'],0,atol=1e-13)
    assert np.max(abs(r['hene_signal_spectrum'][r['t_us']<0]))>1e-3


def test_cw_exact_reference_ratio_for_real_readout():
    p=Settings(hene=True);r=simulate(p);L=r['hene_reference_spectrum'];s=r['s0']
    expected=-np.log10((s[None,:]*10**(-r['ideal'])+L[None,:])/(s+L)[None,:])
    np.testing.assert_allclose(r['observed'],expected,atol=1e-12)
    blocked=simulate(replace(p,hene_blocking_od=6))
    np.testing.assert_allclose(blocked['hene_reference_spectrum'],L*1e-6,atol=1e-15)


def test_hene_and_actinic_are_independent_continuous_and_pulsed_terms():
    p=Settings(hene=True,laser=True,laser_route='interferometric',laser_area_us=2e-5)
    # A Gaussian centered on the flash has a leading half before zero. The
    # recorder bin centered at -3 us ends at zero and legitimately receives it.
    r=simulate(p);pre=r['t_us']<-p.dt_us/2;late=r['t_us']>100
    np.testing.assert_allclose(r['laser_signal_spectrum'][pre],0,atol=1e-14)
    np.testing.assert_allclose(r['laser_signal_spectrum'][late],0,atol=1e-14)
    assert np.max(abs(r['laser_signal_spectrum']))>1e-5
    assert np.max(abs(r['hene_signal_spectrum'][pre]))>1e-3
    np.testing.assert_allclose(r['hene_signal_spectrum'][0],r['hene_signal_spectrum'][-1],atol=1e-14)


def test_hene_uses_exact_physical_displacement_with_motion():
    p=Settings(hene=True,wobble=True,bias_nm=25,coadds=1)
    r=simulate(p);bare_peak=np.max(abs(np.fft.irfft(r['s0'],n=p.n_opd)))
    phase=2*np.pi*(1e7/p.hene_nm)*(r['x_cm'][None,:]+r['displacement_cm'])
    expected=p.hene_fraction*bare_peak*(1+np.cos(phase))
    expected=np.fft.rfft(expected,axis=-1).real
    np.testing.assert_allclose(r['hene_signal_spectrum'],expected,atol=1e-14)
    assert np.max(np.ptp(r['hene_signal_spectrum'],axis=0))>1e-3


def test_free_running_cw_reference_matches_averaged_preflash():
    p=Settings(hene=True,wobble=True,phase_mode='free',coadds=2,heat_scale=0,rp_scale=0,offset_scale=0)
    r=simulate(p);pre=r['t_us']<0
    np.testing.assert_allclose(r['hene_signal_spectrum'][pre].mean(0),r['hene_reference_spectrum'],atol=1e-13)
    np.testing.assert_allclose(r['signal'][pre].mean(0),r['ref'],atol=1e-12)


def test_direct_cw_does_not_acquire_a_wavelength_alias():
    p=Settings(hene=True,hene_route='direct');a=simulate(p);b=simulate(replace(p,hene_nm=632))
    np.testing.assert_array_equal(a['hene_reference_spectrum'],b['hene_reference_spectrum'])
    assert np.argmax(abs(a['hene_reference_spectrum']))==0
    assert a['hene_alias_cm1']==pytest.approx(fold_display(1e7/632.8,p.fold_width))
    assert b['hene_alias_cm1']==pytest.approx(1078.0446115932489)


def test_master_off_disables_cw_and_electrical_phase_is_separate():
    r=simulate(Settings(enabled=False,hene=True))
    assert np.max(abs(r['hene_reference_spectrum']))==0
    p=Settings(electrical=True,heat_scale=0,rp_scale=0,offset_scale=0)
    a=simulate(p);b=simulate(replace(p,phase_deg=73))
    np.testing.assert_array_equal(a['observed'],b['observed'])
    c=simulate(replace(p,electrical_phase_deg=73))
    assert np.max(abs(a['observed']-c['observed']))>1e-6
