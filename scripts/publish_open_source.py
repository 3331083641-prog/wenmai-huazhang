"""Local publication helper. Secrets are acquired in memory, never persisted."""
from pathlib import Path
import json, os, re, subprocess, urllib.request, urllib.error

ROOT=Path(__file__).resolve().parents[1]
OWNER='3331083641-prog'
REPO='wenmai-huazhang'

def git(*args):
    p=subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace')
    if p.returncode: raise RuntimeError('Git operation failed: '+args[0]+' '+p.stderr[:400])
    return p.stdout.strip()

def credentials():
    env=os.environ.copy();env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never')
    r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=env,timeout=20)
    values=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
    if r.returncode or not values.get('password'):raise RuntimeError('GitHub credentials unavailable')
    return values['password']

def api(path,data=None,method=None,token=None):
    headers={'Accept':'application/vnd.github+json','User-Agent':'wenmai-publication','X-GitHub-Api-Version':'2022-11-28'}
    if token:headers['Authorization']='Bearer '+token
    body=None if data is None else json.dumps(data).encode('utf-8')
    if body:headers['Content-Type']='application/json'
    req=urllib.request.Request('https://api.github.com'+path,data=body,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def stage():
    if not (ROOT/'.git').exists():git('init','-b','main')
    git('config','user.name','PengYi Wen')
    git('config','user.email','246807796+3331083641-prog@users.noreply.github.com')
    files=['.gitignore','README.md','LICENSE','THIRD_PARTY_NOTICES.md']
    for directory in ['docs','licenses','frontend/src','frontend/public','backend/style_refs','assets','backend/providers','backend/services']:
        files.extend(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files.extend(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'backend').glob('*.py'))
    files.extend(['backend/.env.example','backend/requirements.txt','backend/requirements-instantstyle.txt','frontend/.env.example','frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/index.html','frontend/metadata.json','frontend/.gitignore','scripts/start_backend.ps1','scripts/start_frontend.ps1'])
    for i in range(0,len(files),75):git('add','--',*files[i:i+75])
    staged=git('ls-files').splitlines()
    bad=[]
    patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'github_pat_[A-Za-z0-9_]{20,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    for name in staged:
        p=ROOT/name
        if p.name=='.env' or (p.name.startswith('.env.') and p.name!='.env.example') or any(part in ('node_modules','venv','.cache','outputs','uploads','logs') for part in p.relative_to(ROOT).parts):bad.append(name)
        if p.suffix.lower() not in ('.png','.jpg','.jpeg','.webm','.mp4','.pdf'):
            blob=p.read_bytes()
            if any(re.search(pattern,blob) for pattern in patterns):bad.append(name)
    if bad:raise RuntimeError('Public-file audit requires correction: '+', '.join(bad))
    if git('status','--porcelain','--untracked-files=no'):git('commit','-m','Open source Wenmai Huazhang with real examples and portable setup')
    print(json.dumps({'public_files':len(staged),'commit':git('rev-parse','--short','HEAD'),'secret_audit':'passed'},ensure_ascii=False),flush=True)

def publish():
    token=credentials()
    user=api('/user',token=token)
    if user['login']!=OWNER:raise RuntimeError('Unexpected GitHub account')
    try:repo=api(f'/repos/{OWNER}/{REPO}',token=token)
    except urllib.error.HTTPError as e:
        if e.code!=404:raise RuntimeError('GitHub repository lookup failed')
        repo=api('/user/repos',{'name':REPO,'description':'纹脉华章｜传统文化视觉智能创作与文创应用平台 · React + FastAPI + Qwen Image + Qwen3-VL','private':False,'auto_init':False,'has_issues':True,'has_wiki':False},token=token)
    if repo.get('private'):raise RuntimeError('Existing repository is private; visibility was not changed')
    if 'origin' not in git('remote').splitlines():git('remote','add','origin',f'https://github.com/{OWNER}/{REPO}.git')
    if git('remote','get-url','origin')!=f'https://github.com/{OWNER}/{REPO}.git':raise RuntimeError('Unexpected existing remote')
    git('push','-u','origin','main')
    api(f'/repos/{OWNER}/{REPO}/topics',{'names':['traditional-culture','generative-ai','qwen','react','fastapi','cultural-heritage']},method='PUT',token=token)
    repo=api(f'/repos/{OWNER}/{REPO}',token=token)
    print(json.dumps({'repository':repo['html_url'],'public':not repo['private'],'default_branch':repo['default_branch']},ensure_ascii=False),flush=True)

if __name__=='__main__':
    import sys
    stage()
    if '--push' in sys.argv:publish()
