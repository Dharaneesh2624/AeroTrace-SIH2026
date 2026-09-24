"""Small native OpenCascade modelling/export layer; no VTK dependency."""
import math
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Ax1, gp_Vec, gp_Trsf
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeSphere, BRepPrimAPI_MakeTorus, BRepPrimAPI_MakePrism
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_REVERSED
from OCP.TopLoc import TopLoc_Location
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.STEPControl import STEPControl_Writer, STEPControl_Reader, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorGen
from OCP.TDataStd import TDataStd_Name
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB

def box(dx,dy,dz,p=(0,0,0)):
    return BRepPrimAPI_MakeBox(gp_Pnt(p[0]-dx/2,p[1]-dy/2,p[2]-dz/2),dx,dy,dz).Shape()

def cyl(r,h,p=(0,0,0),axis=(0,0,1)):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*p),gp_Dir(*axis)),r,h).Shape()

def sphere(r,p=(0,0,0)):
    return BRepPrimAPI_MakeSphere(gp_Pnt(*p),r).Shape()

def torus(r,t,p=(0,0,0),axis=(0,0,1)):
    return BRepPrimAPI_MakeTorus(gp_Ax2(gp_Pnt(*p),gp_Dir(*axis)),r,t).Shape()

def boolean(kind,base,tool):
    op=kind(base,tool); op.Build()
    if not op.IsDone(): raise RuntimeError('OpenCascade boolean failed')
    return op.Shape()
def cut(s,*tools):
    for t in tools: s=boolean(BRepAlgoAPI_Cut,s,t)
    return s
def fuse(*shapes):
    s=shapes[0]
    for t in shapes[1:]: s=boolean(BRepAlgoAPI_Fuse,s,t)
    return s
def common(s,t): return boolean(BRepAlgoAPI_Common,s,t)

def move(s,p=(0,0,0),rx=0):
    if rx:
        tr=gp_Trsf(); tr.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),math.radians(rx))
        s=BRepBuilderAPI_Transform(s,tr,True).Shape()
    if any(p):
        tr=gp_Trsf(); tr.SetTranslation(gp_Vec(*p)); s=BRepBuilderAPI_Transform(s,tr,True).Shape()
    return s

def orient(s,axis,p=(0,0,0)):
    # Rotate a Z-axis primitive onto the required direction.
    dx,dy,dz=axis; n=math.sqrt(dx*dx+dy*dy+dz*dz); dx/=n;dy/=n;dz/=n
    angle=math.acos(max(-1,min(1,dz)))
    if angle>1e-9:
        ax=(-dy,dx,0) if abs(dz)<0.999999 else (1,0,0)
        tr=gp_Trsf();tr.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(*ax)),angle)
        s=BRepBuilderAPI_Transform(s,tr,True).Shape()
    return move(s,p)

def extrude(points,vec):
    poly=BRepBuilderAPI_MakePolygon()
    for p in points: poly.Add(gp_Pnt(*p))
    poly.Close(); face=BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face,gp_Vec(*vec)).Shape()

def rounded_xy(dx,dy,h,r,p=(0,0,0)):
    # True rounded plan with cylinders; planar top and bottom.
    shapes=[box(dx-2*r,dy,h,p),box(dx,dy-2*r,h,p)]
    for x in [-1,1]:
        for y in [-1,1]: shapes.append(cyl(r,h,(p[0]+x*(dx/2-r),p[1]+y*(dy/2-r),p[2]-h/2)))
    return fuse(*shapes)

def pipe(points,ro,ri=0):
    # Swept straight segments with spherical elbows; a connected, hollow solid.
    def solid(r):
        pieces=[]
        for a,b in zip(points,points[1:]):
            vec=[b[i]-a[i] for i in range(3)]; length=math.sqrt(sum(x*x for x in vec))
            pieces.append(cyl(r,length,a,vec))
        for p in points[1:-1]: pieces.append(sphere(r,p))
        return fuse(*pieces)
    out=solid(ro)
    return cut(out,solid(ri)) if ri else out

def coil(radius,wire_radius,height,turns):
    from OCP.TColgp import TColgp_HArray1OfPnt
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.Geom import Geom_Circle
    pts=TColgp_HArray1OfPnt(1,turns*24+1)
    for i in range(turns*24+1):
        t=i/(turns*24);pts.SetValue(i+1,gp_Pnt(radius*math.cos(t*turns*math.tau),radius*math.sin(t*turns*math.tau),t*height))
    interp=GeomAPI_Interpolate(pts,False,1e-6);interp.Perform()
    path=BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(interp.Curve()).Edge()).Wire()
    circle=Geom_Circle(gp_Ax2(gp_Pnt(radius,0,0),gp_Dir(0,radius*turns*math.tau,height)),wire_radius)
    profile=BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circle).Edge()).Wire()
    return BRepOffsetAPI_MakePipe(path,BRepBuilderAPI_MakeFace(profile).Face()).Shape()

def compound(shapes):
    s=TopoDS_Compound(); builder=BRep_Builder();builder.MakeCompound(s)
    for p in shapes: builder.Add(s,p)
    return s

def volume(s):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(s,g);return g.Mass()
def bounds(s):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(s,b,False,False);return list(b.Get())
def valid(s):return BRepCheck_Analyzer(s).IsValid()
def solid_count(s):
    ex=TopExp_Explorer(s,TopAbs_SOLID);n=0
    while ex.More():n+=1;ex.Next()
    return n

def mesh(s,tol=0.6):
    BRepMesh_IncrementalMesh(s,tol,False,0.22,True).Perform()
    vs=[];ts=[];ex=TopExp_Explorer(s,TopAbs_FACE)
    while ex.More():
        f=TopoDS.Face_s(ex.Current());loc=TopLoc_Location();tri=BRep_Tool.Triangulation_s(f,loc)
        if tri:
            offset=len(vs);tr=loc.Transformation()
            for i in range(1,tri.NbNodes()+1):
                p=tri.Node(i).Transformed(tr);vs.append([p.X(),p.Y(),p.Z()])
            for i in range(1,tri.NbTriangles()+1):
                t=list(tri.Triangle(i).Get())
                if f.Orientation()==TopAbs_REVERSED:t.reverse()
                ts.append([x-1+offset for x in t])
        ex.Next()
    return vs,ts

def step(s,path):
    writer=STEPControl_Writer();writer.Transfer(s,STEPControl_AsIs)
    if writer.Write(str(path)) != IFSelect_RetDone:raise RuntimeError('STEP write failed')

def assembly_step(parts,path):
    doc=TDocStd_Document(TCollection_ExtendedString('AE300'))
    shapes=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()); colors=XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    root=shapes.AddShape(compound([]),True);TDataStd_Name.Set_s(root,TCollection_ExtendedString('AE300_R4'))
    groups={}
    for p in parts:
        if p['group'] not in groups:
            label=shapes.AddShape(compound([]),True);TDataStd_Name.Set_s(label,TCollection_ExtendedString(p['group']))
            shapes.AddComponent(root,label,TopLoc_Location());groups[p['group']]=label
        label=shapes.AddShape(p['world'],False)
        TDataStd_Name.Set_s(label,TCollection_ExtendedString(p['name']))
        colors.SetColor(label,Quantity_Color(*p['color'],Quantity_TOC_RGB),XCAFDoc_ColorGen)
        instance=shapes.AddComponent(groups[p['group']],label,TopLoc_Location())
        TDataStd_Name.Set_s(instance,TCollection_ExtendedString(p['name']))
    shapes.UpdateAssemblies()
    writer=STEPCAFControl_Writer();writer.SetColorMode(True);writer.SetNameMode(True)
    if not writer.Transfer(doc,STEPControl_AsIs): raise RuntimeError('Assembly transfer failed')
    if writer.Write(str(path))!=IFSelect_RetDone:raise RuntimeError('Assembly STEP write failed')

def read_step(path):
    r=STEPControl_Reader()
    if r.ReadFile(str(path))!=IFSelect_RetDone:raise RuntimeError('Cannot read STEP')
    r.TransferRoots();return r.OneShape()
