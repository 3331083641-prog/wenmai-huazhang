"""Package only the verified depth model and its license for release delivery."""
from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/interactive'))
from depth_estimation import SPEC,verify_local_model


def main():
    folder=verify_local_model();output=ROOT/'release';output.mkdir(exist_ok=True)
    target=output/'wenmai-depth-anything-v2-small-20261025.zip'
    prefix='depth-anything-v2-small/'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in SPEC['files']:archive.write(folder/name,prefix+name)
        archive.write(ROOT/'licenses/Apache-2.0.txt',prefix+'LICENSE.txt')
        archive.writestr(prefix+'WENMAI_SOURCE.json',json.dumps(SPEC,ensure_ascii=False,indent=2))
        archive.writestr(prefix+'INSTALL.txt','Extract this directory to <project>/.cache/models/depth-anything-v2-small/\n'
            'Then run: backend/venv/Scripts/python.exe scripts/setup_interactive_models.py --check\n'
            'Only the depth model is included. Ollama Qwen3-VL is installed separately.\n')
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (output/'wenmai-depth-model-sha256.txt').write_text(digest+'  '+target.name+'\n',encoding='utf-8')
    print(target.name,str(target.stat().st_size)+' bytes',digest)


if __name__=='__main__':main()
