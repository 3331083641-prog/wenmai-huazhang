"""Small, staged helpers for the already-created native Jianying task draft.

Default invocation only inspects the application's own windows. GUI changes
require --ready. Export additionally requires --source-verified, after the
operator has reopened/refreshed this task draft and inspected a changed frame.
No AppData, registry, draft JSON, deletion, paid feature, or publishing action.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_jianying_environment as v

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--action', choices=['inspect', 'open-export', 'configure-export', 'export', 'status'], default='inspect')
parser.add_argument('--ready', action='store_true')
parser.add_argument('--source-verified', action='store_true')
parser.add_argument('--video', type=Path, default=v.ROOT / 'iCAN_应用方案' / '视频' / '06_ffmpeg' / 'ffmpeg_master.mp4')
parser.add_argument('--output-name', default='纹脉华章_2026_iCAN_演示视频')
parser.add_argument('--expand-codecs', action='store_true')
parser.add_argument('--label', default='reexport_inspect')
args = parser.parse_args()

project = v.ROOT.resolve()
source = args.video.resolve()
if not source.is_relative_to(project) or not source.is_file():
    raise ValueError('Source must be an existing file inside the project')
if Path(args.output_name).name != args.output_name or '.' in args.output_name:
    raise ValueError('Output name must be a simple extension-free filename')

print(json.dumps({
    'desktop': v.input_desktop_state(),
    'source': str(source), 'source_size': source.stat().st_size,
    'source_mtime': source.stat().st_mtime,
    'own_windows': [{'name': w.Name, 'class': w.ClassName, 'rectangle': str(w.BoundingRectangle)} for w in v.windows()],
}, ensure_ascii=False))

if args.action in ['inspect', 'status']:
    v.snapshot(args.label, native=True)
    sys.exit(0)
if not args.ready:
    raise RuntimeError('Wait for the explicit final-master READY notification, then pass --ready')
if v.input_desktop_state()['locked_or_unavailable']:
    raise RuntimeError('Desktop unavailable; no input sent')

def editor():
    return next(w for w in v.windows() if w.Name == '剪映专业版' and w.ClassName.startswith('MainWindow'))

def export_dialog():
    return next(w for w in v.windows() if w.Name.startswith('导出-') and '纹脉华章_iCAN_提交版精修' in w.Name)

def paste(text):
    v.auto.SetClipboardText(text)
    v.auto.SendKeys('{Ctrl}a{Ctrl}v{Tab}', waitTime=.2)

if args.action == 'open-export':
    w = editor()
    # Native right-aligned Export button, previously verified in this draft.
    w.Click(x=w.BoundingRectangle.width() - 197, y=28, simulateMove=True)
    time.sleep(.5)
    export_dialog()
elif args.action == 'configure-export':
    d = export_dialog()
    if d.BoundingRectangle.width() != 960 or d.BoundingRectangle.height() != 1080:
        raise RuntimeError('Export layout changed; inspect the screenshot before using coordinates')
    d.Click(x=800, y=152, simulateMove=True)
    paste(args.output_name)
    d.Click(x=913, y=207, simulateMove=True)
    time.sleep(.3)
    chooser = v.find_class('#32770')
    if chooser.Name != '请选择导出路径':
        raise RuntimeError('Unexpected native file dialog')
    output_dir = v.ROOT / 'iCAN_应用方案' / '视频' / '09_final'
    if not output_dir.is_dir():
        raise FileNotFoundError(output_dir)
    chooser.EditControl(searchDepth=4, AutomationId='1152').GetValuePattern().SetValue(str(output_dir))
    chooser.ButtonControl(searchDepth=4, AutomationId='1').GetInvokePattern().Invoke()
    time.sleep(.3)
    if args.expand_codecs:
        export_dialog().Click(x=737, y=687, simulateMove=True)
elif args.action == 'export':
    if not args.source_verified:
        raise RuntimeError('Reopen/refresh the native task draft and inspect a changed frame before --source-verified')
    d = export_dialog()
    if d.BoundingRectangle.width() != 960 or d.BoundingRectangle.height() != 1080:
        raise RuntimeError('Unexpected export layout')
    d.Click(x=762, y=1040, simulateMove=True)
    time.sleep(8)

v.snapshot(args.label, native=True)
