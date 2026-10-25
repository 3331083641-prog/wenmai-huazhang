"""Bounded image-grounded review; never executes a model's code or arbitrary tools."""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import shutil
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[2]
POLICY_PATH=Path(__file__).with_name('review_policy.json')
POLICY=json.loads(POLICY_PATH.read_text(encoding='utf-8'))
CAMERA_PARAMETERS={'depth_amplitude','yaw_limit_deg','pitch_limit_deg','framing_margin'}
TUNING_DEFAULTS={'haze':.10,'mist':.26,'ripple':1.0,'sway':1.0,'subject_relief':.035,'cutout_motion':.05,'paper_flex':0.0}
REFERENCE_CASES={'zhuxianzhen':'zhuxianzhen-ruimao','bianxiu':'bianxiu-xiutu',
                 'songhua':'songhua-yunhe','qinghua':'qinghua-dieyun','jianzhi':'jianzhi-linghu'}


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temporary.replace(path)


def portable_record(value):
    """Public case reports keep project-relative evidence locations."""
    if isinstance(value,dict):return {key:portable_record(item) for key,item in value.items()}
    if isinstance(value,list):return [portable_record(item) for item in value]
    if isinstance(value,str):
        for prefix in (str(ROOT)+'\\',ROOT.as_posix()+'/'):
            if value.startswith(prefix):return value[len(prefix):].replace('\\','/')
    return value


def evidence_intact(frame):
    try:
        path=Path(frame['path'])
        if not path.is_absolute():path=ROOT/path
        path.resolve().relative_to(ROOT.resolve())
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==frame['sha256']
    except (KeyError,TypeError,ValueError,OSError):return False


def validate_parameters(parameters):
    if not isinstance(parameters,dict) or len(parameters)>4:
        raise ValueError('最多接受四个白名单参数')
    for name,value in parameters.items():
        limits=POLICY['parameterRanges'].get(name)
        if (limits is None or isinstance(value,bool) or not isinstance(value,(int,float))
                or not math.isfinite(value) or not limits[0]<=value<=limits[1]):
            raise ValueError('复审参数不在白名单或允许范围内')
    return dict(parameters)


def apply_parameters(manifest,parameters):
    result=deepcopy(manifest)
    for name,value in validate_parameters(parameters).items():
        result.setdefault('camera' if name in CAMERA_PARAMETERS else 'tuning',{})[name]=value
    provenance=result.setdefault('provenance',{})
    provenance.pop('asset_revision',None)
    provenance['asset_revision']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
    return result


def review_score(review):
    return round(sum(float(review['dimensions'][key])*weight for key,weight in POLICY['weights'].items()),2)


def manifest_fingerprint(manifest):
    # JS parses JSON 1.0 as 1; identical numeric values must have identical hashes.
    def normalized(value):
        if isinstance(value,dict):return {key:normalized(item) for key,item in value.items()}
        if isinstance(value,list):return [normalized(item) for item in value]
        if type(value) is float and value.is_integer():return int(value)
        return value
    return hashlib.sha256(json.dumps(normalized(manifest),sort_keys=True,ensure_ascii=False,
        separators=(',',':')).encode()).hexdigest()


def verify_capture(manifest,evidence):
    result=deepcopy(evidence)
    result.setdefault('checks',{})['manifest_matches']=result.get('manifest_sha256')==manifest_fingerprint(manifest)
    result['checks']['passed']=bool(result['checks'].get('passed') and result['checks']['manifest_matches'])
    return result


def review_passes(review,checks):
    return bool(checks.get('passed') and review.get('passed') and
        review_score(review)>=POLICY['targetScore'] and
        review['dimensions']['fidelity']>=POLICY['minimumFidelity'] and
        review['dimensions']['occlusion']>=POLICY['minimumOcclusion'] and
        not any(issue.get('severity') in ('blocker','major') for issue in review.get('issues',[])))


@contextmanager
def _restore_manifest(path,get_best):
    try:
        yield
    finally:
        write_json(path,get_best())


def optimize_candidates(world_dir,capture,reviewer,*,max_rounds=3,progress=None,feedback_handler=None):
    """Inject actual browser/API boundaries; unit tests do not spend API credits.

    Asset pixels remain immutable during parameter search. On every exit restore
    the best evidenced manifest, including when the API fails mid-search.
    """
    world_dir=Path(world_dir);manifest_path=world_dir/'world.json'
    original=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    backup=ROOT/'.cache/world-review-backups'/str(original.get('slug','case'))/datetime.now().strftime('%Y%m%d-%H%M%S-%f')/'world.json'
    write_json(backup,original)
    current=deepcopy(original);best=deepcopy(original);best_index=None;best_score=None
    history=[];error=None;stop='round_limit'
    with _restore_manifest(manifest_path,lambda:best):
        for index in range(min(POLICY['maxRounds'],max(1,int(max_rounds)))):
            write_json(manifest_path,current)
            if progress:progress(index)
            try:
                evidence=capture(index,deepcopy(current))
                if not evidence.get('checks',{}).get('passed'):
                    raise RuntimeError('browser checks failed; no cloud request sent')
                review=reviewer(evidence,deepcopy(history))
                score=review_score(review)
                checks=evidence.get('checks',{})
                valid=bool(checks.get('passed')) and not any(
                    issue.get('severity') in ('blocker','major') for issue in review.get('issues',[]))
                passed=review_passes(review,checks)
                entry={'round':index,'parameters':{
                    **{k:current.get('camera',{}).get(k) for k in CAMERA_PARAMETERS},
                    **{k:current.get('tuning',{}).get(k,v) for k,v in TUNING_DEFAULTS.items()}},
                    'score':score,'review':review,'checks':checks,'passed':passed,
                    'evidence':evidence}
                history.append(entry)
                # Never trade away the original form merely to increase a total score.
                baseline=history[0]['review']['dimensions']
                fidelity_ok=review['dimensions']['fidelity']>=baseline['fidelity']-1
                occlusion_ok=review['dimensions']['occlusion']>=baseline['occlusion']-2
                if valid and fidelity_ok and occlusion_ok and (best_score is None or score>best_score):
                    best=deepcopy(current);best_index=index;best_score=score
                if passed:
                    stop='target_reached';break
                try:parameters=validate_parameters(review.get('suggestedParameters',{}))
                except ValueError:
                    entry['rejectedSuggestion']='参数越界、数量超限或包含未授权字段';stop='invalid_suggestion';break
                candidate=apply_parameters(current,parameters)
                content_changed=False
                if feedback_handler:
                    candidate,content_changed=feedback_handler(review,candidate,index)
                if not content_changed and (not parameters or candidate.get('camera')==current.get('camera') and candidate.get('tuning')==current.get('tuning')):
                    stop='no_actionable_change';break
                current=candidate
            except Exception as exc:
                # External errors can contain credentials; persist the class only.
                error=type(exc).__name__;stop='review_unavailable';break
    chosen=next((entry for entry in history if entry['round']==best_index),None)
    status=('unverified' if error else 'approved' if chosen and chosen['passed'] else 'needs_review')
    baseline_score=history[0]['score'] if history else None
    return {'schemaVersion':1,'status':status,'rounds':len(history),'selectedRound':best_index,
        'baselineScore':baseline_score,'finalScore':best_score,'improved':bool(
            best_score is not None and baseline_score is not None and best_score>baseline_score),
        'stopReason':stop,'errorType':error,'history':history,'originalManifestBackup':str(backup.relative_to(ROOT)),
        'scoringNote':'DeepSeek视觉评分是主观评价；程序检查单独保存，不能视为客观准确率。'}


def review_enabled():
    return os.getenv('DEEPSEEK_REVIEW_ENABLED','false').lower().strip() in ('true','1','yes','on')


def _fingerprint(paths):
    digest=hashlib.sha256()
    for path in paths:digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def reference_bundle(capture_func,base_url):
    """Five immutable original works captured by exactly the same browser path."""
    paths=[Path(__file__).with_name('capture_world.py'),
        *sorted((ROOT/'frontend/src/features/painting-world').glob('*.ts')),
        *sorted((ROOT/'frontend/src/features/painting-world').glob('*.tsx'))]
    for style in REFERENCE_CASES:
        paths.extend([ROOT/f'docs/examples/{style}/generated.png',
                      *sorted((ROOT/f'frontend/public/interactive/{style}/world').glob('*'))])
    signature=_fingerprint(paths)
    directory=ROOT/'.cache/world-review-references'/signature[:20]
    index=directory/'index.json'
    if index.is_file():
        result=json.loads(index.read_text(encoding='utf-8'))
        if result.get('fingerprint')==signature and all(Path(frame['path']).is_file() and
                hashlib.sha256(Path(frame['path']).read_bytes()).hexdigest()==frame['sha256']
                for row in result['works'] for frame in row['capture']['frames']):
            return result
    rows=[]
    for style,case in REFERENCE_CASES.items():
        expected=json.loads((ROOT/f'frontend/public/interactive/{style}/world/world.json').read_text(encoding='utf-8-sig'))
        evidence=verify_capture(expected,capture_func(case,directory/style,base_url=base_url))
        if not evidence['checks'].get('passed'):
            raise RuntimeError('原五件参照作品的实际浏览器检查未通过')
        rows.append({'styleId':style,'caseId':case,'sourceImageSha256':hashlib.sha256(
            (ROOT/f'docs/examples/{style}/generated.png').read_bytes()).hexdigest(),'capture':evidence})
    result={'fingerprint':signature,'works':rows}
    write_json(index,result);return result


def _preview_url():
    explicit=os.getenv('WENMAI_REVIEW_FRONTEND_URL','').strip()
    if explicit:return explicit
    try:
        state=json.loads((ROOT/'.cache/windows_launcher/processes.json').read_text(encoding='utf-8-sig'))
        port=int(state.get('webPort',5173))
    except (OSError,ValueError,TypeError):port=5173
    return f'http://127.0.0.1:{port}'


@contextmanager
def review_lock(timeout=600):
    """Serialize GPU/browser reviews across backend worker processes."""
    path=ROOT/'.cache/world-review.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0,2)
        if not stream.tell():stream.write(b'0');stream.flush()
        began=time.monotonic()
        while True:
            try:
                stream.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic()-began>=timeout:raise TimeoutError('review queue timeout')
                time.sleep(.5)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def reserve_review_call():
    """Called inside the global review lock; failed HTTP attempts also consume a slot."""
    path=ROOT/'.cache/world-review-daily-budget.json'
    today=datetime.now().date().isoformat()
    try:value=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):value={}
    if value.get('date')!=today:value={'date':today,'attemptedCalls':0}
    limit=min(100,max(1,int(os.getenv('DEEPSEEK_DAILY_REVIEW_LIMIT','24'))))
    if int(value.get('attemptedCalls',0))>=limit:raise RuntimeError('daily review call budget exhausted')
    value['attemptedCalls']=int(value.get('attemptedCalls',0))+1
    write_json(path,value)


def review_world(case_id,style_id,*,max_rounds=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}',case_id) or style_id not in REFERENCE_CASES:
        raise ValueError('无效案例ID或风格')
    if not review_enabled():return _review_world(case_id,style_id,max_rounds=max_rounds)
    with review_lock():
        return _review_world(case_id,style_id,max_rounds=max_rounds)


def review_dependencies(case,world):
    files=_fingerprint([POLICY_PATH,Path(__file__),
        Path(__file__).with_name('capture_world.py'),ROOT/'backend/services/deepseek_review.py',
        case/'interaction-analysis.json',
        case/'experience.json',
        *sorted(p for p in world.glob('*') if p.is_file() and p.name!='world.json'),
        *(ROOT/f'docs/examples/{style}/generated.png' for style in REFERENCE_CASES),
        *(p for style in REFERENCE_CASES for p in sorted((ROOT/f'frontend/public/interactive/{style}/world').glob('*')) if p.is_file()),
        *sorted((ROOT/'frontend/src/features/painting-world').glob('*.ts')),
        *sorted((ROOT/'frontend/src/features/painting-world').glob('*.tsx'))])
    metadata=json.loads((case/'metadata.json').read_text(encoding='utf-8-sig'))
    metadata.pop('qualityReview',None)
    return hashlib.sha256((files+json.dumps(metadata,sort_keys=True,ensure_ascii=False)).encode()).hexdigest()


def restore_case_snapshot(case,output,world):
    selected=manifest_fingerprint(json.loads((world/'world.json').read_text(encoding='utf-8-sig')))
    for snapshot in sorted(output.glob('round-*/case-snapshot')):
        if (snapshot/'world.json').is_file() and manifest_fingerprint(
                json.loads((snapshot/'world.json').read_text(encoding='utf-8-sig')))==selected:
            for name in ('metadata.json','experience.json','interaction-analysis.json'):
                if (snapshot/name).is_file():shutil.copy2(snapshot/name,case/name)
            if (snapshot/'world-assets').is_dir():
                shutil.copytree(snapshot/'world-assets',world,dirs_exist_ok=True)
            return


def _review_world(case_id,style_id,*,max_rounds=None):
    """Production entry called after local Qwen/depth and metadata are ready."""
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from services.deepseek_review import ReviewClient
    from capture_world import capture_world
    case=ROOT/'docs/examples'/case_id
    world=ROOT/'frontend/public/interactive'/case_id/'world'
    output=ROOT/'.cache/world-reviews'/case_id/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    report_file=case/'quality-review.json'
    if not review_enabled():
        result={'status':'disabled','rounds':0,'improved':False}
        metadata=json.loads((case/'metadata.json').read_text(encoding='utf-8-sig'))
        metadata['qualityReview']={**result,'reportFile':'quality-review.json'}
        write_json(case/'metadata.json',metadata)
        write_json(report_file,result);return result
    client=ReviewClient.from_env()
    artifact=json.loads((case/'interaction-analysis.json').read_text(encoding='utf-8-sig'))
    actual_image_sha=hashlib.sha256((case/'generated.png').read_bytes()).hexdigest()
    current_world=json.loads((world/'world.json').read_text(encoding='utf-8-sig'))
    if (actual_image_sha!=artifact['inputImageSha256'] or
            current_world.get('provenance',{}).get('source_image_sha256')!=actual_image_sha):
        raise RuntimeError('当前图像与本地解析或画境来源哈希不一致，禁止云端复审')
    dependencies=review_dependencies(case,world)
    if report_file.is_file():
        cached=json.loads(report_file.read_text(encoding='utf-8-sig'))
        if (cached.get('status') in ('approved','needs_review') and cached.get('sourceImageSha256')==actual_image_sha
                and cached.get('dependencyFingerprint')==dependencies and cached.get('styleId')==style_id and cached.get('reviewerModel')==client.model
                and cached.get('reviewerProvider')==getattr(client,'provider','bailian')
                and cached.get('roundLimit')==int(max_rounds or client.max_calls)
                and cached.get('selectedManifestSha256')==manifest_fingerprint(current_world)
                and all(evidence_intact(f)
                    for row in cached.get('history',[]) for f in row['evidence']['frames'])):
            cached['reused']=True
            metadata=json.loads((case/'metadata.json').read_text(encoding='utf-8-sig'))
            metadata['qualityReview']={key:cached.get(key) for key in (
                'status','rounds','selectedRound','baselineScore','finalScore','improved','reviewerModel')}
            metadata['qualityReview']['reportFile']='quality-review.json';write_json(case/'metadata.json',metadata)
            return cached
    base_url=_preview_url()
    references=reference_bundle(capture_world,base_url)
    # Matching-style three-view reference plus one real side-view of every other style.
    reference_images=[]
    for row in references['works']:
        frames=row['capture']['frames']
        selected=frames[:3] if row['styleId']==style_id else frames[1:2]
        reference_images.extend({'label':f"原五件参照/{row['styleId']}/{f['label']}",'path':Path(f['path'])} for f in selected)
    def capture(index,manifest):
        snapshot=output/f'round-{index}'/'case-snapshot';snapshot.mkdir(parents=True,exist_ok=True)
        for name in ('metadata.json','experience.json','interaction-analysis.json'):
            shutil.copy2(case/name,snapshot/name)
        write_json(snapshot/'world.json',manifest)
        shutil.copytree(world,snapshot/'world-assets',dirs_exist_ok=True)
        result=verify_capture(manifest,capture_world(case_id,output/f'round-{index}',base_url=base_url))
        result['caseSnapshotDir']=str(snapshot)
        return result
    def reviewer(evidence,history):
        current_artifact=json.loads((case/'interaction-analysis.json').read_text(encoding='utf-8-sig'))
        current=json.loads((world/'world.json').read_text(encoding='utf-8-sig'))
        context={'task':'严格复审并仅建议允许参数，不代写热点章节或改原图',
            'requirements':POLICY['requirements'],'parameterRanges':POLICY['parameterRanges'],
            'thresholds':{k:POLICY[k] for k in ('targetScore','minimumFidelity','minimumOcclusion')},
            'caseId':case_id,'styleId':style_id,'sourceImageSha256':artifact['inputImageSha256'],
            'referenceFingerprint':references['fingerprint'],'referenceCases':list(REFERENCE_CASES.values()),
            'localQwenAnalysis':current_artifact['analysis'],'browserChecks':evidence['checks'],
            'worldCamera':current['camera'],'worldTuning':current.get('tuning',{}),
            'renderLayers':[{k:cut.get(k) for k in ('id','depth','completeSubject','negativeSpacePreserved','reliefSource','bbox_norm')}
                            for cut in current.get('cutouts',[])],
            'worldProvenance':{k:v for k,v in current.get('provenance',{}).items() if k not in ('depth_inference',)},
            'previousRounds':[{'round':h['round'],'score':h['score'],'review':h['review']} for h in history]}
        images=[{'label':'本件目标原图（判断保真依据）','path':case/'generated.png'},*reference_images,
            *({'label':f"本件当前画境/{f['label']}",'path':Path(f['path'])} for f in evidence['frames'])]
        reserve_review_call()
        return client.review(context,images)
    def repair_content(review,candidate,index):
        feedback=[issue for issue in review.get('issues',[]) if issue.get('severity') in ('major','blocker')
                  and re.search(r'STORY|NARRATIVE|TEXT|CULTUR|FACT|CONTENT|SEMANTIC_MISMATCH|HOTSPOT|COORDINAT|LOCATION',issue.get('code',''),re.I)]
        if not feedback or index>=min(int(max_rounds or client.max_calls),3)-1:return candidate,False
        from services.interaction_plan import InteractionPlanService,assemble_experience
        from ingest_case import STYLES
        points=any(re.search(r'HOTSPOT|COORDINAT|LOCATION',issue.get('code',''),re.I) for issue in feedback)
        local=InteractionPlanService()
        if points:
            updated=local.refine_hotspots(case/'generated.png',STYLES[style_id],case/'interaction-analysis.json',feedback)
            import subprocess
            env=dict(os.environ);env['DEEPSEEK_REVIEW_ENABLED']='false'
            rebuilt=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/interactive/ingest_case.py'),
                '--refresh',case_id],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
            if rebuilt.returncode:raise RuntimeError('本地热点重定位后的资产重建未通过')
            next_world=json.loads((world/'world.json').read_text(encoding='utf-8-sig'))
            next_world['camera'].update({k:v for k,v in candidate['camera'].items() if k in CAMERA_PARAMETERS})
            next_world.setdefault('tuning',{}).update(candidate.get('tuning',{}))
            candidate=next_world
        else:
            updated=local.refine_narrative(case/'generated.png',STYLES[style_id],case/'interaction-analysis.json',feedback)
        from PIL import Image
        with Image.open(case/'generated.png') as image:size=image.size
        draft=assemble_experience(case_id,style_id,STYLES[style_id],size,updated)
        write_json(case/'experience.json',draft)
        metadata=json.loads((case/'metadata.json').read_text(encoding='utf-8-sig'))
        metadata['artworkTitle']=draft['title'];write_json(case/'metadata.json',metadata)
        candidate['title']=draft['title']
        candidate.setdefault('provenance',{})['local_content_sha256']=hashlib.sha256((case/'interaction-analysis.json').read_bytes()).hexdigest()
        return apply_parameters(candidate,{}),True
    result=None
    try:
        result=optimize_candidates(world,capture,reviewer,max_rounds=max_rounds or client.max_calls,feedback_handler=repair_content)
    finally:
        restore_case_snapshot(case,output,world)
    result.update({'caseId':case_id,'styleId':style_id,'roundLimit':int(max_rounds or client.max_calls),'sourceImageSha256':artifact['inputImageSha256'],
        'referenceFingerprint':references['fingerprint'],'reviewerModel':client.model,
        'reviewerProvider':getattr(client,'provider','bailian'),'dependencyFingerprint':review_dependencies(case,world),
        'selectedManifestSha256':manifest_fingerprint(json.loads((world/'world.json').read_text(encoding='utf-8-sig'))),
        'policySha256':hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        'completedAt':datetime.now(timezone.utc).isoformat(),
        'requestCount':client.call_count,'usage':client.usage})
    write_json(report_file,portable_record(result));write_json(output/'result.json',result)
    metadata=json.loads((case/'metadata.json').read_text(encoding='utf-8-sig'))
    metadata['qualityReview']={key:result[key] for key in (
        'status','rounds','selectedRound','baselineScore','finalScore','improved','reviewerModel')}
    metadata['qualityReview']['reportFile']='quality-review.json'
    write_json(case/'metadata.json',metadata)
    return result


if __name__=='__main__':
    import argparse,sys
    from dotenv import load_dotenv
    load_dotenv(Path(os.getenv('WENMAI_ENV_FILE') or ROOT/'backend/.env'),encoding='utf-8-sig',override=False)
    parser=argparse.ArgumentParser(description='显式执行已配置供应商的 DeepSeek 视觉复审，可能产生 API 费用')
    parser.add_argument('--case',required=True);parser.add_argument('--style',required=True,choices=list(REFERENCE_CASES))
    args=parser.parse_args()
    if not args.case or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for c in args.case):
        parser.error('无效案例ID')
    value=review_world(args.case,args.style)
    print(json.dumps({k:v for k,v in value.items() if k!='history'},ensure_ascii=False))
