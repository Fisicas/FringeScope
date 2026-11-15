import io,hashlib
from pathlib import Path
import pytest
import updater as u

def record(version='v0.12.0',digest=True):
 data=b'test installer'
 return {'tag_name':version,'assets':[{'name':u.ASSET,'size':len(data),'digest':'sha256:'+hashlib.sha256(data).hexdigest() if digest else '', 'browser_download_url':'https://github.com/Fisicas/FringeScope/releases/download/'+version+'/'+u.ASSET}]}

def test_version_and_required_digest():
 assert u.read_release(record(),'0.11.0')
 assert u.read_release(record('v0.9.0'),'0.11.0') is None
 assert u.read_release(dict(record(),prerelease=True),'0.11.0') is None
 assert u.read_release(record('v0.12.0rc1'),'0.11.0') is None
 with pytest.raises(ValueError):u.read_release(record(digest=False),'0.11.0')

def test_bad_host_and_path():
 r=record();r['assets'][0]['browser_download_url']='https://example.com/FringeScope-setup.exe'
 with pytest.raises(ValueError):u.read_release(r,'0.11.0')

def test_download_integrity(tmp_path,monkeypatch):
 monkeypatch.setattr(u.tempfile,'mkdtemp',lambda **kw:str(tmp_path))
 release=u.read_release(record(),'0.11.0')
 target=u.download(release,opener=lambda *a,**k:io.BytesIO(b'test installer'))
 assert target.read_bytes()==b'test installer'
 with pytest.raises(ValueError):u.download(release,opener=lambda *a,**k:io.BytesIO(b'wrong'))
 assert not target.exists()

def test_hold_is_offline_and_source_cannot_update(monkeypatch):
 monkeypatch.setattr(u.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Network under publication hold'))
 assert not u.enabled() and u.available('0.11.0') is None
 assert u.install_dir() is None

def test_paths_with_spaces_are_single_arguments():
 args=u.installer_command(Path('C:/temporary folder/setup.exe'),Path('C:/user programs/FringeScope'))
 assert args[0]==str(Path('C:/temporary folder/setup.exe'))
 assert args[-1].startswith('/DIR=') and len(args)==7


def test_download_cancellation_removes_partial_file(tmp_path,monkeypatch):
 monkeypatch.setattr(u.tempfile,'mkdtemp',lambda **kw:str(tmp_path))
 release=u.read_release(record(),'0.11.0')
 with pytest.raises(RuntimeError,match='canceled'):
  u.download(release,opener=lambda *a,**k:io.BytesIO(b'test installer'),cancel=lambda:True)
 assert not (tmp_path/u.ASSET).exists()

def test_installed_marker_must_match(tmp_path,monkeypatch):
 monkeypatch.setattr(u.sys,'frozen',True,raising=False)
 monkeypatch.setattr(u.sys,'executable',str(tmp_path/'FringeScope.exe'))
 (tmp_path/'unins000.exe').write_bytes(b'fixture')
 marker=tmp_path/'fringescope-install.json'
 marker.write_text('{"app_id":"another app"}')
 assert u.install_dir() is None
 marker.write_text('{"app_id":"E2584836-92DC-4E44-BCA4-40F9B58478C0"}')
 assert u.install_dir()==tmp_path
