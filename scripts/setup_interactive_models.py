"""Install the pinned local depth model explicitly; background jobs never download."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import requests

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proxy',help='Optional HTTP(S) proxy for this download only')
    parser.add_argument('--check',action='store_true',help='Verify local files without network')
    args=parser.parse_args()
    spec=json.loads((ROOT/'models/interactive-models.json').read_text(encoding='utf-8'))['depth']
    folder=ROOT/spec['directory'];folder.mkdir(parents=True,exist_ok=True)
    session=requests.Session()
    if args.proxy:session.proxies.update({'http':args.proxy,'https':args.proxy})
    checks={}
    for name,expected in spec['files'].items():
        target=folder/name
        actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        if not target.is_file() or (expected and actual!=expected):
            if args.check:raise SystemExit('Model file missing or hash mismatch: '+name)
            url=f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{name}?download=true&timestamp={int(time.time())}"
            print('Downloading '+name,flush=True)
            temporary=target.with_suffix(target.suffix+'.part')
            with session.get(url,stream=True,timeout=(20,120)) as response:
                response.raise_for_status()
                with temporary.open('wb') as output:
                    for chunk in response.iter_content(1024*1024):output.write(chunk)
            actual=hashlib.sha256(temporary.read_bytes()).hexdigest()
            if expected and actual!=expected:raise SystemExit('Downloaded hash mismatch: '+name)
            os.replace(temporary,target)
        checks[name]={'bytes':target.stat().st_size,'sha256':actual}
        print('Verified '+name+' '+str(target.stat().st_size)+' bytes',flush=True)
    (folder/'installation.json').write_text(json.dumps({'repository':spec['repository'],'revision':spec['revision'],
        'license':spec['license'],'files':checks},indent=2),encoding='utf-8')
    print('Local depth model ready. No cloud inference is used.')


if __name__=='__main__':main()
