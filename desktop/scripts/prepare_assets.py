"""Copy project CAD assets; generate a simple app mark and Windows icon."""
from pathlib import Path
import shutil
import gzip
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
(root/'public').mkdir(exist_ok=True)
(root/'build').mkdir(exist_ok=True)
if not (root/'public/engine.glb').exists():
    compressed = root.parent/'public-demo/public/engine.glb.gz'
    if compressed.exists():
        with gzip.open(compressed, 'rb') as source, (root/'public/engine.glb').open('xb') as target:
            shutil.copyfileobj(source, target)
    else:
        shutil.copy2(root.parent/'output/ae300_r4/AE300_R4_Animated.glb', root/'public/engine.glb')
if not (root/'public/engine-preview.png').exists():
    shutil.copy2(root.parent/'output/ae300_r4/04_integration.png', root/'public/engine-preview.png')
image=Image.new('RGBA',(256,256),(0,0,0,0))
d=ImageDraw.Draw(image)
d.rounded_rectangle((5,5,251,251),radius=55,fill='#112634',outline='#3b857d',width=5)
d.polygon([(57,195),(113,54),(150,54),(208,195),(167,195),(131,96),(97,195)],fill='#4dd9c3')
d.polygon([(103,147),(164,147),(174,173),(93,173)],fill='#4dd9c3')
d.ellipse((199,18,241,60),fill='#89f1d6',outline='#112634',width=7)
image.save(root/'public/app-icon.png')
image.save(root/'build/icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('CAD assets and app icon prepared')
