from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, LVector4,
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomLines, Geom, GeomNode,
    DirectionalLight
)
from direct.task import Task
import math
import itertools

# Configuration for the window settings
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D 4D Hiperkocka Vetítés")
loadPrcFileData("", "show-frame-rate-meter true")

class Hypercube4DProjection(ShowBase):
    """
    Panda3D alkalmazás, amely a 4D Hiperkocka (Tesseract) 3D-s vetítését 
    generálja és animálja, szimulálva a forgást a 4D térben.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        self.setBackgroundColor(0.0, 0.0, 0.15, 1) # Sötétkék háttér
        self.cam.setPos(0, -50, 0)
        self.cam.lookAt(0, 0, 0)
        
        # Fénybeállítások: Ambient fény a drótváz láthatóságáért
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.8, 0.8, 0.8, 1)) 
        self.render.setLight(self.render.attachNewNode(alight))

        # --- 2. 4D Structure Setup (4D Struktúra Beállítása) ---
        self.define_hypercube_structure()
        self.hypercube_node = None # A vetített geometria tárolója
        
        self.angle_zw = 0.0 # Forgásszög a ZW síkban (a vizuális hatásért)
        
        # --- 3. Animation Task (Animációs Feladat) ---
        # A feladat minden képkockában frissíti a 4D forgatást és újraépíti a 3D vetületet
        self.taskMgr.add(self.update_hypercube, "UpdateHypercubeTask")

    def define_hypercube_structure(self):
        """
        Létrehozza a hiperkocka 16 csúcsát (x, y, z, w = +/- 1) és 32 élét.
        """
        scale_factor = 5.0 # Méretezés
        
        self.vertices_4d_coords = []
        # Létrehozzuk a 16 csúcsot (minden koordináta +/- 1)
        for x, y, z, w in itertools.product([-1, 1], repeat=4):
            self.vertices_4d_coords.append(LVector4(x * scale_factor, y * scale_factor, z * scale_factor, w * scale_factor))
        
        # Élek meghatározása: összekötés, ahol csak 1 koordináta tér el (Hamming távolság = 1)
        self.edges_list = []
        for i in range(16):
            for j in range(i + 1, 16):
                v1 = self.vertices_4d_coords[i]
                v2 = self.vertices_4d_coords[j]
                
                # Ellenőrizzük, hány koordináta különbözik
                diffs = 0
                if v1.x != v2.x: diffs += 1
                if v1.y != v2.y: diffs += 1
                if v1.z != v2.z: diffs += 1
                if v1.w != v2.w: diffs += 1
                
                if diffs == 1:
                    self.edges_list.append((i, j))

    def rotate_and_project(self, point_4d):
        """
        Forgatás alkalmazása a ZW (Z-W) szuper-síkon, majd perspektivikus vetítés 3D-be.
        """
        x, y, z, w = point_4d.x, point_4d.y, point_4d.z, point_4d.w
        angle = self.angle_zw
        
        # 1. 4D Forgatás (Z-W síkban)
        z_rotated = z * math.cos(angle) - w * math.sin(angle)
        w_rotated = z * math.sin(angle) + w * math.cos(angle)
        
        x_rotated = x
        y_rotated = y
        
        # 2. Perspektivikus vetítés (A W' koordináta adja a mélységi hatást/skálázást)
        distance = 30.0 # Virtuális távolság a 4D kamera előtt
        # Az a pont, ami közelebb van a 4. dimenziós "kamerához" (kisebb w_rotated), nagyobb lesz.
        divisor = distance - w_rotated
        
        # Kerüljük el az osztást 0-val (bár itt a distance=30 biztosítja ezt)
        if divisor == 0:
            return LVector3(0, 0, 0)
            
        scale_factor = 1.0 / divisor
        
        x_proj = x_rotated * scale_factor
        y_proj = y_rotated * scale_factor
        z_proj = z_rotated * scale_factor
        
        return LVector3(x_proj, y_proj, z_proj) * 15.0 # Végső skálázás a jelenethez

    def create_lines_geometry_4d(self):
        """
        Generálja a hiperkocka vetületének geometriáját a jelenlegi 4D forgatási szöggel.
        """
        format = GeomVertexFormat.getV3c4()
        vdata = GeomVertexData('hypercube_data', format, Geom.UHStatic)
        
        vertex_writer = GeomVertexWriter(vdata, 'vertex')
        color_writer = GeomVertexWriter(vdata, 'color')
        lines = GeomLines(Geom.UHStatic)

        hypercube_color = VBase4(0.3, 0.9, 0.9, 1.0) # Türkiz/Cián drótváz szín
        
        # 1. Csúcsok 3D-be vetítése és VData-ba írása
        for p_4d in self.vertices_4d_coords:
            p_3d = self.rotate_and_project(p_4d)
            
            vertex_writer.addData3f(p_3d.x, p_3d.y, p_3d.z)
            color_writer.addData4f(hypercube_color)

        # 2. Élek hozzáadása vonalszakaszokként
        for v1_idx, v2_idx in self.edges_list:
            lines.addVertices(v1_idx, v2_idx)
        
        geom = Geom(vdata)
        geom.addPrimitive(lines)
        
        node = GeomNode('hypercube_geom')
        node.addGeom(geom)
        
        node_path = NodePath(node)
        node_path.setRenderModeThickness(2.0) # Vonal vastagságának beállítása
        return node_path

    def update_hypercube(self, task):
        """
        Frissíti a 4D forgásszöget és újraépíti a geometriát.
        """
        # Folyamatos forgatás a ZW síkban (lassú, lebegő hatás)
        self.angle_zw += globalClock.getDt() * 0.5 
        
        # Régi geometria eltávolítása
        if self.hypercube_node:
            self.hypercube_node.removeNode()

        # Új geometria generálása az aktuális forgatás alapján
        self.hypercube_node = self.create_lines_geometry_4d()
        self.hypercube_node.reparentTo(self.render)

        return Task.cont

# Run the application
if __name__ == "__main__":
    app = Hypercube4DProjection()
    app.run()