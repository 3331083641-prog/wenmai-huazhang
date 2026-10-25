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


def extract_white_subject(image, seed, preserve_holes=False):
    """Extract a complete subject with observed-colour alpha and white defringing.

    Coarse connectivity selects the subject, while native-resolution colour
    coverage refines its contour. White interiors remain opaque by default;
    preserve_holes explicitly treats white negative space as transparent paper
    cutouts. RGB is unmatted algebraically, never generated or repainted.
    """
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
    coarse=Image.fromarray(filled.astype(np.uint8)*255)
    # Restrict native-resolution evidence to the selected silhouette and a tiny
    # surrounding band, retaining thin contours without acquiring other motifs.
    nearby=np.asarray(coarse.filter(ImageFilter.MaxFilter(7)).resize(
        (width,height),Image.Resampling.NEAREST))>0
    pixels=image.astype(np.float32)
    bg=background.astype(np.float32)
    coverage=np.max(np.maximum(0,1-pixels/np.maximum(bg,1)),axis=2)
    # Also bound alpha for channels lighter than a slightly off-white paper.
    highlight=np.divide(np.maximum(0,pixels-bg),255-bg,
        out=np.zeros_like(pixels),where=(255-bg)>0)
    coverage=np.maximum(coverage,np.max(highlight,axis=2))
    coverage=np.where(nearby,coverage,0).astype(np.float32)
    # Local strongest colour provides an observed opaque-colour reference.
    # Unlike blurring RGB, this cannot carry white paper into the foreground.
    # Pillow rank filters require byte images; rounding upward keeps the
    # minimum-opacity constraint conservative after byte quantisation.
    local=np.asarray(Image.fromarray(np.ceil(coverage*255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(9))).astype(np.float32)/255
    opacity=np.divide(coverage,local,out=np.zeros_like(coverage),where=local>0)
    opacity=np.maximum(opacity,coverage)
    if not preserve_holes:
        interior=np.asarray(coarse.filter(ImageFilter.MinFilter(5)).resize(
            (width,height),Image.Resampling.NEAREST))>0
        opacity[interior]=1
    alpha_bytes=np.ceil(np.clip(opacity,0,1)*255).astype(np.uint8)
    mask=alpha_bytes>0
    if not mask.any():return None
    ys,xs=np.where(mask);pad=4
    left=max(0,int(xs.min())-pad);right=min(width,int(xs.max())+pad+1)
    top=max(0,int(ys.min())-pad);bottom=min(height,int(ys.max())+pad+1)
    # Invert the original paper composite using the delivered, quantised alpha.
    # Compositing these RGB values back over measured paper reproduces the source.
    a=alpha_bytes.astype(np.float32)[:,:,None]/255
    foreground=np.divide(pixels-bg*(1-a),a,out=pixels.copy(),where=a>0)
    foreground=np.clip(np.rint(foreground),0,255).astype(np.uint8)
    rgba=np.dstack((foreground,alpha_bytes))[top:bottom,left:right]
    surface=image.copy();surface[mask]=background.astype(np.uint8)
    return {'surface':surface,'image':Image.fromarray(rgba),'mask':mask,
        'info':{'bbox_norm':[left/width,top/height,(right-left)/width,(bottom-top)/height],
            'size':[right-left,bottom-top],'alpha_coverage':float((rgba[:,:,3]>128).mean()),
            'method':'white-background-connected-native-coverage-defringe',
            'completeSubject':True,'negativeSpacePreserved':bool(preserve_holes)}}
