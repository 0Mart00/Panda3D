# -*- coding: utf-8 -*-
# Panda3D Kék Lézersugár és Fehér Gyűrű Effekt

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    CardMaker, VBase4, TransparencyAttrib, ColorBlendAttrib,
    NodePath, LineSegs
)
from direct.task import Task
import math

class LaserEffectApp(ShowBase):
    """
    Panda3D alkalmazás egyetlen kék lézersugár és három egymást követő,
    pulzáló fehér gyűrű effekt megjelenítésére.
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
        
        # Lézersugár hosszának beállítása
        self.laser_length = 20.0
        self.cycle_duration = 1.5 # Egy gyűrű effekt időtartama

        # Sugár létrehozása
        self.laser = None
        self.rings = []
        self.create_laser_beams()
        self.create_laser_ring_effects()

        # Animációs feladat indítása
        self.ring_timer = 0.0
        self.taskMgr.add(self.animate_effect, 'AnimateLaserEffectTask')
        

    def create_ground(self):
        """Létrehoz egy egyszerű talaj síkot."""
        cm = CardMaker('ground')
        cm.setFrame(-10, 10, -10, 10)
        ground = render.attachNewNode(cm.generate())
        ground.setHpr(0, -90, 0) # XZ síkba fordítás (földre)
        ground.setPos(0, 0, 0) # A Z=0 a talaj
        ground.setColor(VBase4(0.2, 0.2, 0.2, 1))

    def create_laser_beams(self):
        """Létrehozza az EGYETLEN főlézersugarat."""
        
        # A forrás (emitter) NodePath, Z=1 magasságban
        self.emitter = render.attachNewNode("LaserEmitter")
        self.emitter.setPos(0, 0, 1)
        
        cm = CardMaker('laserBeam')
        # Lézer vastagsága: 0.05 egység mindkét irányban, hossza: self.laser_length
        cm.setFrame(-0.05, 0.05, 0, self.laser_length) 
        
        self.laser = self.emitter.attachNewNode(cm.generate())
        
        # Orientáció beállítása (vízszintes, Y irány)
        self.laser.setHpr(0, 0, 0) 

        # Kék, világító hatás (additív keverés a ragyogásért)
        self.laser.setTransparency(TransparencyAttrib.M_alpha)
        self.laser.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        # Ragyogó kék szín: (R, G, B, A)
        self.laser.setColorScale(VBase4(0.2, 0.5, 1.0, 1.0)) 
        
        # A sugár másik oldala is látszódjon
        self.laser.setTwoSided(True)


    def create_ring_texture(self):
        """Procedurálisan létrehozza a gyűrűhöz szükséges textúrát (körvonal)."""
        ls = LineSegs()
        ls.setThickness(5.0) # A gyűrű vastagsága
        
        # Gyűrű rajzolása (XY síkban)
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
        return render.attachNewNode(ring_node)

    def create_laser_ring_effects(self):
        """Létrehozza a HÁROM gyűrű effektet és csatolja a fő sugárhoz."""
        
        # A gyűrű geometria
        ring_model = self.create_ring_texture()
        ring_model.setBillboardAxis(0) 
        
        # Fehér, additív keverés a maximális ragyogásért
        ring_model.setTransparency(TransparencyAttrib.M_alpha)
        ring_model.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        ring_model.setColorScale(VBase4(1.0, 1.0, 1.0, 1.0)) # Kezdeti fehér szín
        
        self.base_scale = 0.5
        
        # Fáziseltolás a három gyűrű indításához
        num_rings = 3
        
        for i in range(num_rings):
            # Klónozzuk a gyűrűt minden effekthez, és mindegyiket a fő lézerhez csatoljuk
            ring_instance = self.laser.attachNewNode(f"LaserRing_{i}")
            ring_model.instanceTo(ring_instance)
            
            # Kezdő pozíció a sugár elején
            ring_instance.setPos(0, 0, 0) 
            ring_instance.setScale(self.base_scale)
            
            # Tároljuk a gyűrűt a hozzá tartozó fázis eltolással
            # Phase = 0, 0.5, 1.0. Ez biztosítja, hogy a gyűrűk ne egyszerre induljanak, hanem eltolva.
            phase_offset = i * (self.cycle_duration / num_rings)
            self.rings.append({'node': ring_instance, 'offset': phase_offset})


    def animate_effect(self, task):
        """Animálja a gyűrű effekteket (mozgás, tágulás és halványítás) fáziseltolással."""
        dt = globalClock.getDt()
        self.ring_timer += dt

        # Minden gyűrű külön fázisban van animálva
        for ring_data in self.rings:
            ring = ring_data['node']
            offset = ring_data['offset']
            
            # Effektív idő kiszámítása az eltolással
            effective_time = self.ring_timer + offset
            
            # Ciklus normalizálása 0 és 1 között (a többszörös ciklusra is figyelünk)
            t = (effective_time % self.cycle_duration) / self.cycle_duration
            
            # --- 1. Pozíció/Mozgás (Utazás a sugár mentén) ---
            # A gyűrű Y=0-tól (a sugár eleje) Y=self.laser_length-ig (a sugár vége) mozog.
            ring_y_pos = t * self.laser_length
            ring.setY(ring_y_pos)

            # --- 2. Tágulás és Halványítás ---
            
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