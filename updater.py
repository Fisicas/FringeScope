"""Installed-only GitHub release updates. No network while publication hold is set."""
import hashlib,json,re,subprocess,sys,tempfile,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from packaging.version import Version,InvalidVersion

API='https://api.github.com/repos/Fisicas/FringeScope/releases/latest'
ASSET='FringeScope-setup.exe'

def enabled():
    cfg=json.loads((Path(__file__).parent/'release_config.json').read_text(encoding='utf-8'))
    return cfg.get('updates_enabled') is True

def install_dir():
    folder=Path(sys.executable).resolve().parent
    if not getattr(sys,'frozen',False) or not any(folder.glob('unins*.exe')):return None
    try:marker=json.loads((folder/'fringescope-install.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return None
    return folder if marker.get('app_id')=='E2584836-92DC-4E44-BCA4-40F9B58478C0' else None

def read_release(record,current):
    if record.get('draft') or record.get('prerelease'):return None
    try:
        version=Version(str(record['tag_name']).removeprefix('v'))
        if version.is_prerelease or version<=Version(current):return None
    except (KeyError,InvalidVersion):return None
    asset=next((a for a in record.get('assets',[]) if a.get('name')==ASSET and a.get('state','uploaded')=='uploaded'),None)
    if not asset:return None
    digest=asset.get('digest','')
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):raise ValueError('Update has no valid published SHA-256 digest')
    url=asset.get('browser_download_url','');parts=urlsplit(url)
    if parts.scheme!='https' or parts.netloc!='github.com' or not parts.path.startswith('/Fisicas/FringeScope/releases/download/') or not parts.path.endswith('/'+ASSET):raise ValueError('Unexpected installer download URL')
    size=asset.get('size')
    if not isinstance(size,int) or size<=0 or size>2_000_000_000:raise ValueError('Invalid installer size')
    return dict(version=str(version),url=url,size=size,sha256=digest[7:].lower())

def available(current):
    if not enabled() or install_dir() is None:return None
    req=urllib.request.Request(API,headers={'User-Agent':'FringeScope-updater','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=8) as response:
        data=response.read(2_000_001)
    if len(data)>2_000_000:raise ValueError('Oversized release metadata')
    return read_release(json.loads(data),current)

def download(release,opener=urllib.request.urlopen,cancel=lambda:False):
    folder=Path(tempfile.mkdtemp(prefix='FringeScope-update-'));target=folder/ASSET
    digest=hashlib.sha256();size=0
    try:
        req=urllib.request.Request(release['url'],headers={'User-Agent':'FringeScope-updater'})
        with opener(req,timeout=30) as source,target.open('wb') as output:
            while True:
                if cancel():raise RuntimeError('Update download canceled')
                chunk=source.read(65536)
                if not chunk:break
                size+=len(chunk)
                if size>release['size']:raise ValueError('Downloaded installer exceeds declared size')
                digest.update(chunk);output.write(chunk)
        if size!=release['size'] or digest.hexdigest()!=release['sha256']:raise ValueError('Update checksum/size verification failed; nothing was installed')
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise

def installer_command(installer,folder):
    return [str(installer),'/SILENT','/SUPPRESSMSGBOXES','/NORESTART','/CLOSEAPPLICATIONS','/relaunch=1',f'/DIR={folder}']

def launch(installer,folder):
    subprocess.Popen(installer_command(installer,folder),creationflags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),close_fds=True)
