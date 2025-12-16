# -*- coding: utf-8 -*-
# Panda3D Hexagonális Világ Generátor
# A Minecraft mintájára, de hatszögletű építőelemekkel.

from panda3d.core import (
    PandaNode, NodePath, GeomVertexFormat, GeomVertexData, GeomVertexWriter, 
    GeomTriangles, Geom, GeomNode, LVector3f, LColor, ClockObject,
    GeomVertexArrayFormat, InternalName
)
from direct.showbase.ShowBase import ShowBase
import math
import random

# --- GLOBÁLIS GEOMETRIA BEÁLLÍTÁSOK ---

# Explicit vertex format definíció, a metódusláncolás hibájának elkerülése érdekében.
# Lépésenként regisztráljuk a V3 (pozíció), C4 (szín) és N3 (normál) formátumot.
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
array_format.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)
array_format.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)

CUSTOM_HEX_FORMAT = GeomVertexFormat.registerFormat(array_format)

# --- GEOMETRIA DEFINÍCIÓK ÉS SEGÉDFÜGGVÉNYEK ---

HEX_SIZE = 1.0  # A hatszög (hexagon) sugara
HEX_HEIGHT_STEP = 0.5 # Egy szint magassága

# Egyszerű zajgenerátor (Perlin zaj helyett)
# A magasságot egy egyszerű szinuszos hullámzás adja
def simple_noise(x, y, scale=0.1, amplitude=5.0):
    """
    Egy egyszerű hullámzó zajfüggvény a magasság kiszámításához.
    """
    return int(amplitude * (math.sin(x * scale) + math.cos(y * scale)) + amplitude)

def get_hex_center(q, r):
    """
    Kiszámítja a hatszög 3D-s középpontját (axialis koordinátákból).
    Flat-top (lapos tetejű) elrendezést használunk.
    """
    x = HEX_SIZE * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = HEX_SIZE * (0 * q + 3/2 * r)
    return LVector3f(x, y, 0)

def get_hex_corner(center, i):
    """
    Kiszámítja a hatszög 6 sarokpontjának 2D koordinátáit.
    i: 0-tól 5-ig a sarok indexe.
    """
    angle_deg = 60 * i
    angle_rad = math.pi / 180 * angle_deg
    
    # A lapos tetejű hatszög miatt elforgatjuk a kiindulási szöget
    angle_rad += math.pi / 6 
    
    x = center.x + HEX_SIZE * math.cos(angle_rad)
    y = center.y + HEX_SIZE * math.sin(angle_rad)
    return x, y

def make_hex_prism(q, r, z_level, color):
    """
    Létrehoz egy hatszögletű hasábot (voxelt) a megadott koordinátákon és színnel.
    A geometria kézzel készül a Panda3D Geom osztályaival.
    """
    hex_center = get_hex_center(q, r)
    base_z = z_level * HEX_HEIGHT_STEP
    top_z = (z_level + 1) * HEX_HEIGHT_STEP

    # A Panda3D Geom objektumokhoz szükséges formátum
    format = CUSTOM_HEX_FORMAT
    vdata = GeomVertexData('hex_data', format, Geom.UHDynamic)
    vertex = GeomVertexWriter(vdata, 'vertex')
    color_writer = GeomVertexWriter(vdata, 'color')
    normal_writer = GeomVertexWriter(vdata, 'normal')
    tris = GeomTriangles(Geom.UHDynamic)

    # 6 sarokpont kiszámítása 2D-ben
    corners_2d = [get_hex_corner(hex_center, i) for i in range(6)]

    # --- TOP FACE --- (Felső lap)
    center_top_index = vdata.getNumRows() 
    vertex.addData3f(hex_center.x, hex_center.y, top_z)
    color_writer.addData4f(color.x * 1.0, color.y * 1.0, color.z * 1.0, color.w)
    normal_writer.addData3f(0, 0, 1) # Felfelé néző normál

    top_indices = []
    for i in range(6):
        cx, cy = corners_2d[i]
        index = vdata.getNumRows()
        top_indices.append(index)
        
        vertex.addData3f(cx, cy, top_z)
        color_writer.addData4f(color.x * 1.0, color.y * 1.0, color.z * 1.0, color.w)
        normal_writer.addData3f(0, 0, 1)

    # Háromszögek a felső laphoz
    for i in range(6):
        i0 = top_indices[i]
        i1 = top_indices[(i + 1) % 6]
        tris.addVertices(i0, center_top_index, i1)

    # --- BOTTOM FACE --- (Alsó lap)
    center_bottom_index = vdata.getNumRows() 
    vertex.addData3f(hex_center.x, hex_center.y, base_z)
    color_writer.addData4f(color.x * 0.8, color.y * 0.8, color.z * 0.8, color.w) # Sötétebb szín
    normal_writer.addData3f(0, 0, -1) # Lefelé néző normál

    bottom_indices = []
    for i in range(6):
        cx, cy = corners_2d[i]
        index = vdata.getNumRows()
        bottom_indices.append(index)
        
        vertex.addData3f(cx, cy, base_z)
        color_writer.addData4f(color.x * 0.8, color.y * 0.8, color.z * 0.8, color.w)
        normal_writer.addData3f(0, 0, -1)

    # Háromszögek az alsó laphoz (fordított sorrendben)
    for i in range(6):
        i0 = bottom_indices[i]
        i1 = bottom_indices[(i + 1) % 6]
        tris.addVertices(i1, center_bottom_index, i0)

    # --- SIDE FACES --- (Oldallapok)
    side_color = LColor(color.x * 0.9, color.y * 0.9, color.z * 0.9, color.w)

    for i in range(6):
        # Aktuális és következő sarokpont koordinátái
        p0_2d = corners_2d[i]
        p1_2d = corners_2d[(i + 1) % 6]
        
        # Kiszámítja az oldalra mutató normál vektort
        mid_x = (p0_2d[0] + p1_2d[0]) / 2.0
        mid_y = (p0_2d[1] + p1_2d[1]) / 2.0
        
        norm_x = mid_x - hex_center.x
        norm_y = mid_y - hex_center.y
        
        # Létrehozzuk az oldalsó normál vektort
        side_normal = LVector3f(norm_x, norm_y, 0)
        
        # Normalizálás in-place. A Panda3D verzióknál ez adja vissza a True/False-t.
        # Ha False-t ad vissza (nulla vektor), megakadályozzuk, hogy a side_normal True/False legyen.
        if not side_normal.normalize():
            # Ha valamiért (0,0,0) a normál vektor, adjunk egy default értéket.
            # Ez a biztonsági fallback megakadályozza az AttributeError-t.
            side_normal = LVector3f(1, 0, 0)

        # Új vertexek létrehozása a négyzet mind a 4 sarkához, egyedi normállal
        
        # B0 (Alsó, p0)
        idx_b0 = vdata.getNumRows()
        vertex.addData3f(p0_2d[0], p0_2d[1], base_z)
        color_writer.addData4f(side_color.x, side_color.y, side_color.z, side_color.w)
        normal_writer.addData3f(side_normal.x, side_normal.y, side_normal.z)

        # T0 (Felső, p0)
        idx_t0 = vdata.getNumRows()
        vertex.addData3f(p0_2d[0], p0_2d[1], top_z)
        color_writer.addData4f(side_color.x, side_color.y, side_color.z, side_color.w)
        normal_writer.addData3f(side_normal.x, side_normal.y, side_normal.z)

        # T1 (Felső, p1)
        idx_t1 = vdata.getNumRows()
        vertex.addData3f(p1_2d[0], p1_2d[1], top_z)
        color_writer.addData4f(side_color.x, side_color.y, side_color.z, side_color.w)
        normal_writer.addData3f(side_normal.x, side_normal.y, side_normal.z)
        
        # B1 (Alsó, p1)
        idx_b1 = vdata.getNumRows()
        vertex.addData3f(p1_2d[0], p1_2d[1], base_z)
        color_writer.addData4f(side_color.x, side_color.y, side_color.z, side_color.w)
        normal_writer.addData3f(side_normal.x, side_normal.y, side_normal.z)

        # Két háromszög a négyszöghöz (quad)
        tris.addVertices(idx_b0, idx_t0, idx_t1)
        tris.addVertices(idx_b0, idx_t1, idx_b1)


    geom = Geom(vdata)
    geom.addPrimitive(tris)

    # A Geom-ot GeomNode-ba helyezzük
    node = GeomNode('HexVoxel')
    node.addGeom(geom)
    
    return NodePath(node)

# --- FŐ ALKALMAZÁS ---

class HexVoxelWorld(ShowBase):
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
        if height < 2:
            # Víz (kék)
            return LColor(0.1, 0.4, 0.9, 1) # Világosabb kék
        elif height < 5:
            # Fű/Síkság (világos zöld)
            return LColor(0.3, 0.8, 0.3, 1) # Világosabb zöld
        elif height < 8:
            # Hegyoldal (szürke-barna)
            return LColor(0.6, 0.5, 0.4, 1)
        else:
            # Csúcs/Hó (TISZTA FEHÉR)
            return LColor(1.0, 1.0, 1.0, 1) # Tiszta fehér a kért szín
        
    def generate_world(self):
        """A hatszögletű világ procedurális generálása."""
        
        print(f"Világ generálása indul: {self.world_size}x{self.world_size} hatszög.")
        
        # Az összes generált voxel egy közös NodePath alá kerül a könnyebb kezelés érdekében
        self.world_root = self.render.attachNewNode("WorldRoot")

        for q in range(-self.world_size, self.world_size):
            for r in range(-self.world_size, self.world_size):
                # Csak a gyémánt alakú (axial) rácson belüli hatszögeket generáljuk
                if abs(q + r) > self.world_size:
                    continue

                # Kiszámoljuk a magasságot zajfüggvény alapján
                height_blocks = simple_noise(q, r, scale=0.15, amplitude=3.0)
                
                # A hatszögek építése a legalsó szinttől a zaj által meghatározott magasságig
                for z in range(height_blocks):
                    
                    # Ha a legalsó réteg (dirt/kő)
                    if z == 0:
                        voxel_color = LColor(0.5, 0.3, 0.1, 1) # Barna (föld/kő)
                    # Ha a legfelső réteg (biome)
                    elif z == height_blocks - 1:
                        voxel_color = self.get_color_by_height(height_blocks)
                    # Ha középső réteg (dirt)
                    else:
                        voxel_color = LColor(0.4, 0.25, 0.05, 1) # Sötétbarna
                        
                    # Létrehozza a 3D hatszög hasábot
                    hex_voxel = make_hex_prism(q, r, z, voxel_color)
                    
                    # Hozzáadja a világhoz
                    hex_voxel.reparentTo(self.world_root)

        print("Világ generálása kész.")

if __name__ == "__main__":
    app = HexVoxelWorld()
    app.run()