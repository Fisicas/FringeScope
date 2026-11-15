"""Build locally; never uploads, signs, or enables updates. Use a prepared build venv."""
import argparse,hashlib,importlib.metadata as md,json,os,platform,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--iscc',type=Path,required=True);p.add_argument('--output',type=Path,default=root/'build-output');args=p.parse_args()
output=Path(os.path.abspath(args.output)).resolve();output.mkdir(parents=True,exist_ok=True)
if not args.iscc.is_file():raise SystemExit('Inno Setup compiler not found')
sys.path.insert(0,str(root/'desktop'))
import branding
record={'python':sys.version,'platform':platform.platform(),
 'packages':{name:md.version(name) for name in ['numpy','scipy','matplotlib','PySide6-Essentials','packaging','pyinstaller','pyinstaller-hooks-contrib']},
 'inno_compiler_sha256':hashlib.sha256(args.iscc.read_bytes()).hexdigest(),'version':branding.VERSION}
(output/'BUILD_ENVIRONMENT.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
subprocess.run([sys.executable,'-X','utf8',str(root/'desktop/build_theory.py')],cwd=root,check=True)
env=dict(os.environ);env['PATH']=os.pathsep.join([str(Path(sys.executable).parent),str(Path(os.environ['SystemRoot'])/'System32'),os.environ['SystemRoot']])
subprocess.run([sys.executable,'-X','utf8','-m','PyInstaller','--noconfirm','--clean','--distpath',str(output/'dist'),'--workpath',str(output/'work'),str(root/'tools/FringeScope.spec')],cwd=root,env=env,check=True)
subprocess.run([str(args.iscc),'/DAppVersion='+branding.VERSION,'/DBundleDir='+str(output/'dist/FringeScope'),'/DReleaseOutput='+str(output/'installer'),str(root/'tools/FringeScope.iss')],cwd=root,check=True)
asset=output/'installer/FringeScope-setup.exe'
(asset.parent/'SHA256SUMS.txt').write_text(hashlib.sha256(asset.read_bytes()).hexdigest()+'  '+asset.name+'\n',encoding='utf-8')
print('Built locally:',asset)
