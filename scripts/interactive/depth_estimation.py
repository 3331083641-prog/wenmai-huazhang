"""Pinned, local-only relative depth; network installation is a separate command."""
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from PIL import Image
from image_geometry import image_depth

ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/'models/interactive-models.json').read_text(encoding='utf-8'))['depth']


def model_directory():
    return Path(os.environ.get('WENMAI_DEPTH_MODEL_DIR') or ROOT/SPEC['directory'])


def verify_local_model():
    folder=model_directory()
    for name,expected in SPEC['files'].items():
        target=folder/name
        if not target.is_file():
            raise RuntimeError('本地深度模型未安装；请运行 scripts/setup_interactive_models.py。后台不会下载或静默替换模型。')
        if expected and hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('本地深度权重校验失败，请重新安装固定版本。')
    return folder


def run_local_model(image_path, folder):
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    torch.set_num_threads(min(4,os.cpu_count() or 1))
    use_cuda=torch.cuda.is_available() and torch.cuda.mem_get_info()[0]>1_500_000_000
    device='cuda' if use_cuda else 'cpu'
    processor=AutoImageProcessor.from_pretrained(str(folder),local_files_only=True,use_fast=False)
    model=AutoModelForDepthEstimation.from_pretrained(str(folder),local_files_only=True,
        trust_remote_code=False,use_safetensors=True).to(device).eval()
    with Image.open(image_path) as source:
        image=source.convert('RGB')
    inputs=processor(images=image,return_tensors='pt').to(device)
    with torch.inference_mode():
        output=model(**inputs)
    depth=processor.post_process_depth_estimation(output,target_sizes=[(image.height,image.width)])[0]['predicted_depth']
    return depth.detach().float().cpu().numpy().astype(np.float32)


def estimate_image_depth(image_path, plan=None):
    mode=os.getenv('WENMAI_DEPTH_MODE','model').strip().lower()
    if mode=='geometry':
        return image_depth(image_path,(plan or {}).get('hotspots'),(plan or {}).get('scene_kind','flat_artwork')), {
            'source':'image_geometry_v1','modelUsed':False,'approximate':True}
    if mode!='model':raise RuntimeError('WENMAI_DEPTH_MODE 只支持 model 或显式 geometry。')
    folder=verify_local_model()
    digest=hashlib.sha256(Path(image_path).read_bytes()).hexdigest()
    cache=ROOT/'.cache/interactive-depth'/f"{digest}-{SPEC['revision'][:12]}-v1.npz"
    if cache.is_file():
        with np.load(cache,allow_pickle=False) as saved:depth=saved['depth'].copy()
    else:
        depth=run_local_model(image_path,folder)
        if not np.isfinite(depth).all() or float(np.ptp(depth))<1e-5:
            raise RuntimeError('本图深度推理结果为空、非数值或没有层次，拒绝发布画境。')
        cache.parent.mkdir(parents=True,exist_ok=True)
        temporary=cache.with_suffix('.tmp.npz');np.savez_compressed(temporary,depth=depth);temporary.replace(cache)
    return depth, {'source':'depth-anything-v2-small','modelUsed':True,'approximate':True,
        'repository':SPEC['repository'],'revision':SPEC['revision'],
        'weightsSha256':SPEC['files']['model.safetensors'],'license':SPEC['license'],
        'inputImageSha256':digest}
