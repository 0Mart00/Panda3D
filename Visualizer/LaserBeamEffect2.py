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
    Panda3D alkalmazás egy kék lézersugár és egy pulzáló fehér gyűrű effekt megjelenítésére.
    A lézersugár egyenesen vízszintesen mutat (pozitív Y irányba).
    A gyűrű utazik a sugár mentén, miközben tágul és elhalványul.
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
        
        # Lézersugár és gyűrű effekt létrehozása
        self.laser_length = 20.0
        self.create_laser_beam()
        self.create_laser_ring_effect()

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

    def create_laser_beam(self):
        """Létrehozza a kék lézersugár geometriáját (vékony quad), ami egyenesen vízszintesen mutat."""
        cm = CardMaker('laserBeam')
        # Lézer vastagsága: 0.05 egység mindkét irányban, hossza: self.laser_length
        cm.setFrame(-0.05, 0.05, 0, self.laser_length) 
        
        self.laser = render.attachNewNode(cm.generate())
        # A sugár Z=1 magasságban indul
        self.laser.setPos(0, 0, 1) 
        
        # Orientáció beállítása: A CardMaker a Y tengely mentén van, így 0 fokos HPR-rel vízszintesen előre mutat.
        self.laser.setHpr(0, 0, 0) # Vízszintes (pozitív Y) irány

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

    def create_laser_ring_effect(self):
        """Létrehozza a pulzáló, lapos fehér gyűrűt."""
        
        self.ring = self.create_ring_texture()
        self.ring.reparentTo(self.laser) 
        
        # A lézersugár a Y tengely mentén van a NodePath-ban (0-tól 20-ig terjed).
        # A gyűrű a sugár elején indul.
        RING_START_POSITION = 0.0
        self.ring.setPos(0, RING_START_POSITION, 0) 
        
        # Billboarding: a gyűrű Z tengelye (normálisa) mindig a kamera felé néz.
        # setBillboardAxis(0) a Z tengelyt használja a billboardinghoz.
        self.ring.setBillboardAxis(0) 

        # Fehér, additív keverés a maximális ragyogásért
        self.ring.setTransparency(TransparencyAttrib.M_alpha)
        self.ring.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.ring.setColorScale(VBase4(1.0, 1.0, 1.0, 1.0)) # Kezdeti fehér szín

        # Kezdeti skála beállítása
        self.base_scale = 0.5


    def animate_effect(self, task):
        """Animálja a gyűrű effektet (mozgás, tágulás és halványítás)."""
        dt = globalClock.getDt()
        self.ring_timer += dt

        # Ciklus beállításai
        cycle_duration = 1.5 # Másfél másodpercenként ismétlődik a lövés

        # A ciklus normalizálása 0 és 1 között
        t = (self.ring_timer % cycle_duration) / cycle_duration
        
        # --- 1. Pozíció/Mozgás (Utazás a sugár mentén) ---
        # A gyűrű Y=0-tól (a sugár eleje) Y=self.laser_length-ig (a sugár vége) mozog.
        ring_y_pos = t * self.laser_length
        self.ring.setY(ring_y_pos) # setPos(0, ring_y_pos, 0) a setY a csatolt NodePath-ban

        # --- 2. Tágulás és Halványítás ---
        
        # Skála: 0.5-től (t=0) 3.0-ig (t=1) terjed
        scale = self.base_scale + t * 2.5 
        
        # Alpha: 1.0-tól (t=0) 0.0-ig (t=1) halványul
        alpha = 1.0 - t 

        self.ring.setScale(scale, scale, 1)
        self.ring.setColorScale(VBase4(1.0, 1.0, 1.0, alpha)) 
        
        return Task.cont

# Alkalmazás futtatása
app = LaserEffectApp()
app.run()