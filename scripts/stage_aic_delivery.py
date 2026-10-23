"""Stage only the authorized delivery; validate no private tokens in the index."""
from pathlib import Path
import subprocess, json, re
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
path=ROOT/'docs/examples/songhua/metadata.json'
m=json.loads(path.read_text(encoding='utf-8'));m['outputType']='postcard'
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Retain exact tracked baselines for changes that were backed up from git.
for rel in ['frontend/package-lock.json','backend/providers/dashscope_qwen_image_provider.py','backend/provider_service.py','frontend/src/App.tsx','frontend/vite.config.ts']:
    baseline=ROOT/'.cache/aic-judge-experience-prechange/git-baseline'/rel
    if not baseline.exists():baseline.parent.mkdir(parents=True,exist_ok=True);baseline.write_bytes(git('show',f'HEAD:{rel}'))
files=['README.md','backend/app.py','backend/prompt_builder.py','backend/provider_service.py','backend/providers/dashscope_qwen_image_provider.py','backend/services/vision_analysis.py','backend/image_analyzer.py','backend/instantstyle_service.py',
 'docs/examples','docs/images/workspace.png','docs/images/aic','docs/AIC_GALLERY_AND_JUDGE_EXPERIENCE_ACCEPTANCE.md','docs/ASSET_DELIVERY_AUDIT.md',
 'frontend/src/App.tsx','frontend/src/components/Navbar.tsx','frontend/src/components/creator/CultureCard.tsx','frontend/src/data/styleLibrary.ts','frontend/src/data/savedCases.ts','frontend/src/pages/Gallery.tsx','frontend/src/pages/AICreator.tsx','frontend/src/pages/Home.tsx','frontend/src/pages/About.tsx','frontend/src/pages/Scenarios.tsx','frontend/src/services/generationService.ts','frontend/vite.config.ts','frontend/package-lock.json',
 '.github/workflows/pages.yml','setup_windows.cmd','start_windows.cmd','stop_windows.cmd','check_environment.cmd',
 'scripts/windows_launcher.ps1','scripts/prepare_style_assets.py','scripts/analyze_generated_case.py','scripts/verify_aic_browser.py','scripts/verify_unconfigured_runtime.py','scripts/verify_static_showcase.py','tests/test_aic_delivery.py']
subprocess.run(['git','add','--',*files],cwd=ROOT,check=True)
keys=[v.encode() for k,v in dotenv_values(ROOT/'backend/.env').items() if v and ('KEY' in k or 'TOKEN' in k or 'SECRET' in k) and len(v)>12]
staged=git('diff','--cached','--name-only','--diff-filter=ACMR').decode().splitlines()
for name in staged:
    if any(part in name.split('/') for part in ['node_modules','venv','.cache']) or name.endswith('.env'):
        raise SystemExit(f'Private file staged: {name}')
    blob=git('show',f':{name}')
    if any(token in blob for token in keys) or re.search(rb'sk-[A-Za-z0-9]{24,}',blob):
        raise SystemExit(f'Sensitive content detected in: {name}')
print(f'Staged {len(staged)} added/modified files; no private keys or dependency/cache directories in staged content.')
# Record largest tracked assets without printing credentials or file contents.
tracked=git('ls-files').decode().splitlines()
large=sorted([( (ROOT/p).stat().st_size,p) for p in tracked if (ROOT/p).is_file()],reverse=True)[:12]
(ROOT/'.cache/aic-tracked-size-audit.json').write_text(json.dumps(large,ensure_ascii=False,indent=2),encoding='utf-8')
