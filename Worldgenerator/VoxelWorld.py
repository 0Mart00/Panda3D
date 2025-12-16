# -*- coding: utf-8 -*-
# Panda3D Kocka Világ Generátor (Minecraft stílus)
# A korábbi hatszöges kód átalakítva standard kockákra.

from panda3d.core import (
    PandaNode, NodePath, GeomVertexFormat, GeomVertexData, GeomVertexWriter, 
    GeomTriangles, Geom, GeomNode, LVector3f, LColor, ClockObject,
    GeomVertexArrayFormat, InternalName
)
from direct.showbase.ShowBase import ShowBase
import math
import random

# --- GLOBÁLIS GEOMETRIA BEÁLLÍTÁSOK ---

# Explicit vertex format definíció: Pozíció (V3), Szín (C4), Normál (N3)
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
array_format.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)
array_format.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)

CUSTOM_VOXEL_FORMAT = GeomVertexFormat.registerFormat(array_format)

# --- GEOMETRIA DEFINÍCIÓK ÉS SEGÉDFÜGGVÉNYEK ---

VOXEL_SIZE = 1.0  # Egy kocka mérete
HALF_VOXEL = VOXEL_SIZE / 2.0

# Kocka sarokpontjai lokális koordinátákban
CUBE_VERTICES = [
    LVector3f(-HALF_VOXEL, -HALF_VOXEL, -HALF_VOXEL), # 0
    LVector3f( HALF_VOXEL, -HALF_VOXEL, -HALF_VOXEL), # 1
    LVector3f( HALF_VOXEL,  HALF_VOXEL, -HALF_VOXEL), # 2
    LVector3f(-HALF_VOXEL,  HALF_VOXEL, -HALF_VOXEL), # 3
    LVector3f(-HALF_VOXEL, -HALF_VOXEL,  HALF_VOXEL), # 4
    LVector3f( HALF_VOXEL, -HALF_VOXEL,  HALF_VOXEL), # 5
    LVector3f( HALF_VOXEL,  HALF_VOXEL,  HALF_VOXEL), # 6
    LVector3f(-HALF_VOXEL,  HALF_VOXEL,  HALF_VOXEL)  # 7
]

# Kocka lapjai (normál, vertex indexek)
# Minden lap két háromszögből áll
CUBE_FACES = [
    # Top (+Z)
    (( 0, 0, 1), [4, 7, 6, 5]),
    # Bottom (-Z)
    (( 0, 0,-1), [0, 1, 2, 3]),
    # Front (-Y)
    (( 0,-1, 0), [0, 4, 5, 1]),
    # Back (+Y)
    (( 0, 1, 0), [3, 2, 6, 7]),
    # Left (-X)
    ((-1, 0, 0), [0, 3, 7, 4]),
    # Right (+X)
    (( 1, 0, 0), [1, 5, 6, 2]),
]

# Egyszerű zajgenerátor (Perlin zaj helyett)
def simple_noise(x, y, scale=0.1, amplitude=10.0):
    """
    Egy egyszerű hullámzó zajfüggvény a magasság kiszámításához.
    """
    return int(amplitude * (math.sin(x * scale) + math.cos(y * scale)) + amplitude)

def make_cube(x_idx, y_idx, z_idx, color):
    """
    Létrehoz egy kocka (voxel) modellt a megadott rács koordinátán.
    """
    center_pos = LVector3f(
        x_idx * VOXEL_SIZE,
        y_idx * VOXEL_SIZE,
        z_idx * VOXEL_SIZE
    )

    format = CUSTOM_VOXEL_FORMAT
    vdata = GeomVertexData('cube_data', format, Geom.UHDynamic)
    vertex = GeomVertexWriter(vdata, 'vertex')
    color_writer = GeomVertexWriter(vdata, 'color')
    normal_writer = GeomVertexWriter(vdata, 'normal')
    tris = GeomTriangles(Geom.UHDynamic)
    
    # A base_index tárolja, hol kezdjük el a vertexek írását ebben a ciklusban
    base_index = vdata.getNumRows()
    
    # Kocka sarokpontjait írjuk be egyszer
    for v_local in CUBE_VERTICES:
        # Globális pozíció kiszámítása
        v_global = center_pos + v_local
        vertex.addData3f(v_global.x, v_global.y, v_global.z)
        # Az indexet majd a CUBE_FACES listából vesszük, de a színt hozzáadjuk
        color_writer.addData4f(color.x, color.y, color.z, color.w)
        # Normál vektort csak a lapoknál adjuk hozzá

    # Lapok (Faces) létrehozása
    for normal_tuple, indices in CUBE_FACES:
        # A normál vektor
        normal = LVector3f(normal_tuple[0], normal_tuple[1], normal_tuple[2])
        
        # A Panda3D-ben a normálokat a vertexekhez kell rendelni.
        # Itt a kényelem kedvéért minden laphoz külön vertexet adunk a Panda3D-nek,
        # hogy a normálok helyesek legyenek a lapon, bár az alacsony szintű kód nem hatékony.
        
        v_idx_start = vdata.getNumRows()
        
        # Lap 4 sarkának hozzáadása
        for i in indices:
            v_local = CUBE_VERTICES[i]
            v_global = center_pos + v_local
            
            vertex.addData3f(v_global.x, v_global.y, v_global.z)
            color_writer.addData4f(color.x, color.y, color.z, color.w)
            normal_writer.addData3f(normal.x, normal.y, normal.z)

        # Két háromszög a laphoz
        tris.addVertices(v_idx_start + 0, v_idx_start + 1, v_idx_start + 2)
        tris.addVertices(v_idx_start + 0, v_idx_start + 2, v_idx_start + 3)

    geom = Geom(vdata)
    geom.addPrimitive(tris)

    # A Geom-ot GeomNode-ba helyezzük
    node = GeomNode('Voxel')
    node.addGeom(geom)
    
    return NodePath(node)

# --- FŐ ALKALMAZÁS ---

class VoxelWorld(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0.2, 0.2, 0.4) # Sötétkék égbolt

        # Engedélyezi a shader generálást a jobb megvilágítás érdekében
        self.render.setShaderAuto() 

        # Kamera beállítások
        self.disableMouse()
        self.camera.setPos(-20, -20, 30)
        self.camera.lookAt(0, 0, 0)
        self.cam_angle = 0
        self.cam_dist = 40
        self.cam_height = 10
        self.taskMgr.add(self.camera_task, "CameraControlTask")

        # Fény hozzáadása
        from panda3d.core import DirectionalLight
        dlight = DirectionalLight('dlight')
        dlight.setColor(LColor(1, 1, 1, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(45, -45, 0)
        self.render.setLight(dlnp)

        # Globális változók
        self.world_size = 15 # A generált rács mérete
        self.generate_world()

    def camera_task(self, task):
        """Kamera körbeforgatása a világ körül."""
        dt = globalClock.getDt()
        
        # A kamera körbefordul a világ középpontja körül
        self.cam_angle += 10.0 * dt  # Fordulási sebesség
        
        # Pozíció kiszámítása
        x = self.cam_dist * math.cos(math.radians(self.cam_angle))
        y = self.cam_dist * math.sin(math.radians(self.cam_angle))
        
        self.camera.setPos(x, y, self.cam_height)
        self.camera.lookAt(0, 0, 0)
        
        return task.cont

    def get_color_by_height(self, height):
        """Magasság alapján színt rendel a voxelhez (Minecraft-stílusú biómok)."""
        if height < 3:
            # Víz (kék)
            return LColor(0.1, 0.4, 0.9, 1) 
        elif height < 7:
            # Fű/Síkság (világos zöld)
            return LColor(0.3, 0.8, 0.3, 1) 
        elif height < 12:
            # Hegyoldal (szürke-barna)
            return LColor(0.6, 0.5, 0.4, 1)
        else:
            # Csúcs/Hó (TISZTA FEHÉR)
            return LColor(1.0, 1.0, 1.0, 1) 
        
    def generate_world(self):
        """A kockaalapú világ procedurális generálása."""
        
        print(f"Voxel világ generálása indul: {self.world_size}x{self.world_size} területen.")
        
        # Az összes generált voxel egy közös NodePath alá kerül
        self.world_root = self.render.attachNewNode("WorldRoot")

        # Két ciklus a 2D rácshoz (x, y)
        for x_idx in range(-self.world_size, self.world_size):
            for y_idx in range(-self.world_size, self.world_size):
                
                # Kiszámoljuk a magasságot zajfüggvény alapján
                height_blocks = simple_noise(x_idx, y_idx, scale=0.1, amplitude=5.0)
                
                # A kockák építése a legalsó szinttől a zaj által meghatározott magasságig
                for z_idx in range(height_blocks):
                    
                    # Ha a legalsó réteg (kő)
                    if z_idx == 0:
                        voxel_color = LColor(0.5, 0.5, 0.5, 1) # Szürke (kő)
                    # Ha a legfelső réteg (biome)
                    elif z_idx == height_blocks - 1:
                        voxel_color = self.get_color_by_height(height_blocks)
                    # Ha középső réteg (föld)
                    else:
                        voxel_color = LColor(0.4, 0.25, 0.05, 1) # Sötétbarna (föld)
                        
                    # Létrehozza a 3D kockát
                    cube_voxel = make_cube(x_idx, y_idx, z_idx, voxel_color)
                    
                    # Hozzáadja a világhoz
                    cube_voxel.reparentTo(self.world_root)

        print("Voxel világ generálása kész.")

if __name__ == "__main__":
    app = VoxelWorld()
    app.run()