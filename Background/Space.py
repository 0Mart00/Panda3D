import random
import math
from panda3d.core import (
    NodePath, Geom, GeomNode, GeomPoints, GeomVertexFormat,
    GeomVertexData, GeomVertexWriter, PNMImage, Texture,
    TransparencyAttrib, ColorBlendAttrib, CardMaker,
    Vec3, Vec4, Point3, PerlinNoise2, StackedPerlinNoise2
)
from direct.showbase.ShowBase import ShowBase
from direct.task import Task

# --- KONFIGURÁCIÓ ---
SEED = 42
STAR_COUNT = 4000
NEBULA_LAYER_COUNT = 30
SKY_RADIUS = 500.0  # Milyen távol legyen a háttér
NEBULA_RES = 128    # Textúra felbontás (pixel)

class SpaceBackground:
    def __init__(self, render_node, camera_node):
        """
        Létrehozza a procedurális hátteret.
        :param render_node: A jelenet gyökere (render)
        :param camera_node: A kamera node (base.camera), amihez a gömböt rögzítjük
        """
        self.root = render_node.attachNewNode("SpaceBackground")
        self.camera = camera_node
        
        # Random seed beállítása a determinisztikus generáláshoz
        random.seed(SEED)
        
        # 1. Csillagmező generálása
        self.create_stars()
        
        # 2. Nebula felhők generálása
        self.create_nebula()

        # Renderelési beállítások:
        # Kikapcsoljuk a mélységírást, hogy mindig a háttérben maradjon,
        # de a mélységteszt marad, hogy a felhők takarják a csillagokat, ha kell.
        self.root.setBin("background", 0)
        self.root.setDepthWrite(False)
        self.root.setLightOff() # Nem kell világítás, a vertex színek dominálnak
        
        # Task a pozíció frissítésére (Skybox viselkedés)
        base.taskMgr.add(self.update_position, "UpdateSkyboxPos")

    def get_random_point_on_sphere(self, radius):
        """Véletlen pont generálása gömbhéjon (uniform eloszlás)."""
        theta = random.uniform(0, 2 * math.pi)
        phi = math.acos(random.uniform(-1, 1))
        
        x = radius * math.sin(phi) * math.cos(theta)
        y = radius * math.sin(phi) * math.sin(theta)
        z = radius * math.cos(phi)
        return Point3(x, y, z)

    def create_stars(self):
        """Pontszerű csillagok létrehozása GeomPoints segítségével."""
        format = GeomVertexFormat.getV3c4() # Pozíció + Szín
        vdata = GeomVertexData('stars', format, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        
        for _ in range(STAR_COUNT):
            pos = self.get_random_point_on_sphere(SKY_RADIUS * 1.5) # Kicsit távolabb a nebuláknál
            vertex.addData3(pos)
            
            # Csillag színek: EVE stílusban főleg fehér/kék, kevés sárgával
            r_val = random.random()
            if r_val > 0.9: # Sárgás/Vöröses
                c = Vec4(1.0, 0.8, 0.6, 1.0)
            elif r_val > 0.6: # Kékes
                c = Vec4(0.6, 0.7, 1.0, 1.0)
            else: # Fehér
                c = Vec4(random.uniform(0.8, 1.0), random.uniform(0.8, 1.0), random.uniform(0.8, 1.0), 1.0)
            
            # Random fényerő
            brightness = random.uniform(0.3, 1.0)
            color.addData4(c * brightness)

        points = GeomPoints(Geom.UHStatic)
        points.addNextVertices(STAR_COUNT)
        
        geom = Geom(vdata)
        geom.addPrimitive(points)
        
        node = GeomNode('star_geom')
        node.addGeom(geom)
        self.root.attachNewNode(node)

    def generate_noise_texture(self):
        """Runtime PNMImage generálása Perlin noise segítségével."""
        pnm = PNMImage(NEBULA_RES, NEBULA_RES)
        
        # Javítás: StackedPerlinNoise2 paraméterek: sx, sy, octaves, persistence, scale, table_size, seed
        # A table_size-nak 2-hatványnak kell lennie (pl. 256).
        perlin = StackedPerlinNoise2(0.5, 0.5, 4, 0.5, 2.0, 256, SEED)
        
        # Pixel kitöltés
        for x in range(NEBULA_RES):
            for y in range(NEBULA_RES):
                # Normalizált koordináták
                nx = x / float(NEBULA_RES)
                ny = y / float(NEBULA_RES)
                
                # Noise érték (-1..1 -> 0..1)
                val = (perlin.noise(nx * 4, ny * 4) + 1.0) * 0.5
                
                # Szélek elhalványítása (vignette), hogy ne látszódjon a kártya széle
                dx = nx - 0.5
                dy = ny - 0.5
                dist = math.sqrt(dx*dx + dy*dy)
                mask = max(0.0, 1.0 - (dist * 2.5)) # Radial gradient mask
                
                final_val = val * mask
                pnm.setGray(x, y, final_val)
        
        tex = Texture()
        tex.load(pnm)
        return tex

    def create_nebula(self):
        """Nebula felhők létrehozása billboard sprite-okból."""
        tex = self.generate_noise_texture()
        cm = CardMaker('nebula_card')
        cm.setFrame(-200, 200, -200, 200) # Nagy méretű lapok
        
        # Alapszínek (EVE stílusú paletta)
        colors = [
            Vec4(0.2, 0.0, 0.4, 0.2), # Mély lila
            Vec4(0.0, 0.2, 0.5, 0.2), # Ciánkék
            Vec4(0.0, 0.3, 0.1, 0.15),# Zöldes
            Vec4(0.4, 0.1, 0.1, 0.15) # Vöröses
        ]
        
        base_color = random.choice(colors)

        for i in range(NEBULA_LAYER_COUNT):
            card = self.root.attachNewNode(cm.generate())
            card.setTexture(tex)
            
            # Pozicionálás
            pos = self.get_random_point_on_sphere(SKY_RADIUS)
            card.setPos(pos)
            card.lookAt(Point3(0, 0, 0)) # Középpont felé nézzen (billboard effect)
            
            # Véletlenszerű forgatás a saját tengelye körül
            card.setR(random.uniform(0, 360))
            
            # Szín variáció
            layer_color = base_color + Vec4(
                random.uniform(-0.1, 0.1),
                random.uniform(-0.1, 0.1),
                random.uniform(-0.1, 0.1),
                0
            )
            card.setColor(layer_color)
            
            # Transzparencia és Blend mód
            card.setTransparency(TransparencyAttrib.MAlpha)
            # Additív blendelés a "ragyogó" gáz hatáshoz
            card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
            
            # Billboard beállítás: mindig a kamera felé forduljon
            card.setBillboardPointEye()

    def update_position(self, task):
        """A háttér pozícióját a kamerához igazítja."""
        if self.camera:
            self.root.setPos(self.camera.getPos(base.render))
        return Task.cont

class EveSpaceApp(ShowBase):
    def __init__(self):
        super().__init__()
        
        # Ablak beállítások
        self.disableMouse() # Saját kamera irányítás vagy fix
        self.set_background_color(0, 0, 0) # Fekete űr
        
        # Háttér generálása
        self.bg = SpaceBackground(self.render, self.camera)
        
        # Egyszerű kamera forgatás (hogy körbe lehessen nézni)
        self.camera_angle = 0
        self.taskMgr.add(self.spin_camera, "SpinCamera")
        
        print(f"Space generated with SEED: {SEED}")
        print("Controls: Mouse logic disabled for smooth auto-spin.")

    def spin_camera(self, task):
        self.camera_angle += 0.1
        # Lassú keringés, hogy látszódjon a parallax és a skybox stabilitása
        self.camera.setHpr(self.camera_angle, 0, 0)
        return Task.cont

if __name__ == "__main__":
    app = EveSpaceApp()
    app.run()