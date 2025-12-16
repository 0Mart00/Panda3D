from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode,
    TransparencyAttrib
)
from direct.task import Task
from direct.interval.IntervalGlobal import Sequence, Parallel, LerpFunc, Func, Wait
import random
import itertools
import math

# Configuration for the window settings
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Teleport Effekt Demó")
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


class TeleportEffectDemo(ShowBase):
    """
    Simulates a teleport effect using a combination of fading and flash animations.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        self.setBackgroundColor(0.1, 0.1, 0.1, 1) # Sötétszürke háttér
        self.cam.setPos(0, -30, 10)
        self.cam.lookAt(0, 0, 0)
        
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.8, 0.8, 0.8, 1)) 
        self.render.setLight(self.render.attachNewNode(alight))

        # --- 2. Teleportable Object (Teleportálható Objektum) ---
        self.teleport_object = create_cube_mesh()
        self.teleport_object.reparentTo(self.render)
        self.teleport_object.setScale(1.5)
        self.teleport_object.setPos(5, 5, 5) # Kezdeti pozíció
        self.teleport_object.setColor(VBase4(0.9, 0.1, 0.1, 1.0)) # Piros szín
        self.teleport_object.setTransparency(TransparencyAttrib.MAlpha)
        
        # Rotációs feladat hozzáadása a jobb láthatóságért
        self.taskMgr.add(self.rotate_object, "RotateObjectTask")
        
        # --- 3. Teleport Task (Teleport Feladat) ---
        # Teleportáljon minden 3.5 másodpercben
        self.taskMgr.doMethodLater(0.5, self.start_teleport, "StartTeleportTask")

    def rotate_object(self, task):
        """Forgatja a teleportálható kockát."""
        self.teleport_object.setH(self.teleport_object.getH() + 0.5)
        return Task.cont

    def spawn_flash_effect(self, position, color, duration):
        """Létrehoz egy gyorsan növekvő és elhalványuló villanást."""
        flash = create_cube_mesh()
        flash.reparentTo(self.render)
        flash.setPos(position)
        flash.setScale(0.1)
        flash.setColorScale(color)
        flash.setTransparency(TransparencyAttrib.MAlpha)
        
        # Animációs szekvencia: Növekedés és halványulás
        flash_sequence = Sequence(
            Parallel(
                flash.scaleInterval(duration, 3.0, startScale=0.1),
                flash.colorScaleInterval(duration, VBase4(color.x, color.y, color.z, 0.0), startColorScale=color)
            ),
            Func(flash.removeNode)
        )
        flash_sequence.start()

    def start_teleport(self, task):
        """Elindítja a teleport animációs szekvenciát."""
        
        current_pos = self.teleport_object.getPos()
        
        # Véletlenszerű célpozíció kiválasztása
        new_pos = LVector3(
            random.uniform(-10, 10),
            random.uniform(-10, 10),
            random.uniform(0, 10)
        )
        
        # Ha a cél túl közel van a forráshoz, válasszunk újat
        while (new_pos - current_pos).length() < 10:
            new_pos = LVector3(random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(0, 10))

        # --- A Teleport Szekvencia Létrehozása ---
        
        # 1. Elhalványulás az indulás előtt
        fade_out = self.teleport_object.colorScaleInterval(0.3, VBase4(1.0, 1.0, 1.0, 0.0))
        
        # 2. Forrás Villám (Sárga)
        source_flash_func = Func(self.spawn_flash_effect, current_pos, VBase4(1.0, 1.0, 0.2, 1.0), 0.4)
        
        # 3. Pozícióváltás (azonnali)
        teleport_func = Func(self.teleport_object.setPos, new_pos)
        
        # 4. Cél Villám (Kék)
        target_flash_func = Func(self.spawn_flash_effect, new_pos, VBase4(0.2, 0.5, 1.0, 1.0), 0.4)
        
        # 5. Visszaállás
        fade_in = self.teleport_object.colorScaleInterval(0.3, VBase4(1.0, 1.0, 1.0, 1.0))

        # Teljes szekvencia összeállítása:
        teleport_sequence = Sequence(
            fade_out,               # Objektum eltűnik
            source_flash_func,      # Sárga villanás az indulásnál
            Wait(0.1),              # Kis szünet
            teleport_func,          # Azonnali helyzetváltoztatás
            target_flash_func,      # Kék villanás az érkezésnél
            Wait(0.1),              # Kis szünet
            fade_in                 # Objektum megjelenik
        )
        
        teleport_sequence.start()

        # Időzítő a következő teleportáláshoz
        task.delayTime = 3.5
        return Task.again

# Run the application
if __name__ == "__main__":
    app = TeleportEffectDemo()
    app.run()