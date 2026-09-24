"""Produce the preview animation, dimension reference sheet and portable package."""
import json,math,zipfile,html
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from kinematics import v,a,R,L,cylinder_state
from paths import HERE, OUT
frames=[]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for index,f in enumerate(sorted((OUT/'motion_frames').glob('*.png'))):
    im=Image.open(f).convert('RGB');draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,1000,57),fill=(10,17,24))
    draw.text((20,10),'AE300 R4  |  Analytic mechanism reconstruction',font=font,fill=(225,236,242))
    draw.text((20,34),f'Crank angle {index*12:03d} deg   |   Slow-motion cycle   |   92 mm stroke / 1.69 ratio',font=font,fill=(120,199,211))
    frames.append(im.quantize(colors=96))
if frames:frames[0].save(OUT/'AE300_R4_motion.gif',save_all=True,append_images=frames[1:],duration=110,loop=0,optimize=False)

# A vector dimension reference for the genuinely controlled interfaces. Schematic
# projections are deliberately distinguished from the approximate outer casting.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1050" viewBox="0 0 1400 1050">',
     '<rect width="1400" height="1050" fill="#f6f8fa"/>',
     '<style>text{font-family:Arial,sans-serif;fill:#182b3a}.small{font-size:16px}.label{font-size:19px}.heading{font-size:23px;font-weight:bold}.line{stroke:#244756;stroke-width:2;fill:none}.dim{stroke:#328493;stroke-width:1.3;fill:none}.datum{stroke:#9aaeba;stroke-width:1;stroke-dasharray:6 5;fill:none}</style>',
     '<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6 Z" fill="#328493"/></marker></defs>']
def text(x,y,s,cls='small'):svg.append(f'<text x="{x}" y="{y}" class="{cls}">{html.escape(s)}</text>')
def line(x1,y1,x2,y2,cls='line'):svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="{cls}"/>')
def circle(x,y,r,cls='line'):svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" class="{cls}"/>')
def dim(x1,y1,x2,y2,s):
    svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="dim" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
    text((x1+x2)/2-20,(y1+y2)/2-9,s)

text(45,55,'AE300 / E4 — R4 CONTROLLED DIMENSION REFERENCE','heading')
text(45,85,'Millimetres | Schematic projections | Source dimensions only; outer contours and internal detail reconstructed')
line(40,107,1360,107)
text(50,150,'CYLINDER BANK / TOP PROJECTION','heading')
for i in range(4):
    x=128+i*135;circle(x,276,62.25);line(x,197,x,355,'datum');line(x-70,276,x+70,276,'datum');text(x-10,285,str(i+1),'label')
    if i<3:dim(x,184,x+135,184,'90')
dim(65.75,380,190.25,380,'83 bore')
text(55,417,'Four bores at 90 pitch. Source: MM01-9 (PDF31).')
text(55,444,'Displacement from bore/stroke: 1991.104 cm3; OEM nominal 1991 cm3.')

text(770,150,'PROPELLER FLANGE / FRONT','heading')
cx=1010;cy=285;scale=1.8
circle(cx,cy,127/2*scale);circle(cx,cy,101.6/2*scale,'datum')
circle(cx,cy,27*scale,'datum')
for i in range(6):
    t=i*math.tau/6;circle(cx+50.8*scale*math.cos(t),cy+50.8*scale*math.sin(t),6.375*scale)
line(cx-135,cy,cx+135,cy,'datum');line(cx,cy-135,cx,cy+135,'datum')
text(1180,230,'OD 127');text(1180,262,'PCD 101.6');text(1180,294,'6 x dia12.75')
text(780,420,'Source: IM Fig15.2, PDF134. Other flange dimensions assumed.')
text(780,446,'Centre bore shown dashed: reconstructed, not dimensioned here.')
line(40,479,1360,479)
text(50,520,'MOUNT DATUM COORDINATES','heading')
text(50,547,'Origin: propeller flange centre; +X aft, +Z up; Y per IM Table6.1.')
text(70,585,'Position');text(325,585,'X');text(440,585,'Y');text(555,585,'Z')
for i,(name,p) in enumerate(zip(['Front left','Front right','Rear left','Rear right'],v('mounts'))):
    yy=625+i*36;text(70,yy,name,'label')
    for xx,value in zip([325,440,555],p):text(xx,yy,str(value),'label')
text(55,797,'Rear-left Z is -298 mm, verified directly against the drawing.')
text(55,824,'Pad/hole/support shapes remain reconstruction concepts.')

text(770,520,'MECHANISM / VOLUME CONTROL','heading')
text(785,565,'Bore: 83 mm     Stroke: 92 mm     Crank radius: 46 mm','label')
text(785,602,'Compression ratio: 17.5 : 1','label')
text(785,639,'Reduction: 1.69 : 1     Firing: 1 - 3 - 4 - 2','label')
text(785,676,'Rod length: 147 mm [ASSUMED]','label')
text(785,713,'Bank inclination: 40 deg [ASSUMED]','label')
text(785,750,'Gear teeth: 100 / 50 / 169 [ASSUMED]','label')
text(785,797,'Actual assembly extents: see validation.json.')
text(785,824,'Source envelope: L738 x W855 x H574; not achieved contour fidelity.')
line(40,865,1360,865)
text(50,903,'RELEASE: DIGITAL TWIN RECONSTRUCTION — NOT AN OEM MANUFACTURING DRAWING','heading')
text(50,936,'Geometry, sensor placement and motion assumptions: DESIGN_NOTES.md / parameters.json / sensor_map.json')
text(50,964,'Build-time solid checks and analytic motion; STEP geometric reimport blocked. See release validation status.')
text(50,997,'References: E4.08.04 maintenance package and E4.02.01 installation Rev22; original manuals remain primary.')
svg.append('</svg>');(OUT/'AE300_R4_Dimension_Reference.svg').write_text('\n'.join(svg),encoding='utf-8')

package=OUT/'AE300_R4_CAD_Package.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in OUT.rglob('*'):
        if not f.is_file() or f==package or 'motion_frames' in f.parts or f.name in ['render_meshes.json'] or f.suffix=='.blend1':continue
        z.write(f,'AE300_R4/'+str(f.relative_to(OUT)))
    for f in HERE.glob('*'):
        if f.is_file():z.write(f,'AE300_R4/source/'+f.name)
print('Package',package,'bytes',package.stat().st_size)
