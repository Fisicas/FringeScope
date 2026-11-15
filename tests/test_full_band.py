from dataclasses import replace
import warnings
import numpy as np
import ftir_sim as core


def test_full_band_includes_both_exact_endpoints():
    p=core.Settings();r=core.simulate(p)
    assert len(r['nu'])==513 and r['valid'].all()
    assert r['nu'][0]==2*p.fold_width and r['nu'][-1]==p.fold_width
    assert np.isfinite(r['observed']).all() and np.isfinite(r['ideal']).all()
    assert r['artifact_rms_full_OD']<1e-12
    outside=(r['nu']<=1120)|(r['nu']>=1950)
    np.testing.assert_array_equal(r['ideal'][:,outside],0)
    np.testing.assert_allclose(r['observed'][:,outside],0,atol=1e-14)


def test_zero_reference_is_preserved_and_masked(monkeypatch):
    data=core.public_data()
    data['s0']=data['s0'].copy();data['s0'][0]=0;data['s0'][1]=1e-8
    monkeypatch.setattr(core,'load_data',lambda key:data)
    with warnings.catch_warnings():
        warnings.simplefilter('error',RuntimeWarning)
        r=core.simulate()
    assert r['s0'][0]==0 and r['s0'][1]==1e-8
    assert not r['valid'][:2].any()
    assert np.isnan(r['observed'][:,:2]).all()
    assert np.isfinite(r['observed'][:,2:]).all()


def test_full_band_recovers_das_and_causal_bin_means():
    p=core.Settings();r=core.simulate(p)
    f=core.fit_das(r,p,low=p.fold_width,high=2*p.fold_width)
    # Independent closed-form bin integrals, including the causal offset.
    left=np.maximum(r['t_us']-p.dt_us/2,0)
    right=np.maximum(r['t_us']+p.dt_us/2,0)
    basis=[tau/p.dt_us*(np.exp(-left/tau)-np.exp(-right/tau)) for tau in [p.heat_tau,p.rp_tau]]
    basis.append((right-left)/p.dt_us)
    expected=np.column_stack(basis)@r['truth_das']
    np.testing.assert_allclose(r['observed'],expected,atol=2e-14)
    np.testing.assert_allclose(f['das'],r['truth_das'],atol=2e-14)
    assert f['rms']<1e-12


def test_532_alias_has_valid_visible_channels():
    p=core.Settings(laser=True,laser_route='interferometric',laser_area_us=2e-5)
    r=core.simulate(p)
    channel=np.argmin(abs(r['nu']-r['laser_alias_cm1']))
    assert r['valid'][channel] and np.isfinite(r['difference'][:,channel]).all()
    assert np.max(abs(r['difference'][:,channel]))>1e-9
    assert p.fold_width<r['laser_alias_cm1']<2*p.fold_width
