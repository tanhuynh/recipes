import cv2,numpy as np,sys
from skimage.color import rgb2lab
def lab(p):
    im=cv2.imread(p,cv2.IMREAD_UNCHANGED)[...,:3][...,::-1]/65535.; return im, rgb2lab(im)
for p in sys.argv[1:]:
    im,l=lab(p); L,A,B=l[...,0],l[...,1],l[...,2]; C=np.hypot(A,B)
    print('==',p.split('/')[-1])
    for name,(x0,y0,x1,y1) in {'left white caps':(150,170,720,420),'center white tower':(1080,90,1290,260),'white dune BR':(1200,900,1700,1150)}.items():
        s=np.s_[y0:y1,x0:x1]; m=(L[s]>70)
        print(f'  {name:20s} L {np.median(L[s][m]):.1f} a* {np.median(A[s][m]):+.1f} b* {np.median(B[s][m]):+.1f}')
    t=np.s_[0:500,800:1450]; g=(L[t]<45)&(C[t]>5)&(np.abs(A[t])<15)
    tA,tB=np.median(A[t][g&(A[t]<0)]),np.median(B[t][g&(A[t]<0)]); print(f'  trees a* {tA:.1f} b* {tB:.1f} hue {np.degrees(np.arctan2(tB,tA)):.0f}')
    r=(C>20)&(L>40)&(L<75); print(f'  red rock a* {np.median(A[r]):.1f} b* {np.median(B[r]):.1f} hue {np.degrees(np.arctan2(np.median(B[r]),np.median(A[r]))):.0f}  C {np.median(C[r]):.1f}')
    print('  L p1/p50/p99.9', np.percentile(L,[1,50,99.9]).round(1))
    cv2.imwrite(p.split('/')[-1].replace('16.png','8.png'),(im[...,::-1]*255).astype(np.uint8))
