"""Targeted JianYing launch, accessibility and project-directory verification."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'iCAN_应用方案' / '视频' / '08_review'
REVIEW.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / '.cache' / 'publication_tools'))
import uiautomation as auto
from PIL import ImageGrab, Image

EXE = Path(r'D:\JianyingPro\11.5.3.14501\JianyingPro.exe')

def input_desktop_state():
    user32=ctypes.WinDLL('user32',use_last_error=True)
    user32.OpenInputDesktop.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    user32.OpenInputDesktop.restype=wintypes.HANDLE
    user32.GetUserObjectInformationW.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    user32.CloseDesktop.argtypes=[wintypes.HANDLE]
    handle=user32.OpenInputDesktop(0,False,1)
    if not handle:
        return {'input_desktop_accessible':False,'locked_or_unavailable':True,'error':ctypes.get_last_error()}
    try:
        name=ctypes.create_unicode_buffer(256)
        needed=wintypes.DWORD()
        ok=user32.GetUserObjectInformationW(handle,2,name,ctypes.sizeof(name),ctypes.byref(needed))
        return {'input_desktop_accessible':True,'input_desktop':name.value if ok else None,'locked_or_unavailable':name.value.casefold()!='default' if ok else True}
    finally:
        user32.CloseDesktop(handle)

def capture_native(w, target):
    """Read only capture of the application's own HWND, no desktop input."""
    user32=ctypes.windll.user32
    gdi32=ctypes.windll.gdi32
    for fn, args, result in [
        (user32.GetWindowDC,[wintypes.HWND],wintypes.HDC),
        (user32.ReleaseDC,[wintypes.HWND,wintypes.HDC],ctypes.c_int),
        (gdi32.CreateCompatibleDC,[wintypes.HDC],wintypes.HDC),
        (gdi32.CreateCompatibleBitmap,[wintypes.HDC,ctypes.c_int,ctypes.c_int],wintypes.HBITMAP),
        (gdi32.SelectObject,[wintypes.HDC,wintypes.HANDLE],wintypes.HANDLE),
        (user32.PrintWindow,[wintypes.HWND,wintypes.HDC,wintypes.UINT],wintypes.BOOL),
        (gdi32.DeleteObject,[wintypes.HANDLE],wintypes.BOOL),
        (gdi32.DeleteDC,[wintypes.HDC],wintypes.BOOL),
    ]:
        fn.argtypes=args
        fn.restype=result
    class Header(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),('planes',wintypes.WORD),('bit_count',wintypes.WORD),('compression',wintypes.DWORD),('image_size',wintypes.DWORD),('xpels',wintypes.LONG),('ypels',wintypes.LONG),('colors_used',wintypes.DWORD),('colors_important',wintypes.DWORD)]
    gdi32.GetDIBits.argtypes=[wintypes.HDC,wintypes.HBITMAP,wintypes.UINT,wintypes.UINT,ctypes.c_void_p,ctypes.POINTER(Header),wintypes.UINT]
    gdi32.GetDIBits.restype=ctypes.c_int
    r=w.BoundingRectangle
    width,height=r.width(),r.height()
    hwnd=w.NativeWindowHandle
    dc=user32.GetWindowDC(hwnd)
    compatible=gdi32.CreateCompatibleDC(dc)
    bitmap=gdi32.CreateCompatibleBitmap(dc,width,height)
    previous=gdi32.SelectObject(compatible,bitmap)
    try:
        ok=user32.PrintWindow(hwnd,compatible,2)
        header=Header(ctypes.sizeof(Header),width,-height,1,32,0,width*height*4,0,0,0,0)
        pixels=ctypes.create_string_buffer(width*height*4)
        gdi32.SelectObject(compatible,previous)
        rows=gdi32.GetDIBits(compatible,bitmap,0,height,pixels,ctypes.byref(header),0)
        if ok and rows:
            Image.frombytes('RGB',(width,height),pixels.raw,'raw','BGRX').save(target)
            return True
        return False
    finally:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(compatible)
        user32.ReleaseDC(hwnd,dc)

def windows():
    found = []
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user32=ctypes.WinDLL('user32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handles=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    callback=callback_type(lambda hwnd,param:(handles.append(hwnd) or True))
    user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user32.EnumWindows(callback,0)
    for hwnd in handles:
        try:
            if not user32.IsWindowVisible(hwnd):
                continue
            pid=wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            handle=kernel.OpenProcess(0x1000,False,pid.value)
            if handle:
                try:
                    buffer=ctypes.create_unicode_buffer(1024)
                    length=wintypes.DWORD(1024)
                    if kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length)) and buffer.value.casefold().startswith(r'd:\jianyingpro'.casefold()):
                        found.append(auto.ControlFromHandle(hwnd))
                finally:
                    kernel.CloseHandle(handle)
        except Exception:
            pass
    return found

def tree(w, depth=0):
    if depth > 8:
        return []
    entries = []
    try:
        r = w.BoundingRectangle
        entries.append({'depth':depth, 'name':w.Name, 'type':w.ControlTypeName, 'class':w.ClassName, 'id':w.AutomationId, 'rectangle':[r.left,r.top,r.right,r.bottom]})
        for c in w.GetChildren():
            entries.extend(tree(c,depth+1))
    except Exception:
        pass
    return entries

def find_class(cls):
    def search(w,depth=0):
        if w.ClassName==cls:
            return w
        if depth<5:
            for c in w.GetChildren():
                found=search(c,depth+1)
                if found:
                    return found
        return None
    for root in windows():
        found=search(root)
        if found:
            return found
    raise RuntimeError(f'Target JianYing window not found: {cls}')

def snapshot(label='launch', capture=False, native=False):
    results = []
    try:
        targets=[find_class(sys.argv[sys.argv.index('--window-class')+1])] if '--window-class' in sys.argv else windows()
    except RuntimeError:
        targets=windows()
    for i,w in enumerate(targets):
        if w.BoundingRectangle.width() < 100:
            continue
        r = w.BoundingRectangle
        data = tree(w)
        name = f'jianying_{label}_{i}'
        (REVIEW / (name+'.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        if capture:
            ImageGrab.grab(bbox=(r.left,r.top,r.right,r.bottom)).save(REVIEW / (name+'.png'))
        if native:
            capture=capture_native(w,REVIEW / (name+'.png'))
        results.append({'title':w.Name,'pid':w.ProcessId,'tree':len(data),'screenshot':str(REVIEW / (name+'.png')) if capture else None})
    print(json.dumps(results,ensure_ascii=False))

if __name__ == '__main__':
    print(json.dumps(input_desktop_state(),ensure_ascii=False))
    if '--restore' in sys.argv:
        if input_desktop_state()['locked_or_unavailable']:
            raise RuntimeError('Desktop locked: no app input sent')
        target=next(w for w in windows() if w.Name=='剪映专业版')
        ctypes.windll.user32.ShowWindow(target.NativeWindowHandle,9)
        ctypes.windll.user32.SetForegroundWindow(target.NativeWindowHandle)
        time.sleep(1)
    if '--dialog-path' in sys.argv:
        if input_desktop_state()['locked_or_unavailable']:
            raise RuntimeError('Desktop locked: no app input sent')
        value=sys.argv[sys.argv.index('--dialog-path')+1]
        if not Path(value).resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Dialog path must stay inside project')
        dialog=find_class('#32770')
        edit=dialog.EditControl(searchDepth=3,AutomationId='1152')
        edit.GetValuePattern().SetValue(value)
        button=dialog.ButtonControl(searchDepth=3,AutomationId='1')
        button.GetInvokePattern().Invoke()
        time.sleep(2)
    if '--click' in sys.argv:
        if input_desktop_state()['locked_or_unavailable']:
            raise RuntimeError('Desktop locked: no app input sent')
        idx=sys.argv.index('--click')
        x,y=map(int,sys.argv[idx+1:idx+3])
        cls=sys.argv[sys.argv.index('--window-class')+1] if '--window-class' in sys.argv else None
        target=find_class(cls) if cls else next(w for w in windows() if w.Name=='剪映专业版')
        packed=(y<<16)|(x&0xffff)
        ctypes.windll.user32.PostMessageW(target.NativeWindowHandle,0x0200,0,packed)
        ctypes.windll.user32.PostMessageW(target.NativeWindowHandle,0x0201,1,packed)
        ctypes.windll.user32.PostMessageW(target.NativeWindowHandle,0x0202,0,packed)
        time.sleep(2)
    if '--launch' in sys.argv:
        # Visible launch is specifically requested for interactive verification.
        p=subprocess.Popen([str(EXE)],cwd=str(EXE.parent))
        (REVIEW/'jianying_started_pid.txt').write_text(str(p.pid),encoding='utf-8')
        time.sleep(8)
    snapshot(sys.argv[-1] if len(sys.argv)>1 and not sys.argv[-1].startswith('--') else 'launch', capture='--capture' in sys.argv, native='--native-capture' in sys.argv)
