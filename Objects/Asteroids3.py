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
ASZTEROIDA_SZAM = 10
SUGAR_MIN = 3.0
SUGAR_MAX = 5.0
TERULET_MERET = 40.0
TORZITAS_MATEK = 1.5

class AszteroidaJatek(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # 1. Alapvető beállítások
        self.disableMouse()
        self.camera.setPos(0, -100, 20)
        self.camera.lookAt(0, 0, 0)
        self.title = self.add_title("Bal klikk: Fúrás | Jobb klikk (tartva): Vonósugár")

        # Ütközésvizsgáló rendszer
        self.cTrav = CollisionTraverser()
        self.collision_queue = CollisionHandlerQueue()

        # A sugár (lézer/vonósugár) létrehozása
        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(BitMask32.bit(1))
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.cTrav.addCollider(self.picker_np, self.collision_queue)

        # Aszteroidák és Loot-ok tárolója
        self.asteroids = []
        self.loots = []
        
        # Vonósugár állapota
        self.tractor_active = False

        # 2. Aszteroidák generálása
        self.generate_asteroids()

        # 3. Eseménykezelők
        self.accept("mouse1", self.shoot)
        
        # Vonósugár kezelése (lenyomás és felengedés)
        self.accept("mouse3", self.start_tractor)
        self.accept("mouse3-up", self.stop_tractor)
        
        self.accept("escape", self.userExit)

        # 4. Taskok
        self.taskMgr.add(self.update_loots, "UpdateLoots")
        self.taskMgr.add(self.update_tractor, "UpdateTractor")

    def add_title(self, text):
        title = TextNode('title')
        title.setText(text)
        title.setTextColor(1, 1, 1, 1)
        titleNode = self.aspect2d.attachNewNode(title)
        titleNode.setScale(0.05)
        titleNode.setPos(-0.9, 0, 0.9)
        return titleNode

    def generate_asteroids(self):
        print(f"Generálás indítása: {ASZTEROIDA_SZAM} db aszteroida...")
        attempts = 0
        while len(self.asteroids) < ASZTEROIDA_SZAM and attempts < 1000:
            attempts += 1
            x = random.uniform(-TERULET_MERET, TERULET_MERET)
            y = random.uniform(-TERULET_MERET, TERULET_MERET)
            z = random.uniform(-TERULET_MERET/2, TERULET_MERET/2)
            pos = Point3(x, y, z)
            scale = random.uniform(SUGAR_MIN, SUGAR_MAX)
            
            if not self.check_overlap(pos, scale):
                self.create_procedural_asteroid(pos, scale)

    def check_overlap(self, pos, scale):
        for ast_np, ast_scale in self.asteroids:
            dist = (ast_np.getPos() - pos).length()
            min_dist = ast_scale + scale + 2.0
            if dist < min_dist:
                return True
        return False

    def create_procedural_asteroid(self, pos, scale):
        model = self.loader.loadModel("models/misc/smiley")
        model.setTextureOff(1)
        self.modify_geometry(model)

        model.reparentTo(self.render)
        model.setPos(pos)
        model.setScale(scale)
        model.setColor(0.4 + random.random()*0.2, 0.3 + random.random()*0.2, 0.3, 1.0)

        c_sphere = CollisionSphere(0, 0, 0, 1.1)
        c_node = CollisionNode('asteroid')
        c_node.addSolid(c_sphere)
        c_node.setIntoCollideMask(BitMask32.bit(1))
        c_node.setTag('asteroid_id', str(len(self.asteroids)))
        
        c_np = model.attachNewNode(c_node)
        self.asteroids.append((model, scale))

    def modify_geometry(self, model_np):
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
        if not self.mouseWatcherNode.hasMouse():
            return

        mpos = self.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        self.cTrav.traverse(self.render)
        
        if self.collision_queue.getNumEntries() > 0:
            self.collision_queue.sortEntries()
            entry = self.collision_queue.getEntry(0)
            hit_node = entry.getIntoNode()
            
            # Csak aszteroidákra lövünk
            if hit_node.getName() == 'asteroid':
                hit_np = entry.getIntoNodePath().getParent()
                local_point = entry.getSurfacePoint(hit_np)
                global_point = entry.getSurfacePoint(self.render)
                
                self.deform_asteroid(hit_np, local_point)
                self.spawn_debris(global_point)

    def start_tractor(self):
        """Vonósugár bekapcsolása"""
        self.tractor_active = True

    def stop_tractor(self):
        """Vonósugár kikapcsolása"""
        self.tractor_active = False

    def update_tractor(self, task):
        """Folyamatosan fut: ha aktív a sugár, vonzza a lootot."""
        if not self.tractor_active:
            return Task.cont
            
        if not self.mouseWatcherNode.hasMouse():
            return Task.cont

        # Sugár frissítése az egér pozíciójához
        mpos = self.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        
        # Ütközésvizsgálat
        self.cTrav.traverse(self.render)

        if self.collision_queue.getNumEntries() > 0:
            self.collision_queue.sortEntries()
            # Megnézzük a legközelebbi találatot
            entry = self.collision_queue.getEntry(0)
            hit_node = entry.getIntoNode()

            # Ha loot-ot találtunk el
            if hit_node.getName() == 'loot':
                loot_np = entry.getIntoNodePath().getParent()
                
                # Vonzás logika
                loot_pos = loot_np.getPos()
                cam_pos = self.camera.getPos()
                
                # Irány vektor a kamerához
                direction = cam_pos - loot_pos
                dist = direction.length()
                direction.normalize()
                
                # Ha nagyon közel van, "begyűjtjük" (eltüntetjük)
                if dist < 3.0:
                    loot_np.removeNode()
                    print("Loot begyűjtve!")
                else:
                    # Különben mozgatjuk felénk
                    speed = 30.0 * globalClock.getDt()
                    loot_np.setPos(loot_pos + direction * speed)

        return Task.cont

    def deform_asteroid(self, model_np, local_point):
        DEFORMATION_RADIUS = 0.6 
        geom_node = model_np.find("**/+GeomNode").node()
        for i in range(geom_node.getNumGeoms()):
            geom = geom_node.modifyGeom(i)
            vdata = geom.modifyVertexData()
            vertex = GeomVertexRewriter(vdata, 'vertex')
            while not vertex.isAtEnd():
                v = vertex.getData3f()
                dist = (v - local_point).length()
                if dist < DEFORMATION_RADIUS:
                    new_v = v * 0.1
                    vertex.setData3f(new_v)

    def spawn_debris(self, pos):
        debris = self.loader.loadModel("models/box")
        debris.reparentTo(self.render)
        debris.setPos(pos)
        debris.setScale(0.2)
        debris.setColor(0, 1, 0, 1)
        debris.setHpr(random.uniform(0,360), random.uniform(0,360), 0)
        
        # CollisionNode hozzáadása a törmelékhez, hogy a sugár lássa
        # Nagyobb sugarat adunk (4.0), mert a szülő scale kicsi (0.2) -> effektív méret 0.8
        c_sphere = CollisionSphere(0, 0, 0, 4.0)
        c_node = CollisionNode('loot')
        c_node.addSolid(c_sphere)
        c_node.setIntoCollideMask(BitMask32.bit(1))
        
        debris.attachNewNode(c_node)
        
        self.loots.append(debris)

    def update_loots(self, task):
        dt = globalClock.getDt()
        for loot in self.loots:
            if not loot.isEmpty():
                loot.setH(loot.getH() + 100 * dt)
                loot.setP(loot.getP() + 50 * dt)
        return Task.cont

if __name__ == "__main__":
    app = AszteroidaJatek()
    app.run()