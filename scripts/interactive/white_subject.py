"""Deterministic complete-subject extraction, only for genuinely white backdrops."""
import numpy as np
from PIL import Image, ImageFilter


def grow(region, allowed):
    for _ in range(sum(allowed.shape)):
        expanded=region.copy()
        expanded[1:]|=region[:-1];expanded[:-1]|=region[1:]
        expanded[:,1:]|=region[:,:-1];expanded[:,:-1]|=region[:,1:]
        expanded&=allowed
        if np.array_equal(region,expanded):break
        region=expanded
    return region


def extract_white_subject(image, seed):
    height,width=image.shape[:2]
    border=np.concatenate((image[:3].reshape(-1,3),image[-3:].reshape(-1,3),
        image[:,:3].reshape(-1,3),image[:,-3:].reshape(-1,3)))
    background=np.median(border,axis=0)
    if float(background.min())<235 or float((np.min(border,axis=1)>230).mean())<.8:return None
    scale=min(1,512/max(width,height));size=(max(1,round(width*scale)),max(1,round(height*scale)))
    small=np.asarray(Image.fromarray(image).resize(size,Image.Resampling.LANCZOS))
    candidate=(np.max(np.abs(small.astype(float)-background),axis=2)>24)
    # Close tiny gaps in an outline; retain the original pixels in the delivered cutout.
    candidate=np.asarray(Image.fromarray(candidate.astype(np.uint8)*255).filter(
        ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)))>127
    h,w=candidate.shape;sx=min(w-1,max(0,round(seed['x']*(w-1))));sy=min(h-1,max(0,round(seed['y']*(h-1))))
    ys,xs=np.where(candidate)
    if not len(xs):return None
    nearest=np.argmin((xs-sx)**2+(ys-sy)**2)
    if (xs[nearest]-sx)**2+(ys[nearest]-sy)**2>(.12*max(w,h))**2:return None
    connected=np.zeros_like(candidate);connected[ys[nearest],xs[nearest]]=True
    connected=grow(connected,candidate)
    empty=~connected;exterior=np.zeros_like(empty)
    exterior[0]=empty[0];exterior[-1]=empty[-1];exterior[:,0]=empty[:,0];exterior[:,-1]=empty[:,-1]
    filled=~grow(exterior,empty)
    if not .02<float(filled.mean())<.85:return None
    alpha=Image.fromarray(filled.astype(np.uint8)*255).resize((width,height),Image.Resampling.LANCZOS)
    alpha=alpha.filter(ImageFilter.GaussianBlur(.55));mask=np.asarray(alpha)>10
    ys,xs=np.where(mask);pad=4
    left=max(0,int(xs.min())-pad);right=min(width,int(xs.max())+pad+1)
    top=max(0,int(ys.min())-pad);bottom=min(height,int(ys.max())+pad+1)
    rgba=np.dstack((image,np.asarray(alpha))).astype(np.uint8)[top:bottom,left:right]
    surface=image.copy();surface[mask]=background.astype(np.uint8)
    return {'surface':surface,'image':Image.fromarray(rgba),'mask':mask,
        'info':{'bbox_norm':[left/width,top/height,(right-left)/width,(bottom-top)/height],
            'size':[right-left,bottom-top],'alpha_coverage':float((rgba[:,:,3]>128).mean()),
            'method':'white-background-connected-subject','completeSubject':True}}
