from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    GeomVertexRewriter,
    GeomNode,
    Vec3,
    Point3,
    CollisionTraverser,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionRay,
    CollisionSphere,
    BitMask32,
    NodePath,
    TextNode
)
from direct.task import Task
import random
import math

# Beállítások
ASZTEROIDA_SZAM = 15
SUGAR_MIN = 2.0
SUGAR_MAX = 4.0
TERULET_MERET = 40.0
TORZITAS_MATEK = 1.5  # Mennyire legyen szabálytalan a gömb

class AszteroidaJatek(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # 1. Alapvető beállítások (Kamera, Fények, Cím)
        self.disableMouse()  # Kikapcsoljuk az alapértelmezett kamera irányítást
        self.camera.setPos(0, -100, 20)
        self.camera.lookAt(0, 0, 0)
        self.title = self.add_title("Panda3D: Procedurális Aszteroida Lövészet (Bal klikk: Lövés)")

        # Ütközésvizsgáló rendszer inicializálása
        self.cTrav = CollisionTraverser()
        self.collision_queue = CollisionHandlerQueue()

        # A sugár (lézer) létrehozása a kamerához
        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(BitMask32.bit(1)) # Csak az 1-es maszkkal ütközik
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.cTrav.addCollider(self.picker_np, self.collision_queue)

        # Aszteroidák és Loot-ok tárolója
        self.asteroids = []
        self.loots = []

        # 2. Aszteroidák generálása
        self.generate_asteroids()

        # 3. Eseménykezelők (Input)
        self.accept("mouse1", self.shoot)
        self.accept("escape", self.userExit)

        # 4. Update task a loot forgatásához
        self.taskMgr.add(self.update_loots, "UpdateLoots")

    def add_title(self, text):
        title = TextNode('title')
        title.setText(text)
        title.setTextColor(1, 1, 1, 1)
        titleNode = self.aspect2d.attachNewNode(title)
        titleNode.setScale(0.05)
        titleNode.setPos(-0.9, 0, 0.9)
        return titleNode

    def generate_asteroids(self):
        """Létrehoz véletlenszerű aszteroidákat ütközésmentes pozíciókban."""
        print(f"Generálás indítása: {ASZTEROIDA_SZAM} db aszteroida...")
        
        attempts = 0
        while len(self.asteroids) < ASZTEROIDA_SZAM and attempts < 1000:
            attempts += 1
            
            # Véletlenszerű pozíció
            x = random.uniform(-TERULET_MERET, TERULET_MERET)
            y = random.uniform(-TERULET_MERET, TERULET_MERET)
            z = random.uniform(-TERULET_MERET/2, TERULET_MERET/2)
            pos = Point3(x, y, z)
            
            # Véletlenszerű méret
            scale = random.uniform(SUGAR_MIN, SUGAR_MAX)
            
            # Ellenőrzés: Ne legyen túl közel a többiekhez
            if not self.check_overlap(pos, scale):
                self.create_procedural_asteroid(pos, scale)

    def check_overlap(self, pos, scale):
        """Megnézi, hogy az adott pozíció ütközik-e már létező aszteroidával."""
        for ast_np, ast_scale in self.asteroids:
            dist = (ast_np.getPos() - pos).length()
            min_dist = ast_scale + scale + 2.0 # +2 buffer
            if dist < min_dist:
                return True
        return False

    def create_procedural_asteroid(self, pos, scale):
        """Betölt egy gömböt, deformálja a vertexeit és collision node-ot ad hozzá."""
        
        # Alap modell betöltése (a beépített 'smiley' jó, mert sok vertexe van)
        # De kikapcsoljuk a textúrát, hogy jobban látszódjon a geometria.
        model = self.loader.loadModel("models/misc/smiley")
        model.setTextureOff(1)
        
        # Procedurális deformáció (vertex manipulation)
        self.modify_geometry(model)

        # Node beállítása a jelenetben
        model.reparentTo(self.render)
        model.setPos(pos)
        model.setScale(scale)
        model.setColor(0.4 + random.random()*0.2, 0.3 + random.random()*0.2, 0.3, 1.0) # Barnás/Szürkés szín

        # Ütközésvizsgálat hozzáadása (Collision Node)
        # Egyszerűség kedvéért egy CollisionSphere-t használunk, ami követi a méretet.
        c_sphere = CollisionSphere(0, 0, 0, 1.1) # 1.1 kicsit nagyobb mint a sugár a deformáció miatt
        c_node = CollisionNode('asteroid')
        c_node.addSolid(c_sphere)
        c_node.setIntoCollideMask(BitMask32.bit(1)) # Ezt találja el a sugár
        c_node.setTag('asteroid_id', str(len(self.asteroids))) # Azonosító
        
        c_np = model.attachNewNode(c_node)
        # c_np.show() # Debug: ha látni akarod az ütköző gömböt

        # Hozzáadjuk a listához
        self.asteroids.append((model, scale))

    def modify_geometry(self, model_np):
        """
        Vertex szintű manipuláció.
        Végigmegyünk a modell csúcspontjain, és elmozdítjuk őket
        a normálvektoruk irányába véletlenszerű mértékben.
        """
        geom_node = model_np.find("**/+GeomNode").node()
        
        # Végigmegyünk minden Geom-on a node-ban
        for i in range(geom_node.getNumGeoms()):
            geom = geom_node.modifyGeom(i)
            vdata = geom.modifyVertexData()
            
            vertex = GeomVertexRewriter(vdata, 'vertex')
            normal = GeomVertexRewriter(vdata, 'normal')
            
            while not vertex.isAtEnd():
                v = vertex.getData3f()
                n = normal.getData3f()
                
                # Zaj generálása: egyszerű random offset
                # (Komplexebb megoldáshoz Perlin noise ajánlott, de ez gyors és egyszerű)
                noise = (random.random() * 2.0 - 1.0) * TORZITAS_MATEK * 0.2
                
                # Új pozíció: régi + normál * zaj
                new_v = v + n * noise
                
                vertex.setData3f(new_v)
                
    def shoot(self):
        """A játékos lő (kattint). Sugárvetés a 3D térbe."""
        if not self.mouseWatcherNode.hasMouse():
            return

        # 1. Egér pozíció lekérése
        mpos = self.mouseWatcherNode.getMouse()
        
        # 2. Sugár beállítása a kamerából az egér irányába
        self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        
        # 3. Ütközésvizsgálat futtatása
        self.cTrav.traverse(self.render)
        
        # 4. Találatok ellenőrzése
        if self.collision_queue.getNumEntries() > 0:
            self.collision_queue.sortEntries() # A legközelebbi találat az első
            entry = self.collision_queue.getEntry(0)
            hit_node = entry.getIntoNode()
            
            if hit_node.getName() == 'asteroid':
                hit_np = entry.getIntoNodePath().getParent() # Az aszteroida modellje
                self.destroy_asteroid(hit_np)

    def destroy_asteroid(self, asteroid_np):
        """Aszteroida megsemmisítése és loot spawnolása."""
        pos = asteroid_np.getPos()
        
        # 1. Aszteroida eltávolítása a listából és a renderből
        # (Egyszerűsített lista kezelés: nem töröljük a listából a referenciát a loop miatt,
        # csak elrejtjük/töröljük a NodePath-et a scene graph-ból)
        asteroid_np.removeNode()
        print("Találat! Aszteroida megsemmisült.")
        
        # 2. Loot spawnolása
        self.spawn_drop(pos)

    def spawn_drop(self, pos):
        """Létrehoz egy 'drop' objektumot (pl. egy kockát) a törés helyén."""
        # Kocka betöltése
        drop = self.loader.loadModel("models/box")
        drop.reparentTo(self.render)
        drop.setPos(pos)
        drop.setScale(1.0) # Kisebb mint az aszteroida
        drop.setColor(0, 1, 0, 1) # Zöld színű loot
        
        # Hozzáadjuk a listához, hogy később tudjuk forgatni
        self.loots.append(drop)

    def update_loots(self, task):
        """Forgatja a leesett tárgyakat."""
        dt = globalClock.getDt()
        for loot in self.loots:
            if not loot.isEmpty():
                loot.setH(loot.getH() + 60 * dt) # Forgás Y tengely körül
                loot.setP(loot.getP() + 30 * dt)
        return Task.cont

# Alkalmazás indítása
if __name__ == "__main__":
    app = AszteroidaJatek()
    app.run()