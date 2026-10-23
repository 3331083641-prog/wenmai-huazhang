from pathlib import Path
import sys, json, shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import qrcode
from qrcode.image.svg import SvgPathImage
from PIL import Image,ImageDraw,ImageFont
import cv2
import numpy as np

URL='https://github.com/3331083641-prog/wenmai-huazhang'
OUT=ROOT/'outputs/qr'
OUT.mkdir(parents=True,exist_ok=True)
qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=24,border=6)
qr.add_data(URL);qr.make(fit=True)
pure=qr.make_image(fill_color='#164e56',back_color='white').convert('RGB')
pure.save(OUT/'纹脉华章_仓库二维码_纯码.png')
qr.make_image(image_factory=SvgPathImage).save(OUT/'纹脉华章_仓库二维码_纯码.svg')
font_path='C:/Windows/Fonts/msyh.ttc'
def font(size):return ImageFont.truetype(font_path,size)
im=Image.new('RGB',(3000,3400),'white');d=ImageDraw.Draw(im)
teal='#164e56';red='#a92c22';gold='#c29850'
d.rounded_rectangle((65,65,2935,3335),radius=55,outline=gold,width=5)
d.rounded_rectangle((1245,167,1755,179),radius=6,fill=gold)
def centered(text,y,size,color):
    f=font(size);w=d.textbbox((0,0),text,font=f)[2];d.text(((3000-w)/2,y),text,font=f,fill=color)
centered('纹脉华章',235,168,teal)
centered('传统文化视觉智能创作与文创应用平台',465,67,teal)
centered('开源项目 · MIT LICENSE',637,58,red)
scaled=pure.resize((2100,2100),Image.Resampling.NEAREST)
im.paste(scaled,(450,810))
centered('扫描获取源码、运行说明与演示材料',2900,67,teal)
centered('github.com/3331083641-prog/wenmai-huazhang',3080,53,'#626a69')
im.save(OUT/'纹脉华章_开源项目二维码.png',dpi=(300,300))
im.save(OUT/'纹脉华章_开源项目二维码.jpg',quality=96,subsampling=0,dpi=(300,300))
im.save(OUT/'纹脉华章_开源项目二维码.pdf',resolution=300)
svg_pure=(OUT/'纹脉华章_仓库二维码_纯码.svg').read_text(encoding='utf-8')
svg_start=svg_pure[svg_pure.index('<svg'):]
# Preserve actual QR geometry as vectors; external ornament never touches the quiet zone.
import re
view=re.search(r'viewBox="([^"]+)"',svg_start).group(1)
inner=svg_start[svg_start.index('>')+1:svg_start.rindex('</svg>')].replace('#000000',teal)
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="3400" viewBox="0 0 3000 3400"><rect width="3000" height="3400" fill="white"/><rect x="65" y="65" width="2870" height="3270" rx="55" fill="none" stroke="{gold}" stroke-width="5"/><rect x="1245" y="167" width="510" height="12" rx="6" fill="{gold}"/><g font-family="Microsoft YaHei,Noto Sans CJK SC,sans-serif" text-anchor="middle"><text x="1500" y="420" font-size="168" fill="{teal}">纹脉华章</text><text x="1500" y="550" font-size="67" fill="{teal}">传统文化视觉智能创作与文创应用平台</text><text x="1500" y="710" font-size="58" fill="{red}">开源项目 · MIT LICENSE</text><text x="1500" y="2990" font-size="67" fill="{teal}">扫描获取源码、运行说明与演示材料</text><text x="1500" y="3150" font-size="53" fill="#626a69">github.com/3331083641-prog/wenmai-huazhang</text></g><svg x="450" y="810" width="2100" height="2100" viewBox="{view}">{inner}</svg></svg>'''
(OUT/'纹脉华章_开源项目二维码.svg').write_text(svg,encoding='utf-8')
decoder=cv2.QRCodeDetector()
checks={}
for name in ['纹脉华章_仓库二维码_纯码.png','纹脉华章_开源项目二维码.png']:
    b=cv2.imdecode(np.fromfile(str(OUT/name),dtype=np.uint8),cv2.IMREAD_COLOR)
    decoded=''
    for width in [900,1200,1600]:
        img=cv2.resize(b,(width,round(b.shape[0]*width/b.shape[1])),interpolation=cv2.INTER_AREA)
        decoded=decoder.detectAndDecode(img)[0]
        if decoded==URL:break
    if decoded!=URL:raise RuntimeError('QR decoding failed: '+name)
    checks[name]='decoded exact repository URL'
(OUT/'二维码核验.json').write_text(json.dumps({'target':URL,'generator':'https://github.com/lincolnloop/python-qrcode','license':'BSD','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'docs/images').mkdir(parents=True,exist_ok=True)
shutil.copy2(OUT/'纹脉华章_开源项目二维码.png',ROOT/'docs/images/project_qr.png')
print(json.dumps(checks,ensure_ascii=False))
