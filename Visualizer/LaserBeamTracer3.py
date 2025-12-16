from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomLines, Geom, GeomNode,
    TransparencyAttrib, GeomTriangles # Hozzáadva a hiányzó GeomTriangles
)
from direct.task import Task
from direct.interval.IntervalGlobal import Sequence, Func, Wait, Parallel, LerpFunc
import random
import math

# Configuration for the window settings
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Lézersugár Rajzoló (Lövés + Részecske)")
loadPrcFileData("", "show-frame-rate-meter true")

# Kocka geometria generálása a részecskékhez (3D objektum)
def create_cube_mesh():
    """Generates a cube mesh programmatically."""
    format = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData('cube_data', format, Geom.UHStatic)
    
    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    texcoord = GeomVertexWriter(vdata, 'texcoord')

    s = 0.5 
    points = [
        (-s, -s, -s), ( s, -s, -s), ( s,  s, -s), (-s,  s, -s), 
        (-s, -s,  s), ( s, -s,  s), ( s,  s,  s), (-s,  s,  s)
    ]
    faces = [0, 1, 2, 3, 4, 7, 6, 5, 1, 5, 6, 2, 0, 3, 7, 4, 3, 2, 6, 7, 0, 4, 5, 1]
    normals = [( 0, -1,  0), ( 0,  1,  0), ( 1,  0,  0), (-1,  0,  0), ( 0,  0,  1), ( 0,  0, -1)]

    prim = GeomTriangles(Geom.UHStatic)
    for i in range(6): 
        p1, p2, p3 = points[faces[i*4 + 0]], points[faces[i*4 + 1]], points[faces[i*4 + 2]]
        p4, p5, p6 = points[faces[i*4 + 0]], points[faces[i*4 + 2]], points[faces[i*4 + 3]]
        tris = [p1, p2, p3, p4, p5, p6]
        
        for k in range(6):
            vertex.addData3f(tris[k][0], tris[k][1], tris[k][2])
            normal.addData3f(normals[i][0], normals[i][1], normals[i][2])
            if k == 0 or k == 3: texcoord.addData2f(0.0, 0.0)
            elif k == 1: texcoord.addData2f(1.0, 0.0)
            elif k == 2 or k == 4: texcoord.addData2f(1.0, 1.0)
            elif k == 5: texcoord.addData2f(0.0, 1.0)

        v_offset = i * 6
        prim.addVertices(v_offset + 0, v_offset + 1, v_offset + 2)
        prim.addVertices(v_offset + 3, v_offset + 4, v_offset + 5)
        
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode('cube_geom')
    node.addGeom(geom)
    return NodePath(node)

# Lézersugár geometria (vonal) generálása
def create_laser_geometry(start_point, end_point, color):
    """
    Programmatically generates a line segment (the laser beam) using GeomLines.
    """
    # V3c4 format: 3D Vertex, 4D Color (RGBa)
    format = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData('laser_data', format, Geom.UHStatic)
    
    vertex = GeomVertexWriter(vdata, 'vertex')
    color_writer = GeomVertexWriter(vdata, 'color')

    # Add start and end points
    vertex.addData3f(start_point.x, start_point.y, start_point.z)
    vertex.addData3f(end_point.x, end_point.y, end_point.z)
    
    # Add color for both vertices
    color_writer.addData4f(color)
    color_writer.addData4f(color)

    # Create the line primitive
    lines = GeomLines(Geom.UHStatic)
    lines.addVertices(0, 1) # Define the line from vertex 0 to vertex 1
    
    geom = Geom(vdata)
    geom.addPrimitive(lines)
    
    node = GeomNode('laser_geom')
    node.addGeom(geom)
    
    return NodePath(node)

class LaserBeamTracer(ShowBase):
    """
    Panda3D application that simulates a laser firing every 1 second, 
    with a metallic impact particle at the target.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        self.setBackgroundColor(0.05, 0.05, 0.1, 1) # Dark blue background
        self.cam.setPos(0, -30, 10)
        self.cam.lookAt(0, 0, 0)
        
        # Set up Lighting (Fénybeállítások)
        alight = AmbientLight('alight')
        # Erős fény az "áttetsző" lila szín kiemeléséhez
        alight.setColor(VBase4(0.5, 0.5, 0.5, 1)) 
        self.render.setLight(self.render.attachNewNode(alight))

        # --- 2. Laser Setup (Lézersugár Beállítása) ---
        self.start_point = LVector3(0, 0, 0) # Fixed origin point
        self.laser_color = VBase4(0.0, 1.0, 0.5, 1.0) # Bright green/cyan laser
        
        # --- 3. Firing Task (Lövés Feladat) ---
        self.taskMgr.doMethodLater(0.0, self.fire_laser, "LaserFireTask")
        self.time = 0.0

    def get_new_target_point(self):
        """Calculates a new target point based on current time."""
        self.time += 1.0
        
        # Complex, 3D trajectory calculation
        x = math.sin(self.time * 1.5) * 8
        y = math.cos(self.time * 2.0) * 8
        z = 5 + math.sin(self.time * 0.7) * 4 
        
        return LVector3(x, y, z)

    def spawn_impact_particle(self, position):
        """
        Creates a purple, metallic-looking particle at the impact point 
        and defines its explosive life cycle.
        """
        # Lila (Purple) szín, magasabb komponensek a fém/fényes hatáshoz
        metallic_purple = VBase4(0.7, 0.3, 0.9, 1.0) 
        
        particle = create_cube_mesh()
        particle.reparentTo(self.render)
        particle.setPos(position)
        particle.setScale(0.5)
        
        # Állítsuk be az anyagszínt. Mivel nem használunk bonyolult árnyékolót, 
        # a fényes/metalikus hatás eléréséhez világos, telített színt használunk.
        particle.setColor(metallic_purple, 1)
        particle.setTransparency(TransparencyAttrib.MAlpha)

        life_duration = 0.5 # A részecske rövid élettartama
        
        # 1. Mozgás: Kis mértékű robbanás/szétszóródás
        # Enyhe, véletlen eltolódás a becsapódási ponttól
        offset_vec = LVector3(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)) * 0.5
        
        move_interval = particle.posInterval(
            life_duration,
            pos=position + offset_vec,
            startPos=position
        )
        
        # 2. Vizuális effektus: Gyors növekedés és halványulás
        scale_interval = particle.scaleInterval(life_duration, 0.0, startScale=0.5)
        
        fade_interval = particle.colorScaleInterval(
            life_duration * 0.8,
            VBase4(1.0, 1.0, 1.0, 0.0), # Teljesen átlátszóvá válik
            startColorScale=VBase4(1.0, 1.0, 1.0, 1.0)
        )
        
        # Kombináció és takarítás
        impact_sequence = Sequence(
            Parallel(move_interval, scale_interval, fade_interval),
            Func(particle.removeNode)
        )
        
        impact_sequence.start()


    def fire_laser(self, task):
        """
        Creates and animates a single laser beam and spawns an impact particle.
        """
        end_point = self.get_new_target_point()
        
        # 1. Lézersugár létrehozása (Line)
        new_laser = create_laser_geometry(self.start_point, end_point, self.laser_color)
        new_laser.reparentTo(self.render)
        new_laser.setTwoSided(True)
        new_laser.setRenderModeThickness(3.0)
        new_laser.setTransparency(TransparencyAttrib.MAlpha)
        new_laser.setColorScale(1.0, 1.0, 1.0, 1.0)
        
        # 2. Részecske létrehozása (Impact Particle)
        self.spawn_impact_particle(end_point)
        
        # 3. Lézersugár eltűnésének animációja
        visibility_duration = 0.1
        fade_duration = 0.4
        
        fade_out = new_laser.colorScaleInterval(
            fade_duration,
            VBase4(1.0, 1.0, 1.0, 0.0),
            startColorScale=new_laser.getColorScale()
        )
        
        laser_sequence = Sequence(
            Wait(visibility_duration),
            fade_out,
            Func(new_laser.removeNode)
        )
        
        laser_sequence.start()

        # Időzítő a következő lövéshez (1 másodperc)
        task.delayTime = 1.0
        return Task.again

# Run the application
if __name__ == "__main__":
    app = LaserBeamTracer()
    app.run()