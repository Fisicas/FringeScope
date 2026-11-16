"""Check an extracted release source tree. No files are modified."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import sys
import tempfile


def check(root, schema=None):
    import yaml
    import numpy as np
    root=root.resolve()
    failures=[]
    files=[p for p in root.rglob('*') if p.is_file() and not any(x in {'.git','__pycache__','.pytest_cache'} for x in p.relative_to(root).parts) and p.relative_to(root).parts[:2]!=('web','site')]
    allowed={'desktop','docs','requirements','tests','tools','web','.github'}
    for p in files:
        rel=p.relative_to(root)
        if len(rel.parts)>1 and rel.parts[0] not in allowed: failures.append(f'Unexpected directory: {rel}')
        if p.suffix.lower() in {'.pdf','.docx','.opus','.dpt','.npz','.npy','.ttf','.otf','.exe','.dll','.log','.zip','.xz'}: failures.append(f'Excluded asset: {rel}')
        if p.suffix.lower()=='.csv' and rel.parts[:2]!=('docs','examples'): failures.append(f'Unexpected CSV: {rel}')
        if p.suffix.lower() in {'.py','.md','.json','.toml','.html','.cff','.txt','.bib','.iss','.svg','.js','.css','.yml',''}:
            text=p.read_text(encoding='utf-8',errors='replace')
            if re.search(r'(?i)[A-Z]:[\\/]Users[\\/]',text): failures.append(f'Private profile path: {rel}')
            if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text): failures.append(f'Possible credential: {rel}')
            if p.suffix=='.py': ast.parse(text,filename=str(rel))
            if p.suffix.lower() in {'.md','.html'} and 'licenses' not in rel.parts:
                links=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text)
                if p.suffix=='.html': links+=re.findall(r'(?:src|data-light-src|data-dark-src)="([^"]+)"',text)
                for link in links:
                    link=link.strip('<>')
                    if link.startswith(('http:','https:','mailto:','#','data:')): continue
                    if not (p.parent/link.split('#')[0]).exists(): failures.append(f'Broken local link {rel}: {link}')
    notices=json.loads((root/'desktop/licenses/NOTICE_PATHS.json').read_text())
    for item in notices.values():
        p=root/'desktop/licenses'/item['file']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']: failures.append(f'Notice byte mismatch: {item["file"]}')
    meta=json.loads((root/'docs/examples/settings.json').read_text())
    for name,digest in meta['scientific_inputs_sha256'].items():
        if hashlib.sha256((root/'desktop'/name).read_bytes()).hexdigest()!=digest: failures.append(f'Example source hash mismatch: {name}')
    cff=yaml.safe_load((root/'CITATION.cff').read_text())
    if schema:
        import jsonschema
        jsonschema.validate(cff,json.loads(schema.read_text()))
    import tomllib
    version=tomllib.loads((root/'pyproject.toml').read_text())['project']['version']
    assert str(cff['version'])==version==meta['version']=='0.11.0'
    digits=cff['authors'][0]['orcid'].rsplit('/',1)[1].replace('-','')
    total=0
    for d in digits[:-1]: total=(total+int(d))*2
    digit=(12-total%11)%11
    assert digits[-1]==('X' if digit==10 else str(digit))
    assert not json.loads((root/'desktop/release_config.json').read_text())['updates_enabled']
    sys.path.insert(0,str(root/'tools'))
    from generate_examples import generate
    with tempfile.TemporaryDirectory(prefix='fringescope_examples_') as folder:
        target=Path(folder)/'new'
        generated=generate(target)
        for name in ['synthetic_ideal_spectrum_100us.csv','synthetic_ideal_kinetics.csv']:
            np.testing.assert_array_equal(np.loadtxt(target/name,delimiter=',',skiprows=1),np.loadtxt(root/'docs/examples'/name,delimiter=',',skiprows=1))
        assert generated['settings']==meta['settings']
    return dict(status='passed' if not failures else 'failed',files_reviewed=len(files),notice_hashes_checked=len(notices),findings=failures,example_reproduction='numeric arrays identical',cff_schema='passed' if schema else 'not checked',scope='Allowlist, extensions, path/credential patterns, local document links, Python syntax, notice/source hashes, version/ORCID and deterministic example reproduction. Not a full security or dependency license certification.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--cff-schema',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=check(args.root,args.cff_schema)
    with args.output.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
    sys.exit(bool(result['findings']))
