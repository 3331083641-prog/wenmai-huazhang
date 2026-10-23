"""Change the new-draft location through JianYing's regular settings dialog."""
import sys
import time
import ctypes
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import verify_jianying_environment as v

def click(control,x,y):
    packed=(y<<16)|(x&0xffff)
    for message,buttons in [(0x0200,0),(0x0201,1),(0x0202,0)]:
        ctypes.windll.user32.PostMessageW(control.NativeWindowHandle,message,buttons,packed)

if v.input_desktop_state()['locked_or_unavailable']:
    raise RuntimeError('Desktop unavailable')
main=next(w for w in v.windows() if w.Name=='剪映专业版')
ctypes.windll.user32.ShowWindow(main.NativeWindowHandle,9)
ctypes.windll.user32.SetForegroundWindow(main.NativeWindowHandle)
time.sleep(.5)
rectangle=main.BoundingRectangle
main.Click(x=1575,y=30,simulateMove=True)
time.sleep(.4)
menu=v.find_class('MenuWindow')
menu.Click(x=rectangle.left+1575,y=rectangle.top+82,simulateMove=True)
time.sleep(.4)
settings=v.find_class('GlobalSettingDialog_QMLTYPE_621')
settings.Click(x=486,y=190,simulateMove=True)
time.sleep(.4)
dialog=v.find_class('#32770')
edit=dialog.EditControl(searchDepth=3,AutomationId='1152')
edit.GetValuePattern().SetValue(str(v.ROOT/'iCAN_应用方案'/'视频'/'07_jianying'))
dialog.ButtonControl(searchDepth=3,AutomationId='1').GetInvokePattern().Invoke()
time.sleep(.5)
settings=v.find_class('GlobalSettingDialog_QMLTYPE_621')
settings.Click(x=150,y=1015,simulateMove=True)
time.sleep(.5)
v.snapshot('new_draft_location',native=True)
