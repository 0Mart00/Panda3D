from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode,
    TransparencyAttrib
)
from direct.task import Task
from direct.interval.IntervalGlobal import Sequence, Parallel, LerpFunc, Func, Wait
import random
import math

# Configuration for the window settings
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Belépés a Kocka Világba")
loadPrcFileData("", "show-frame-rate-meter true")

# Kocka geometria generálása a modellek helyett
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


class EnteringCubeWorld(ShowBase):
    """
    Simulates entering a cube world: the background color switches from 
    white (outside) to black (inside) as the camera passes through the cube's expanding surface.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- Constants (Állandók) ---
        self.WHITE = VBase4(1.0, 1.0, 1.0, 1.0)
        self.BLACK = VBase4(0.0, 0.0, 0.0, 1.0)
        
        # --- 1. Initial Scene Setup (Kezdeti beállítások) ---
        self.setBackgroundColor(self.WHITE) # Alapból fehér háttér
        
        self.cam.setPos(0, -30, 0) # Kezdeti pozíció: messze a kockától
        self.cam.lookAt(0, 0, 0)
        
        alight = AmbientLight('alight')
        alight.setColor(VBase4(1.0, 1.0, 1.0, 1)) # Erős fény, hogy a fehér kocka látszódjon
        self.render.setLight(self.render.attachNewNode(alight))

        # --- 2. Central Cube (Központi Kocka) ---
        self.world_cube = create_cube_mesh()
        self.world_cube.reparentTo(self.render)
        self.world_cube.setScale(2.0) # Kezdeti kis méret
        self.world_cube.setPos(0, 0, 0)
        self.world_cube.setColor(VBase4(0.8, 0.8, 0.8, 1.0)) # Szürke/fehér kocka
        self.world_cube.setTwoSided(True) # Fontos: Látni fogjuk a belső oldalt is!
        
        # Rotációs feladat hozzáadása a jobb láthatóságért
        self.taskMgr.add(self.rotate_object, "RotateObjectTask")
        
        # --- 3. Animation Start (Animáció Indítása) ---
        self.start_transition()

    def rotate_object(self, task):
        """Forgatja a kockát."""
        self.world_cube.setH(self.world_cube.getH() + 0.2)
        return Task.cont

    def bg_color_lerp(self, t, start_color, end_color):
        """Segédfüggvény a háttérszín animálásához."""
        r = start_color.x * (1 - t) + end_color.x * t
        g = start_color.y * (1 - t) + end_color.y * t
        b = start_color.z * (1 - t) + end_color.z * t
        self.win.setClearColor(VBase4(r, g, b, 1.0))

    def start_transition(self):
        """Elindítja a belépési szekvenciát."""
        
        # --- PHASE 1: Approach and Scale Up (Közeledés és Skálázás) ---
        
        # 1. Kocka növekedése: Lassan növekszik a közeledés alatt
        scale_approach = self.world_cube.scaleInterval(
            1.5, # 1.5 másodperc
            10.0, # Növekedés 10-es skáláig
            startScale=2.0
        )
        
        # 2. Kamera közeledése: A kocka felé halad
        cam_approach = self.cam.posInterval(
            1.5,
            pos=LVector3(0, -10, 0), # Közel, de még kívül
            startPos=LVector3(0, -30, 0)
        )

        # --- PHASE 2: Entering the Cube and Background Change (Belépés) ---
        
        # 3. Gyors növekedés: A kocka felrobbanóan megnő, miközben belépünk
        scale_enter = self.world_cube.scaleInterval(
            0.5, # Nagyon gyors, 0.5 másodperc
            100.0, # Extrém nagy skála
            startScale=10.0
        )
        
        # 4. Háttér Fehér -> Fekete váltása (Belül fekete a háttér)
        bg_to_black = LerpFunc(
            self.bg_color_lerp,
            duration=0.5,
            fromData=0.0,
            toData=1.0,
            extraArgs=[self.WHITE, self.BLACK]
        )
        
        # 5. Kamera Belépés: Áthaladás a központba (már a skála változás hatókörén belül)
        cam_enter = self.cam.posInterval(
            0.5,
            pos=LVector3(0, 0, 0), # Középre belépés
            startPos=LVector3(0, -10, 0)
        )
        
        # --- PHASE 3: Stabilization (Stabilizálás) ---
        
        # 6. Várakozás, hogy a belső tér látszódjon
        wait_inside = Wait(3.0)

        # --- Teljes Szekvencia ---
        transition_sequence = Sequence(
            # 1. Közeledés
            Parallel(scale_approach, cam_approach), 
            
            # 2. Belépés a kockába (Villanás)
            Parallel(scale_enter, cam_enter, bg_to_black), 
            
            # 3. Stabilizálás
            wait_inside,
            
            # 4. Újraindítás az elejéről (opcionális a demóhoz)
            # A hiba elkerülése érdekében a teleport_object hivatkozás eltávolítva
            self.cam.posInterval(0.01, pos=LVector3(0, -30, 0)), # Kamera vissza a kiinduló pozícióba
            Func(self.world_cube.setScale, 2.0), # Vissza a kezdeti mérethez
            Func(lambda: self.win.setClearColor(self.WHITE)), # Háttér vissza fehérre
            
            Wait(1.0), # Kis szünet az újraindítás előtt
            Func(self.start_transition) # Újraindítás
        )
        
        transition_sequence.start()

# Run the application
if __name__ == "__main__":
    app = EnteringCubeWorld()
    app.run()