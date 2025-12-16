# -*- coding: utf-8 -*-
# Panda3D Kék Lézersugár és Fehér Gyűrű Effekt

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    CardMaker, VBase4, TransparencyAttrib, ColorBlendAttrib,
    TextureStage, NodePath, LineSegs, LVecBase3, LVector3
)
from direct.task import Task
import math

class LaserEffectApp(ShowBase):
    """
    Panda3D alkalmazás egy kék lézersugár és egy pulzáló fehér gyűrű effekt megjelenítésére.
    A gyűrű billbordozozott, így mindig a kamera felé néz.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # A kamera helyzetének beállítása (így látjuk a lézersugarat)
        self.camera.setPos(0, -10, 3)
        self.camera.lookAt(0, 0, 0)
        self.setBackgroundColor(0.1, 0.1, 0.2) # Sötét háttér a jobb kontraszt érdekében

        # Fények kikapcsolása a sugár és a gyűrű világító hatásához (emisszív színek)
        render.setLightOff()

        # Alap talaj/síkság hozzáadása (opcionális, csak a környezet miatt)
        self.create_ground()
        
        # Lézersugár és gyűrű effekt létrehozása
        self.create_laser_beam()
        self.create_laser_ring_effect()

        # Animációs feladat indítása
        self.ring_timer = 0.0
        self.taskMgr.add(self.animate_effect, 'AnimateLaserEffectTask')
        
        # A lézersugár (a közepén a gyűrűvel) a (0, 0, 1) pontból indul és a pozitív Y irányba mutat
        self.laser.setHpr(0, 0, 0) # Alapértelmezett Y-tengely irány

    def create_ground(self):
        """Létrehoz egy egyszerű talaj síkot."""
        cm = CardMaker('ground')
        cm.setFrame(-10, 10, -10, 10)
        ground = render.attachNewNode(cm.generate())
        ground.setHpr(0, -90, 0) # Lefelé fordítás (XZ síkba)
        ground.setPos(0, 0, 0)
        ground.setColor(VBase4(0.2, 0.2, 0.2, 1))

    def create_laser_beam(self):
        """Létrehozza a kék lézersugár geometriáját (vékony quad)."""
        cm = CardMaker('laserBeam')
        # Lézer vastagsága: 0.05 egység mindkét irányban, hossza: 20 egység
        cm.setFrame(-0.05, 0.05, 0, 20) 
        
        self.laser = render.attachNewNode(cm.generate())
        # A sugár Z=1 magasságban van
        self.laser.setPos(0, 0, 1) 

        # Kék, világító hatás (additív keverés a ragyogásért)
        self.laser.setTransparency(TransparencyAttrib.M_alpha)
        self.laser.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        # Ragyogó kék szín: (R, G, B, A)
        self.laser.setColorScale(VBase4(0.2, 0.5, 1.0, 1.0)) 
        
        # A sugár másik oldala is látszódjon
        self.laser.setTwoSided(True)

    def create_ring_texture(self):
        """Procedurálisan létrehozza a gyűrűhöz szükséges textúrát."""
        # A textúra helyettesítésére egy egyszerű, átlátszó, kör alakú geometriát használunk
        # a LineSegs segítségével, hogy a középső üresség (lyuk) is látszódjon.
        
        ls = LineSegs()
        ls.setThickness(5.0) # A gyűrű vastagsága
        
        # Gyűrű rajzolása
        segments = 64
        radius = 1.0
        
        ls.setColor(VBase4(1.0, 1.0, 1.0, 1.0)) # Fehér szín
        
        for i in range(segments + 1):
            angle = (float(i) / segments) * 2.0 * math.pi
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            if i == 0:
                ls.moveTo(x, 0, y) # A gyűrű az XZ síkban van a billboarding miatt
            else:
                ls.drawTo(x, 0, y)

        ring_node = ls.create()
        return render.attachNewNode(ring_node)

    def create_laser_ring_effect(self):
        """Létrehozza a pulzáló, lapos fehér gyűrűt."""
        
        # A gyűrűt procedurális geometriával hozzuk létre
        self.ring = self.create_ring_texture()
        
        # A lézer közepéhez csatoljuk
        # A sugár 20 egység hosszú, így a fele 10 egységnél van
        self.ring.reparentTo(self.laser) 
        # A gyűrű pozíciója a lézersugáron (pl. a közepén)
        self.ring.setPos(0, 10, 0) 
        self.ring.setScale(0.5)
        
        # Billboarding: a gyűrű (ami az XZ síkban van) Z tengelye mindig a kamera felé néz
        # A Panda3D-ben a setBillboardAxis(0) azt jelenti, hogy a Z tengely (a gyűrű normálisa) néz a kamerába
        self.ring.setBillboardAxis(0) 

        # Fehér, additív keverés a maximális ragyogásért
        self.ring.setTransparency(TransparencyAttrib.M_alpha)
        self.ring.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.ring.setColorScale(VBase4(1.0, 1.0, 1.0, 1.0)) # Kezdeti fehér szín

        # Kezdeti skála beállítása
        self.base_scale = 0.5
        self.ring.setScale(self.base_scale)


    def animate_effect(self, task):
        """Animálja a gyűrű effektet (skálázás és halványítás)."""
        dt = globalClock.getDt()
        self.ring_timer += dt

        # A pulzálás frekvenciája
        pulsing_speed = 1.5

        # 1. Skálázás: 0.5-től indul, max 2.5-ig növekszik
        scale_factor = 1.0 + (math.sin(self.ring_timer * pulsing_speed) + 1.0) * 0.7
        current_scale = self.base_scale * scale_factor
        self.ring.setScale(current_scale, current_scale, 1)

        # 2. Átlátszóság: minél nagyobb a gyűrű, annál átlátszóbb
        # A gyűrű "szétterjed", és elhalványul.
        # Itt egy egyszerű halványodást használunk a szinusz hullám alapján,
        # hogy szimuláljuk az energia szétoszlását.
        alpha_base = 1.0 
        alpha_falloff = (math.sin(self.ring_timer * pulsing_speed * 0.5) * 0.5) + 0.5 # 0.5 és 1.0 között pulzál
        
        # Az alpha folyamatosan csökkenő animációhoz:
        # Ha a gyűrű effektnek ciklusosan meg kell jelennie és eltűnnie:
        
        cycle_duration = 1.5 # Másodpercenként ismétlődik
        
        # A ciklus normalizálása 0 és 1 között
        t = (self.ring_timer % cycle_duration) / cycle_duration

        # Skála: 0.5-től (t=0) 3.0-ig (t=1) terjed
        scale = self.base_scale + t * 2.5 
        
        # Alpha: 1.0-tól (t=0) 0.0-ig (t=1) halványul
        alpha = 1.0 - t 

        self.ring.setScale(scale, scale, 1)
        self.ring.setColorScale(VBase4(1.0, 1.0, 1.0, alpha)) 
        
        # Mozgassuk a kamerát kicsit, hogy lássuk a billboarding hatását
        angle = self.ring_timer * 10
        cam_x = math.cos(math.radians(angle)) * 10
        cam_y = math.sin(math.radians(angle)) * 10
        self.camera.setPos(cam_x, cam_y, 3)
        self.camera.lookAt(0, 0, 1)

        return Task.cont

# Alkalmazás futtatása
app = LaserEffectApp()
app.run()