"""Canonical cultural showcase assets; animal experiment refs are separate."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
STYLES=('zhuxianzhen','bianxiu','songhua','qinghua','jianzhi')
def prepare():
    for style in STYLES:
        source=ROOT/'assets/style_refs'/f'{style}.png'
        if not source.is_file(): raise FileNotFoundError(f'Missing canonical style asset: {style}')
        for folder in ['backend/style_refs','frontend/public']:
            target=ROOT/folder/f'{style}.png'
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or source.read_bytes()!=target.read_bytes(): shutil.copy2(source,target)
    print('Five canonical style showcase assets synchronized; experiment references untouched.')
if __name__=='__main__': prepare()
