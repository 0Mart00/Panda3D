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
ASZTEROIDA_SZAM = 10  # Kevesebb, de nagyobb aszteroida jobban mutat
SUGAR_MIN = 3.0
SUGAR_MAX = 5.0
TERULET_MERET = 40.0
TORZITAS_MATEK = 1.5  # Mennyire legyen szabálytalan a gömb

class AszteroidaJatek(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # 1. Alapvető beállítások (Kamera, Fények, Cím)
        self.disableMouse()  # Kikapcsoljuk az alapértelmezett kamera irányítást
        self.camera.setPos(0, -100, 20)
        self.camera.lookAt(0, 0, 0)
        self.title = self.add_title("Space Engineers Style: Deformálható Aszteroidák (Bal klikk: Fúrás)")

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
        model = self.loader.loadModel("models/misc/smiley")
        model.setTextureOff(1)
        
        # Procedurális deformáció (vertex manipulation) - Kezdeti forma
        self.modify_geometry(model)

        # Node beállítása a jelenetben
        model.reparentTo(self.render)
        model.setPos(pos)
        model.setScale(scale)
        model.setColor(0.4 + random.random()*0.2, 0.3 + random.random()*0.2, 0.3, 1.0) # Barnás/Szürkés szín

        # Ütközésvizsgálat hozzáadása
        c_sphere = CollisionSphere(0, 0, 0, 1.1)
        c_node = CollisionNode('asteroid')
        c_node.addSolid(c_sphere)
        c_node.setIntoCollideMask(BitMask32.bit(1))
        c_node.setTag('asteroid_id', str(len(self.asteroids)))
        
        c_np = model.attachNewNode(c_node)

        self.asteroids.append((model, scale))

    def modify_geometry(self, model_np):
        """Kezdeti 'krumpli' forma létrehozása."""
        geom_node = model_np.find("**/+GeomNode").node()
        for i in range(geom_node.getNumGeoms()):
            geom = geom_node.modifyGeom(i)
            vdata = geom.modifyVertexData()
            vertex = GeomVertexRewriter(vdata, 'vertex')
            normal = GeomVertexRewriter(vdata, 'normal')
            while not vertex.isAtEnd():
                v = vertex.getData3f()
                n = normal.getData3f()
                noise = (random.random() * 2.0 - 1.0) * TORZITAS_MATEK * 0.2
                vertex.setData3f(v + n * noise)
                
    def shoot(self):
        """Lövés logika: Deformáció és törmelék spawnolás."""
        if not self.mouseWatcherNode.hasMouse():
            return

        mpos = self.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        self.cTrav.traverse(self.render)
        
        if self.collision_queue.getNumEntries() > 0:
            self.collision_queue.sortEntries()
            entry = self.collision_queue.getEntry(0)
            hit_node = entry.getIntoNode()
            
            if hit_node.getName() == 'asteroid':
                # Megszerezzük a modellt (a collision node szülője)
                hit_np = entry.getIntoNodePath().getParent()
                
                # Találati pont LOKÁLIS koordinátákban (a deformációhoz)
                local_point = entry.getSurfacePoint(hit_np)
                
                # Találati pont GLOBÁLIS koordinátákban (a törmelékhez)
                global_point = entry.getSurfacePoint(self.render)
                
                # 1. Aszteroida deformálása (lyuk fúrása)
                self.deform_asteroid(hit_np, local_point)
                
                # 2. Kis kocka spawnolása
                self.spawn_debris(global_point)

    def deform_asteroid(self, model_np, local_point):
        """
        Space Engineers effekt: A találati pont közelében lévő vertexeket
        benyomjuk a középpontba, így egy 'lyuk' keletkezik a felszínen.
        """
        # A lyuk sugara (model space-ben)
        DEFORMATION_RADIUS = 0.6 
        
        geom_node = model_np.find("**/+GeomNode").node()
        
        # Minden geometria iterálása
        for i in range(geom_node.getNumGeoms()):
            geom = geom_node.modifyGeom(i)
            vdata = geom.modifyVertexData()
            
            vertex = GeomVertexRewriter(vdata, 'vertex')
            
            while not vertex.isAtEnd():
                v = vertex.getData3f()
                
                # Távolság a lézer találati pontjától
                dist = (v - local_point).length()
                
                if dist < DEFORMATION_RADIUS:
                    # Ha a sugáron belül van, "törjük el" a geometriát.
                    # A legegyszerűbb módszer a lyuk illúzióra, ha a vertexet
                    # drasztikusan behúzzuk a modell belsejébe (majdnem a középpontba).
                    # Így a háromszögek befelé fognak mutatni, krátert alkotva.
                    
                    new_v = v * 0.1 # Behúzzuk a középpontba
                    vertex.setData3f(new_v)

    def spawn_debris(self, pos):
        """Létrehoz egy kis törmeléket a találat helyén."""
        debris = self.loader.loadModel("models/box")
        debris.reparentTo(self.render)
        debris.setPos(pos)
        debris.setScale(0.2) # Kicsi kocka
        debris.setColor(0, 1, 0, 1) # Zöld "ásvány"
        
        # Véletlenszerű forgás indításkor
        debris.setHpr(random.uniform(0,360), random.uniform(0,360), 0)
        
        self.loots.append(debris)

    def update_loots(self, task):
        """Forgatja a leesett törmelékeket."""
        dt = globalClock.getDt()
        for loot in self.loots:
            if not loot.isEmpty():
                loot.setH(loot.getH() + 100 * dt)
                loot.setP(loot.getP() + 50 * dt)
        return Task.cont

# Alkalmazás indítása
if __name__ == "__main__":
    app = AszteroidaJatek()
    app.run()