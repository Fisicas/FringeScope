"""Local installer round trip; writes only its dedicated installation and user fixtures."""
import hashlib,json,os,subprocess,time,winreg
from pathlib import Path
root=Path(__file__).resolve().parent.parent
qa=Path(os.environ.get('FRINGESCOPE_QA_DIR',str(root/'qa_packaging_v01'))).resolve();qa.mkdir(exist_ok=True)
folder=(qa/'installed app').resolve()
assert folder.is_relative_to(qa.resolve()) and folder.name=='installed app'
key=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{E2584836-92DC-4E44-BCA4-40F9B58478C0}_is1'
try:
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key) as k:
  previous=winreg.QueryValueEx(k,'InstallLocation')[0]
  if Path(previous).resolve()!=folder:raise RuntimeError('A different FringeScope installation already exists; test stopped')
except FileNotFoundError:pass
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(qa/'user profile'))
env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
env['PATH']=os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),os.environ['SystemRoot']])
setup=Path(os.environ.get('FRINGESCOPE_BUILD_OUTPUT',str(root/'build-output')))/'installer/FringeScope-setup.exe'
def install(log):
 subprocess.run([str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={folder}','/TASKS=',f'/LOG={qa/log}'],cwd=qa,timeout=180,check=True)
def smoke(name):
 subprocess.run([str(folder/'FringeScope.exe'),'--self-test-output',str(qa/name)],cwd=qa,env=env,timeout=120,check=True)
 data=json.loads((qa/name/'checks.json').read_text());assert data['installed'] and data['frozen']
install('install.log');smoke('installed')
marker=json.loads((folder/'fringescope-install.json').read_text());assert marker['app_id']=='E2584836-92DC-4E44-BCA4-40F9B58478C0'
sentinel=qa/'user profile/FringeScope/exports/preservation.txt';sentinel.parent.mkdir(parents=True,exist_ok=True);sentinel.write_text('preserve user output')
stale=folder/'_internal/stale_test_fixture.txt';stale.write_text('old dependency fixture')
install('reinstall.log');assert not stale.exists() and sentinel.read_text()=='preserve user output'
smoke('reinstalled')
# Uninstall only the verified, workspace-contained fixture installation.
assert folder.is_relative_to(qa.resolve()) and json.loads((folder/'fringescope-install.json').read_text())['app_id']==marker['app_id']
subprocess.run([str(folder/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/LOG={qa/"uninstall.log"}'],cwd=qa,timeout=120,check=True)
for _ in range(20):
 if not (folder/'FringeScope.exe').exists():break
 time.sleep(.25)
assert not (folder/'FringeScope.exe').exists() and sentinel.read_text()=='preserve user output'
record={'status':'passed','checks':['per-user installation in a path with spaces','installed frozen startup/assets/export offline','in-place reinstallation removes stale runtime fixture','user export survives replacement','reinstalled app passes same smoke checks','uninstallation removes app and preserves user data'], 'installer_sha256':hashlib.sha256(setup.read_bytes()).hexdigest()}
(qa/'installation_checks.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
