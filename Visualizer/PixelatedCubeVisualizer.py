from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    DirectionalLight, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode
)
from direct.task import Task
import random

# Konfiguráció az ablak beállításaihoz
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Zöld Pixeles Kocka")
loadPrcFileData("", "show-frame-rate-meter true")

# Kocka geometria generálása pixeles rácshatással
def create_grid_cube_mesh(grid_size=8, color_base=VBase4(0.5, 0.7, 0.2, 1.0)):
    """
    Programozottan generál egy kocka mesh-t, amelynek minden felülete 
    kisebb négyzetekből (pixelekből) áll, a megadott színalap árnyalataiban.
    """
    # V3n3c4: 3D Vertex, 3D Normal, 4D Color (RGBa)
    format = GeomVertexFormat.getV3n3c4()
    vdata = GeomVertexData('grid_cube_data', format, Geom.UHStatic)
    
    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    color = GeomVertexWriter(vdata, 'color')

    s = 0.5  # A kocka alap félmérete (a középpontból)
    
    # A 6 lap normálisai (irányai) és a lokális U/V tengelyek
    face_data = [
        # Normal, U Axis (Right/Width), V Axis (Up/Height)
        (LVector3(0, -1, 0), LVector3(1, 0, 0), LVector3(0, 0, 1)),  # Front (-Y)
        (LVector3(0, 1, 0), LVector3(-1, 0, 0), LVector3(0, 0, 1)),  # Back (+Y)
        (LVector3(1, 0, 0), LVector3(0, 0, 1), LVector3(0, 1, 0)),   # Right (+X)
        (LVector3(-1, 0, 0), LVector3(0, 0, 1), LVector3(0, -1, 0)),  # Left (-X)
        (LVector3(0, 0, 1), LVector3(1, 0, 0), LVector3(0, 1, 0)),   # Top (+Z)
        (LVector3(0, 0, -1), LVector3(1, 0, 0), LVector3(0, -1, 0)), # Bottom (-Z)
    ]
    
    pixel_size = 2 * s / grid_size # Egy kis négyzet élének hossza
    prim = GeomTriangles(Geom.UHStatic)
    vertex_count = 0

    # Grid generálása minden lapra
    for normal_vec, u_vec, v_vec in face_data:
        
        # A laphoz tartozó egyedi színalap véletlenszerű árnyalata
        face_r = color_base[0] + random.uniform(-0.1, 0.1)
        face_g = color_base[1] + random.uniform(-0.1, 0.1)
        face_b = color_base[2] + random.uniform(-0.1, 0.1)
        face_base_color = VBase4(max(0, min(1, face_r)), max(0, min(1, face_g)), max(0, min(1, face_b)), 1.0)
        
        normal_distance = normal_vec * s

        for i in range(grid_size): # U tengely (0-tól 1-ig)
            for j in range(grid_size): # V tengely (0-tól 1-ig)
                
                # A pixel lokális koordinátái a lapon
                u_min = -s + i * pixel_size
                v_min = -s + j * pixel_size
                
                # Véletlenszerű színvariáció a pixelhez (még nagyobb pixeles kontraszt)
                rand_r = face_base_color[0] + random.uniform(-0.1, 0.1)
                rand_g = face_base_color[1] + random.uniform(-0.1, 0.1)
                rand_b = face_base_color[2] + random.uniform(-0.1, 0.1)
                pixel_color = VBase4(max(0, min(1, rand_r)), max(0, min(1, rand_g)), max(0, min(1, rand_b)), 1.0)

                # A 4 csúcs 3D pozíciójának kiszámítása
                v0 = normal_distance + u_vec * u_min + v_vec * v_min
                v1 = normal_distance + u_vec * (u_min + pixel_size) + v_vec * v_min
                v2 = normal_distance + u_vec * (u_min + pixel_size) + v_vec * (v_min + pixel_size)
                v3 = normal_distance + u_vec * u_min + v_vec * (v_min + pixel_size)

                vertices = [v0, v1, v2, v0, v2, v3] # Két háromszög

                for k in range(6): # 6 csúcs 
                    vertex.addData3f(vertices[k][0], vertices[k][1], vertices[k][2])
                    normal.addData3f(normal_vec[0], normal_vec[1], normal_vec[2])
                    color.addData4f(pixel_color) # Minden csúcsra beállítjuk az egységes pixelszínt
                
                # Indexek hozzáadása a két háromszöghöz
                prim.addVertices(vertex_count + 0, vertex_count + 1, vertex_count + 2)
                prim.addVertices(vertex_count + 3, vertex_count + 4, vertex_count + 5)
                
                vertex_count += 6 # 6 csúcs/pixel

    geom = Geom(vdata)
    geom.addPrimitive(prim)
    
    node = GeomNode('grid_cube_geom')
    node.addGeom(geom)
    
    return NodePath(node)

class PixelatedCubeVisualizer(ShowBase):
    """
    Panda3D application focusing on a single, programmatically generated cube
    with a multi-colored 'pixelated' appearance, rotated by a task.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        self.setBackgroundColor(0.0, 0.0, 0.0, 1) # Fekete háttér
        self.cam.setPos(10, -15, 10)
        self.cam.lookAt(0, 0, 0)
        
        # Set up Lighting (Fénybeállítások)
        # Erős ambient fény, hogy a csúcsszínek torzítás nélkül látszódjanak
        alight = AmbientLight('alight')
        alight.setColor(VBase4(1.0, 1.0, 1.0, 1)) 
        self.render.setLight(self.render.attachNewNode(alight))

        # --- CENTER CUBE (Központi kocka) ---
        # Létrehozzuk a rácsos kockát 8x8-as felbontásban, zöld/arany alapszínnel
        self.center_cube = create_grid_cube_mesh(grid_size=8, color_base=VBase4(0.8, 0.7, 0.3, 1.0))
        self.center_cube.reparentTo(self.render)
        self.center_cube.setScale(5.0) # Nagyon nagy
        self.center_cube.setPos(0, 0, 0)
        
        # Kikapcsoljuk az anyagszínt, hogy a csúcsszíneket használja
        self.center_cube.setMaterialOff(1) 

        # --- 2. Rotation Task Setup (Forgatás Feladat) ---
        self.taskMgr.add(self.rotate_cube, "RotateCubeTask")

    def rotate_cube(self, task):
        """Rotates the center cube."""
        self.center_cube.setH(self.center_cube.getH() + 0.5)
        self.center_cube.setP(self.center_cube.getP() + 0.3)
        self.center_cube.setR(self.center_cube.getR() + 0.1)
        return Task.cont

# Run the application
if __name__ == "__main__":
    app = PixelatedCubeVisualizer()
    app.run()