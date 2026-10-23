from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'scripts/record_competition_demo.py').read_text(encoding='utf-8')
source=source.replace("WORK = ROOT / 'outputs/video/source'", "WORK = ROOT / 'iCAN_应用方案/视频/01_screen_recordings/revision'")
source=source.replace('    asyncio.run(voices())','    # Reuse formal narration; this records only real UI operations.')
source=source.replace("ROOT/'docs/examples/songhua/generated.png'", "ROOT/'iCAN_应用方案/视频/02_generated_assets/revision/tower_reference.png'")
source=source.replace("(ROOT/'docs/images').mkdir(parents=True,exist_ok=True)","(WORK/'review').mkdir(parents=True,exist_ok=True)")
source=source.replace("ROOT/'docs/images/workspace.png'", "WORK/'review/workspace.png'")
source=source.replace("青绿群山之间，宋代楼阁临水而立，仙鹤掠过云间，松树与祥云点缀画面，清雅留白，横向山水构图", "青绿群山之间，参考图中的双层古典楼阁临水而立，保留楼阁的木构屋檐与双层形制，仙鹤掠过云间，松树与祥云点缀画面，清雅留白，横向山水构图")
exec(compile(source, str(ROOT/'scripts/record_competition_demo.py'),'exec'),{'__file__':str(ROOT/'scripts/record_competition_demo.py'),'__name__':'__main__'})
