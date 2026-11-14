"""Losslessly package an approved GLB for the gallery. No geometry or textures are changed.

Usage: python scripts/pack-pavilion.py D:/Design/wenmai_master_pavilion.glb
Only run after model audit and browser acceptance. Commit all parts and model.json together.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,shutil,datetime

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path)
args=parser.parse_args()
project=Path(__file__).resolve().parents[1]
dest=project/'frontend/public/models/pavilion-v15'
if dest.exists():
 backup=project/'.work/model-backups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 shutil.copytree(dest,backup)
dest.mkdir(parents=True,exist_ok=True)
parts=[];digest=hashlib.sha256();total=0
with args.source.open('rb') as source:
 if source.read(4)!=b'glTF':raise ValueError('Source must be a GLB')
 source.seek(0)
 while block:=source.read(80*1024*1024):
  name=f'pavilion-v15.part{len(parts)+1}.bin'
  compressed=gzip.compress(block,compresslevel=9,mtime=0)
  assert gzip.decompress(compressed)==block
  (dest/name).write_bytes(compressed);digest.update(block);total+=len(block)
  parts.append(dict(url=name,bytes=len(block),compressedBytes=len(compressed),sha256=hashlib.sha256(block).hexdigest()))
(dest/'model.json').write_text(json.dumps(dict(version='v15-gallery-access',bytes=total,sha256=digest.hexdigest(),parts=parts),indent=2),encoding='utf8')
print(f'{len(parts)} independent gzip parts; {total:,} original bytes; SHA256 {digest.hexdigest()}')
