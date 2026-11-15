import sys, numpy as np
from PIL import Image
from m import load, R
a, b = sys.argv[1], sys.argv[2]
La, Ca, Da = load(a); Lb, Cb, Db = load(b)
rock = Ca > 12
print('region          dL(med)  rockDet a->b   (%)   rockC a->b   fogL a->b')
for k, (x0, y0, x1, y1) in R.items():
    s = np.s_[y0:y1, x0:x1]; m = rock[s]; f = Ca[s] < 8
    da, db = (Da[s][m].std(), Db[s][m].std()) if m.any() else (np.nan, np.nan)
    print(f'{k:14s} {np.median(Lb[s]-La[s]):+6.2f}   {da:5.2f}->{db:5.2f} ({(db/da-1)*100:+4.0f}%)  '
          f'{np.median(Ca[s][m]) if m.any() else np.nan:5.1f}->{np.median(Cb[s][m]) if m.any() else np.nan:5.1f}  '
          f'{np.median(La[s][f]) if f.any() else np.nan:5.1f}->{np.median(Lb[s][f]) if f.any() else np.nan:5.1f}')
d = np.clip(np.abs(Lb - La) * 15, 0, 255).astype(np.uint8)
Image.fromarray(d).save(sys.argv[3])
print('fog px |dL|>1 in x>900:', (np.abs(Lb-La)[:, 900:][(Ca < 8)[:, 900:]] > 1).mean().round(3))
