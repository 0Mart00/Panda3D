import sys
import random
from direct.showbase.ShowBase import ShowBase
from direct.interval.IntervalGlobal import Sequence, Parallel, LerpScaleInterval, LerpColorScaleInterval, Func, Wait
from panda3d.core import Point3, Vec3, NodePath

class SpaceExplosion(ShowBase):
    def __init__(self):
        super().__init__()

        # 1. Alapbeállítások: Űr háttér (Fekete)
        self.setBackgroundColor(0, 0, 0, 1)
        
        # Kamera pozicionálása, hogy rálássunk a robbanásra
        self.camera.setPos(0, -60, 20)
        self.camera.lookAt(0, 0, 0)

        # Információs szöveg
        print("--- ŰRBÉLI ROBBANÁS DEMO ---")
        print("Nyomd meg az 'E' betűt a robbanáshoz!")
        
        # Billentyű hozzárendelés
        self.accept('e', self.trigger_explosion)
        self.accept('escape', sys.exit)

        # Első robbanás automatikus indítása kis késleltetéssel
        self.taskMgr.doMethodLater(2.0, lambda task: self.trigger_explosion(), 'auto_explode')

    def create_debris(self, position):
        """Létrehoz apró törmelékeket, amelyek kirepülnek."""
        debris_root = self.render.attachNewNode("debris_root")
        debris_root.setPos(position)

        expl_parallel = Parallel()

        # 30 darab törmelék generálása
        for i in range(30):
            # Beépített 'box' modell használata
            fragment = self.loader.loadModel("box")
            fragment.reparentTo(debris_root)
            
            # Véletlenszerű méret és szín (narancs/sárga/szürke)
            scale = random.uniform(0.1, 0.4)
            fragment.setScale(scale)
            if random.random() > 0.5:
                fragment.setColorScale(1, 0.5, 0, 1) # Narancs
            else:
                fragment.setColorScale(0.3, 0.3, 0.3, 1) # Szürke

            # Véletlenszerű irányvektor kiszámítása
            dir_x = random.uniform(-1, 1)
            dir_y = random.uniform(-1, 1)
            dir_z = random.uniform(-1, 1)
            target_pos = Point3(dir_x, dir_y, dir_z) * random.uniform(10, 25)

            # A mozgás animációja (repülés + pörgés + eltűnés)
            fragment_anim = Sequence(
                Parallel(
                    fragment.posInterval(1.5, target_pos, blendType='easeOut'),
                    fragment.hprInterval(1.5, Vec3(360, 360, 360)), # Pörgés
                    fragment.colorScaleInterval(1.5, (0, 0, 0, 0)) # Elhalványulás
                ),
                Func(fragment.removeNode) # Törlés a memóriából
            )
            expl_parallel.append(fragment_anim)
        
        # A debris_root csomópontot is töröljük, ha minden kész
        final_sequence = Sequence(expl_parallel, Func(debris_root.removeNode))
        final_sequence.start()

    def create_shockwave(self, position):
        """Egy táguló gyűrű (lökéshullám)."""
        # Mivel nincs gyűrű modellünk, egy laposra nyomott gömböt használunk
        wave = self.loader.loadModel("smiley") # Beépített gömb
        wave.reparentTo(self.render)
        wave.setPos(position)
        wave.setTransparency(True)
        wave.setColor(0.5, 0.8, 1, 1) # Kékes lökéshullám
        wave.setP(-90) # Fektetjük

        # Animáció: Kicsiből nagyra nő + elhalványul
        Sequence(
            Parallel(
                LerpScaleInterval(wave, 0.5, 15.0, startScale=0.1), # Növekedés
                LerpColorScaleInterval(wave, 0.5, (0, 0, 0, 0)) # Átlátszóság
            ),
            Func(wave.removeNode)
        ).start()

    def create_fireball(self, position):
        """A központi tűzgömb."""
        fireball = self.loader.loadModel("smiley")
        fireball.reparentTo(self.render)
        fireball.setPos(position)
        fireball.setTransparency(True)
        
        # Kezdetben nagyon fényes sárga/fehér
        fireball.setColorScale(1, 0.9, 0.6, 1) 
        fireball.setTextureOff(1) # Kikapcsoljuk a smiley arc textúrát, hogy sima gömb legyen

        # Animáció: Gyors tágulás, színváltás vörösre, majd eltűnés
        Sequence(
            Parallel(
                LerpScaleInterval(fireball, 0.4, 8.0, startScale=0.1, blendType='easeOut'),
                Sequence(
                    Wait(0.1),
                    LerpColorScaleInterval(fireball, 0.3, (1, 0.2, 0, 0.5)) # Vörösödés
                )
            ),
            LerpColorScaleInterval(fireball, 0.2, (0, 0, 0, 0)), # Eltűnés
            Func(fireball.removeNode)
        ).start()

    def trigger_explosion(self):
        """Összefogja az effekteket."""
        center_pos = Point3(0, 0, 0)
        
        # A három hatás elindítása
        self.create_fireball(center_pos)
        self.create_shockwave(center_pos)
        self.create_debris(center_pos)
        
        print("Bumm!")

# Futtatás
app = SpaceExplosion()
app.run()