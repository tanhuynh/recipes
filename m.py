import sys, numpy as np
from PIL import Image
from skimage.color import rgb2lab
from scipy.ndimage import gaussian_filter
def load(p):
    a=np.asarray(Image.open(p).convert('RGB'))/255.0
    lab=rgb2lab(a); L=lab[...,0]; C=np.hypot(lab[...,1],lab[...,2])
    det=np.abs(L-gaussian_filter(L,2))
    return L,C,det
# regions in preview px (x0,y0,x1,y1)
R={'hub(ctrl)':(450,380,950,620),'mid-center':(900,250,1250,560),'right-mid':(1250,250,1700,560),
   'bottom-right':(1150,600,2000,833),'far-top':(650,100,1250,230),'fog-right':(1500,80,1950,400)}
def stats(L,C,det,rock):
    out={}
    for k,(x0,y0,x1,y1) in R.items():
        s=np.s_[y0:y1,x0:x1]; m=rock[s]
        out[k]=(np.median(L[s]), m.mean(), np.median(L[s][m]) if m.any() else np.nan,
                det[s][m].std() if m.any() else np.nan, np.median(C[s][m]) if m.any() else np.nan)
    return out
if __name__=='__main__':
    L,C,det=load(sys.argv[1])
    rock=(C>12)  # chroma separates red rock from grey fog
    print('region          medL  rock%  rockL  rockDet  rockC')
    for k,v in stats(L,C,det,rock).items(): print(f'{k:14s} {v[0]:5.1f} {v[1]*100:5.0f} {v[2]:6.1f} {v[3]:7.2f} {v[4]:6.1f}')
    # L histogram of rock vs fog inside fog-affected zone (x>900)
    z=np.s_[:,900:]
    for name,m in (('rock',rock[z]),('fog',(C<8)[z])):
        print(name,'L pct 5/25/50/75/95:',np.percentile(L[z][m],[5,25,50,75,95]).round(1))
