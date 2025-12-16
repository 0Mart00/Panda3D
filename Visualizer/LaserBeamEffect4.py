# -*- coding: utf-8 -*-
# Panda3D Kék Lézersugár és Fehér Gyűrű Effekt

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    CardMaker, VBase4, TransparencyAttrib, ColorBlendAttrib,
    NodePath, LineSegs, NodePathCollection
)
from direct.task import Task
import math
import random # Szükség van rá a villám véletlenszerűségéhez

class LaserEffectApp(ShowBase):
    """
    Panda3D alkalmazás egy láncvillám (Chain Lightning) effekt megjelenítésére.
    A villám egyetlen, kék, villódzó, cikk-cakk vonal, amelyen három
    egymást követő, pulzáló fehér gyűrű effekt fut végig.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # A kamera helyzetének beállítása (vízszintes sugár megtekintésére)
        self.camera.setPos(0, -15, 5)
        self.camera.lookAt(0, 10, 1) # A sugár közepére nézünk
        self.setBackgroundColor(0.1, 0.1, 0.2) # Sötét háttér a jobb kontraszt érdekében
        self.disableMouse() # Kikapcsoljuk az egér vezérlést

        # Fények kikapcsolása a sugár és a gyűrű világító hatásához (emisszív színek)
        render.setLightOff()

        # Alap talaj/síkság hozzáadása
        self.create_ground()
        
        # Lézersugár (villám) hosszának beállítása
        self.laser_length = 20.0
        self.cycle_duration = 1.5 # Egy gyűrű effekt időtartama

        # Sugár létrehozása
        self.laser_np = None # NodePath a LineSegs számára
        self.rings = []
        self.create_laser_beams()
        self.create_laser_ring_effects()

        # Animációs feladat indítása
        self.ring_timer = 0.0
        self.taskMgr.add(self.animate_effect, 'AnimateLaserEffectTask')
        
    # --- HELPER FUNKCIÓK ---

    def create_ground(self):
        """Létrehoz egy egyszerű talaj síkot."""
        cm = CardMaker('ground')
        cm.setFrame(-10, 10, -10, 10)
        ground = render.attachNewNode(cm.generate())
        ground.setHpr(0, -90, 0) # XZ síkba fordítás (földre)
        ground.setPos(0, 0, 0) # A Z=0 a talaj
        ground.setColor(VBase4(0.2, 0.2, 0.2, 1))

    def generate_lightning_geom(self):
        """Procedurálisan létrehozza a villám cikk-cakk geometriáját LineSegs-szel."""
        
        ls = LineSegs()
        ls.setThickness(3.0) # Villám vastagsága
        
        # Ragyogó kék szín: (R, G, B, A)
        ls.setColor(VBase4(0.2, 0.5, 1.0, 1.0)) 
        
        segments = 15 # Hány szegmensből áll a villám
        amplitude = 0.5 # A cikk-cakk szélessége
        
        # Kezdőpont
        ls.moveTo(0, 0, 0)

        # Cikk-cakk pontok létrehozása
        for i in range(1, segments + 1):
            t = i / segments
            y = t * self.laser_length
            # Véletlenszerű elmozdulás az X és Z tengelyen (a villám szélessége)
            x_offset = (random.random() * 2 - 1) * amplitude 
            z_offset = (random.random() * 2 - 1) * amplitude
            
            # Az XZ sík elmozdulásához adjuk a véletlenszerűséget
            # Mivel a villám a Y irányban halad, az X és Z a keresztmetszeti tengely
            ls.drawTo(x_offset, y, z_offset)
        
        return ls.create()

    def create_laser_beams(self):
        """Létrehozza az EGYETLEN láncvillámot."""
        
        # A forrás (emitter) NodePath, Z=1 magasságban
        self.emitter = render.attachNewNode("LaserEmitter")
        self.emitter.setPos(0, 0, 1)
        
        # Létrehozza a kezdeti villámgeometriát
        geom = self.generate_lightning_geom()
        self.laser_np = self.emitter.attachNewNode(geom)
        
        # Világító hatás (additív keverés)
        self.laser_np.setTransparency(TransparencyAttrib.M_alpha)
        self.laser_np.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.laser_np.setTwoSided(True)

    def create_ring_texture(self):
        """Procedurálisan létrehozza a gyűrűhöz szükséges textúrát (körvonal)."""
        ls = LineSegs()
        ls.setThickness(5.0) 
        
        segments = 64
        radius = 1.0
        
        ls.setColor(VBase4(1.0, 1.0, 1.0, 1.0)) # Fehér szín
        
        for i in range(segments + 1):
            angle = (float(i) / segments) * 2.0 * math.pi
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            # A gyűrű az XY síkban jön létre
            if i == 0:
                ls.moveTo(x, y, 0) 
            else:
                ls.drawTo(x, y, 0)

        ring_node = ls.create()
        # Átállítjuk a render-ről a self.emitter-re
        return self.emitter.attachNewNode(ring_node) 

    def create_laser_ring_effects(self):
        """Létrehozza a HÁROM gyűrű effektet és csatolja a fő sugárhoz."""
        
        # A gyűrű geometria
        ring_model = self.create_ring_texture()
        # A gyűrűk most már a fő emitterhez csatoltak, nem a dinamikusan mozgó laser_np-hez.
        ring_model.setBillboardAxis(0) 
        
        # Fehér, additív keverés
        ring_model.setTransparency(TransparencyAttrib.M_alpha)
        ring_model.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        ring_model.setColorScale(VBase4(1.0, 1.0, 1.0, 1.0)) 
        
        self.base_scale = 0.5
        
        num_rings = 3
        
        for i in range(num_rings):
            # Klónozzuk a gyűrűt minden effekthez, és mindegyiket a FŐ EMITTERHEZ csatoljuk
            ring_instance = self.emitter.attachNewNode(f"LaserRing_{i}")
            ring_model.instanceTo(ring_instance) # Használjuk a korábban létrehozott modellt
            
            # Kezdő pozíció a sugár elején
            ring_instance.setPos(0, 0, 0) 
            ring_instance.setScale(self.base_scale)
            
            # Tároljuk a gyűrűt a hozzá tartozó fázis eltolással
            phase_offset = i * (self.cycle_duration / num_rings)
            self.rings.append({'node': ring_instance, 'offset': phase_offset})

    def animate_effect(self, task):
        """Animálja a villám geometriáját és a gyűrű effekteket."""
        dt = globalClock.getDt()
        self.ring_timer += dt

        # --- 1. Villám Geometria Frissítése (Láncvillám effekt) ---
        # Minden frame-ben újra kell rajzolni a villámot, hogy "villódzó" hatása legyen.
        # El kell távolítani a régi NodePath-et és újat csatolni
        self.laser_np.removeNode()
        new_geom = self.generate_lightning_geom()
        self.laser_np = self.emitter.attachNewNode(new_geom)
        
        # Fényhatások visszaállítása az új NodePath-en
        self.laser_np.setTransparency(TransparencyAttrib.M_alpha)
        self.laser_np.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.laser_np.setTwoSided(True)


        # --- 2. Gyűrű Effektek Animálása ---
        
        # Minden gyűrű külön fázisban van animálva
        for ring_data in self.rings:
            ring = ring_data['node']
            offset = ring_data['offset']
            
            # Effektív idő kiszámítása az eltolással
            effective_time = self.ring_timer + offset
            
            # Ciklus normalizálása 0 és 1 között
            t = (effective_time % self.cycle_duration) / self.cycle_duration
            
            # --- Mozgás (Utazás a sugár mentén) ---
            # A gyűrű Y=0-tól (a sugár eleje) Y=self.laser_length-ig (a sugár vége) mozog.
            ring_y_pos = t * self.laser_length
            # A gyűrű az emitterhez van csatolva, így a pozíciója az Y tengely mentén mozog.
            # Mivel a villám pontjai a (0, 0) körül mozognak, a gyűrű középen marad, de körülveszi a villámot.
            ring.setY(ring_y_pos)

            # --- Tágulás és Halványítás ---
            
            # Skála: 0.5-től (t=0) 3.0-ig (t=1) terjed
            scale = self.base_scale + t * 2.5 
            
            # Alpha: 1.0-tól (t=0) 0.0-ig (t=1) halványul
            alpha = 1.0 - t 
            
            ring.setScale(scale, scale, 1)
            ring.setColorScale(VBase4(1.0, 1.0, 1.0, alpha)) 
        
        return Task.cont

# Alkalmazás futtatása
app = LaserEffectApp()
app.run()