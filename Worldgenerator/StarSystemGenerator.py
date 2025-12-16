import random
from direct.showbase.ShowBase import ShowBase
from panda3d import core as pc # Importáljuk a panda3d.core-t "pc" néven az import hibák elkerülése érdekében

# Panda3D konfiguráció: ablakméret és FPS
pc.loadPrcFileData("", "win-size 1280 720")
pc.loadPrcFileData("", "show-frame-rate-meter 1")

# --- KONSTANSOK ÉS BEÁLLÍTÁSOK ---
NUM_SYSTEMS = 100
MAX_COORD = 500  # A galaxis mérete (-MAX_COORD-tól +MAX_COORD-ig)
NEIGHBOR_COUNT = 3  # Hány legközelebbi rendszert kössünk össze
MAP_SCALE = 0.001  # A 3D koordináták 2D térképre vetítésének skálája
MAP_SIZE = 0.3     # A 2D térkép mérete a képernyőn

class StarSystemGenerator(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0, 0, 0.1, 1) # Sötétkék háttér
        
        # A rendszer pozícióinak és metaadatainak tárolása
        self.systems = []
        self.current_system_index = 0
        
        # 3D geometria frissítéséhez szükséges író (initializálás a create_3d_geometry-ban)
        self.galaxy_color_writer = None 
        # 3D vertex adatok tárolása (initializálás a create_3d_geometry-ban)
        self.galaxy_vdata = None 

        self.setup_camera()
        self.setup_lighting()
        
        # Geometria generálása
        self.generate_galaxy_data()
        self.create_3d_geometry()
        self.create_2d_map_hud()

        # Játék logikához szükséges task beállítása
        self.taskMgr.add(self.update_current_system, "update_current_system_task")
        self.accept('1', self.warp_to_random_system) # '1' gomb: Véletlen ugrás
        self.accept('w', self.move_camera, [pc.LVector3(0, 5, 0)])
        self.accept('s', self.move_camera, [pc.LVector3(0, -5, 0)])
        self.accept('a', self.move_camera, [pc.LVector3(-5, 0, 0)])
        self.accept('d', self.move_camera, [pc.LVector3(5, 0, 0)])
        
        self.update_hud_text() # HUD frissítése

    def setup_camera(self):
        # Alapértelmezett kameramozgás engedélyezése (egér)
        self.disableMouse()
        self.camera.setPos(0, -MAX_COORD * 1.5, MAX_COORD / 2)
        self.camera.lookAt(0, 0, 0)
        
    def setup_lighting(self):
        # Egy egyszerű pontfény a csillagok kiemelésére
        plight = pc.PointLight('plight')
        plight.setColor(pc.LVector4(1, 1, 1, 1))
        plight_np = self.render.attachNewNode(plight)
        plight_np.setPos(0, 0, 0)
        self.render.setLight(plight_np)

    # --- CSATLAKOZÓ PONTOK GENERÁLÁSA (K-Legközelebbi Szomszédok) ---
    def find_nearest_neighbors(self):
        """Meghatározza a rendszerek közötti kapcsolatokat (ugróútvonalakat) a legközelebbi szomszédok alapján."""
        connections = set()
        
        for i in range(NUM_SYSTEMS):
            # Távolságok kiszámítása minden más rendszerhez
            distances = []
            for j in range(NUM_SYSTEMS):
                if i != j:
                    pos_i = self.systems[i]['pos']
                    pos_j = self.systems[j]['pos']
                    dist = (pos_i - pos_j).length()
                    distances.append((dist, j))
            
            # K-legközelebbi szomszéd kiválasztása
            distances.sort(key=lambda x: x[0])
            for k in range(min(NEIGHBOR_COUNT, len(distances))):
                neighbor_j = distances[k][1]
                # A kapcsolatot a két index (i, j) rendezett tuple-jaként tároljuk, 
                # hogy elkerüljük a duplikációt ((1, 5) és (5, 1) ugyanaz)
                connection = tuple(sorted((i, neighbor_j)))
                connections.add(connection)
                
        return list(connections)

    # --- GALAXIS ADATOK GENERÁLÁSA ---
    def generate_galaxy_data(self):
        """Létrehozza a csillagrendszer pozícióit és kapcsolatadatait."""
        print(f"Generálás: {NUM_SYSTEMS} csillagrendszer...")
        
        for i in range(NUM_SYSTEMS):
            x = random.uniform(-MAX_COORD, MAX_COORD)
            y = random.uniform(-MAX_COORD, MAX_COORD)
            z = random.uniform(-MAX_COORD / 3, MAX_COORD / 3) # Vékonyabb galaxis sík
            
            self.systems.append({
                'id': i,
                'name': f"Rendszer-{i:03d}",
                'pos': pc.LVector3(x, y, z),
                'color': pc.LVector4(random.random(), random.random(), random.random(), 1)
            })
            
        # Kapcsolatok generálása
        self.connections = self.find_nearest_neighbors()
        print(f"Generálás kész. Kapcsolatok száma: {len(self.connections)}")

    # --- 3D GEOMETRIA LÉTREHOZÁSA (VERTEXEK ALAPJÁN) ---
    def create_3d_geometry(self):
        """
        Létrehozza a csillagok és a vonalak 3D geometriáját.
        FONTOS: A Panda3D kényszerei miatt a pontokhoz és a vonalakhoz külön Geom objektumot kell használni.
        """
        
        # 1. Vertex adatok létrehozása (pozíció, szín) - Ezt osztják meg a Geom-ok
        format_star = pc.GeomVertexFormat.getV3c4()
        self.galaxy_vdata = pc.GeomVertexData('galaxy_vdata', format_star, pc.Geom.UHDynamic) # Mentés: self.galaxy_vdata
        vertex_writer = pc.GeomVertexWriter(self.galaxy_vdata, 'vertex')
        self.galaxy_color_writer = pc.GeomVertexWriter(self.galaxy_vdata, 'color') # Mentés: self.galaxy_color_writer
        
        # 2. Csillagok (Pontok) geometriájának feltöltése
        star_points = pc.GeomPoints(pc.Geom.UHDynamic)
        for system in self.systems:
            pos = system['pos']
            color = system['color']
            
            vertex_writer.addData3f(pos.x, pos.y, pos.z)
            self.galaxy_color_writer.addData4f(color) # Író használata
            
            # Minden csillag egyetlen pont a GeomPoints primitívben
            star_points.addVertex(system['id'])
            
        # 3. Kapcsolatok (Vonalak) geometriájának feltöltése
        star_lines = pc.GeomLines(pc.Geom.UHDynamic)
        for index1, index2 in self.connections:
            # A GeomVertexData indexei megegyeznek a self.systems listában lévő indexekkel
            star_lines.addVertices(index1, index2)
            star_lines.closePrimitive()
            
        # 4. GeomNode létrehozása és a két különböző Geom hozzáadása
        galaxy_node = pc.GeomNode('galaxy_geom_node')

        # Geom 1: Csillagok (Pontok)
        star_geom_points = pc.Geom(self.galaxy_vdata)
        star_geom_points.addPrimitive(star_points)
        galaxy_node.addGeom(star_geom_points)
        
        # Geom 2: Kapcsolatok (Vonalak)
        star_geom_lines = pc.Geom(self.galaxy_vdata)
        star_geom_lines.addPrimitive(star_lines)
        galaxy_node.addGeom(star_geom_lines)

        self.galaxy_np = self.render.attachNewNode(galaxy_node)
        
        # 5. Render beállítások
        # Az attribútumokat eltávolítottuk, mivel hibát okoztak ebben a környezetben.
        
        # Áttetszőség beállítása a vonalakhoz/csillagokhoz.
        self.galaxy_np.setTransparency(pc.TransparencyAttrib.MAlpha)

    # --- 2D TÉRKÉP LÉTREHOZÁSA (HUD) ---
    def create_2d_map_hud(self):
        """Létrehozza a 2D minitérképet a képernyő jobb felső sarkában."""
        
        # 1. Térkép háttere (egyszerű zöld négyzet)
        map_bg = self.aspect2d.attachNewNode("map-background")
        map_bg.setPos(1.0 - MAP_SIZE, 0, 1.0 - MAP_SIZE) # Jobb felső sarok (X+, Z+)
        map_bg.setScale(MAP_SIZE)
        
        # Vertexek a háttér négyzetnek
        bg_vdata = pc.GeomVertexData('map_bg_vdata', pc.GeomVertexFormat.getV3c4(), pc.Geom.UHDynamic)
        vwriter = pc.GeomVertexWriter(bg_vdata, 'vertex')
        cwriter = pc.GeomVertexWriter(bg_vdata, 'color')
        
        # Négyzet vertexei (lokális koordináták 0-1 tartományban)
        vwriter.addData3f(0, 0, 0); cwriter.addData4f(0, 0.2, 0.4, 0.5)
        vwriter.addData3f(1, 0, 0); cwriter.addData4f(0, 0.2, 0.4, 0.5)
        vwriter.addData3f(1, 0, 1); cwriter.addData4f(0, 0.4, 0.7, 0.5)
        vwriter.addData3f(0, 0, 1); cwriter.addData4f(0, 0.4, 0.7, 0.5)

        # Helyesbítés: GeomTristrips használata GeomPrimitive(Geom.TPStrips) helyett
        bg_tris = pc.GeomTristrips(pc.Geom.UHDynamic)
        bg_tris.addConsecutiveVertices(0, 4)
        
        bg_geom = pc.Geom(bg_vdata)
        bg_geom.addPrimitive(bg_tris)
        
        bg_node = pc.GeomNode('map_bg_node')
        bg_node.addGeom(bg_geom)
        map_bg.attachNewNode(bg_node)
        map_bg.setTransparency(pc.TransparencyAttrib.MAlpha)
        
        # 2. Térkép adatok (csillagok és vonalak)
        # Létrehozzuk a VData-t, amit frissíteni fogunk
        self.map_vdata = pc.GeomVertexData('map_vdata', pc.GeomVertexFormat.getV3c4(), pc.Geom.UHDynamic)
        self.map_vwriter = pc.GeomVertexWriter(self.map_vdata, 'vertex')
        self.map_cwriter = pc.GeomVertexWriter(self.map_vdata, 'color')
        
        # A 2D térképen is külön-külön hozunk létre primitíveket, de ugyanazt a VData-t használják
        self.map_points = pc.GeomPoints(pc.Geom.UHDynamic)
        self.map_lines = pc.GeomLines(pc.Geom.UHDynamic)

        # 3. GeomNode és NodePath létrehozása a térkép objektumoknak (megoldja az AssertionError-t itt is)
        map_node = pc.GeomNode('map_geom_node')
        
        # Geom 1: Térkép Pontok
        map_geom_points = pc.Geom(self.map_vdata)
        map_geom_points.addPrimitive(self.map_points)
        map_node.addGeom(map_geom_points)
        
        # Geom 2: Térkép Vonalak
        map_geom_lines = pc.Geom(self.map_vdata)
        map_geom_lines.addPrimitive(self.map_lines)
        map_node.addGeom(map_geom_lines)
        
        self.map_np = map_bg.attachNewNode(map_node) # Csatolás a háttérhez
        
        # 4. Térkép beállítások - a hibás attribútumok eltávolítva.
        
        # 5. HUD szöveg (információ)
        self.hud_text = pc.TextNode('hud_text')
        self.hud_text.setText("Generálva")
        self.hud_text.setTextColor(1, 1, 1, 1)
        self.hud_np = self.aspect2d.attachNewNode(self.hud_text)
        self.hud_np.setScale(0.05)
        # HIBAJAVÍTÁS: self.aspectRatio helyett self.getAspectRatio() használata és kis margó beállítása.
        self.hud_np.setPos(-self.getAspectRatio() + 0.05, 0, 0.9)
        
        self.redraw_map()

    # --- TÉRKÉP FRISSÍTÉSE ---
    def redraw_map(self):
        """Újrarajzolja a térképet a jelenlegi rendszer középpontjában."""
        
        current_pos = self.systems[self.current_system_index]['pos']
        
        # Töröljük a korábbi adatokat (újraírjuk a VData-t)
        self.map_vwriter.setRow(0)
        self.map_cwriter.setRow(0)
        self.map_points.clearVertices()
        self.map_lines.clearVertices()
        
        # 1. Térkép Vertexek (Pontok) feltöltése
        for i, system in enumerate(self.systems):
            pos = system['pos']
            
            # A pozíciót a jelenlegi rendszerhez viszonyítva számoljuk ki (relatív koordináták)
            # CSAK az X és Y tengelyeket használjuk (felülnézet)
            relative_pos = pos - current_pos
            
            # Skálázás és normalizálás a 0 és 1 közötti térkép koordinátákra (0.5 a középpont)
            map_x = relative_pos.x * MAP_SCALE + 0.5
            map_z = relative_pos.y * MAP_SCALE + 0.5 # A Y-tengelyt vetítjük a 2D térkép Z-tengelyére
            
            # Csak azokat a rendszereket vesszük figyelembe, amelyek a térkép "látóterében" vannak (0 és 1 között)
            if 0 < map_x < 1 and 0 < map_z < 1:
                
                # Vertex hozzáadása a térkép VData-jához
                self.map_vwriter.addData3f(map_x, 0, map_z)
                
                # Szín beállítása
                if i == self.current_system_index:
                    # Jelenlegi rendszer (fehér/élénk)
                    self.map_cwriter.addData4f(1, 1, 0, 1) 
                    map_index = self.map_vwriter.getWriteRow() - 1
                    self.map_points.addVertex(map_index)
                else:
                    # Környező rendszerek (eredeti szín, áttetszőbb)
                    self.map_cwriter.addData4f(system['color'].x, system['color'].y, system['color'].z, 0.5)
                    map_index = self.map_vwriter.getWriteRow() - 1
                    self.map_points.addVertex(map_index)
            
                # Ideiglenesen tároljuk a térkép-indexet a vonalak rajzolásához (ha bent van a 0-1 tartományban)
                system['map_index'] = self.map_vwriter.getWriteRow() - 1
            else:
                system['map_index'] = -1 # A rendszer nincs a térképen

        # 2. Térkép Kapcsolatok (Vonalak) feltöltése
        for index1, index2 in self.connections:
            sys1 = self.systems[index1]
            sys2 = self.systems[index2]
            
            # Csak akkor rajzoljuk ki a vonalat, ha mindkét rendszer látható a térképen
            if sys1['map_index'] != -1 and sys2['map_index'] != -1:
                # A GeomLines primitívben a VData-ban lévő indexeket használjuk
                self.map_lines.addVertices(sys1['map_index'], sys2['map_index'])
                self.map_lines.closePrimitive()
        
        # A VData frissítése (fontos, hogy a Panda3D lássa a változást)
        # A markDirty() hívás eltávolítva.

    # --- JÁTÉK LOGIKA ÉS FRISSÍTÉSEK ---
    def update_current_system(self, task):
        """Frissíti a jelenlegi rendszer jelölőjét a 3D-s térben."""
        
        writer = self.galaxy_color_writer
        
        # A 3D-s világban megváltoztatjuk a jelenlegi rendszer színét sárgára/fehérre
        if self.current_system_index is not None:
            # 1. A régi pozíció visszaállítása az eredeti színre (ha volt előző rendszer)
            old_index = (self.current_system_index - 1) % NUM_SYSTEMS
            if self.current_system_index != 0 and old_index != self.current_system_index:
                old_color = self.systems[old_index]['color']
                
                # HIBAJAVÍTÁS: setSubdata helyett GeomVertexWriter használata
                writer.setRow(old_index)
                writer.setData4f(old_color.x, old_color.y, old_color.z, old_color.w)
            
            # 2. A jelenlegi pozíció sárgára/fehérre állítása
            current_index = self.current_system_index
            current_color_data = pc.LVector4(1, 1, 0, 1) # Élénksárga
            
            # HIBAJAVÍTÁS: setSubdata helyett GeomVertexWriter használata
            writer.setRow(current_index)
            writer.setData4f(current_color_data.x, current_color_data.y, current_color_data.z, current_color_data.w)
        
        # Frissítjük a térképet, hogy a jelenlegi rendszer középen legyen
        self.redraw_map()
        self.update_hud_text()
        
        return task.cont

    def warp_to_random_system(self):
        """Véletlen csillagrendszerbe ugrás."""
        new_index = random.randint(0, NUM_SYSTEMS - 1)
        if new_index != self.current_system_index:
            self.current_system_index = new_index
            new_pos = self.systems[new_index]['pos']
            
            # A kamera pozíciójának beállítása az új rendszer elé
            self.camera.setPos(new_pos.x, new_pos.y - 100, new_pos.z + 50)
            self.camera.lookAt(new_pos)
            
            # Erőltetett frissítés a térképen
            self.redraw_map()
            self.update_hud_text()
            print(f"Ugrás a(z) {self.systems[new_index]['name']} rendszerbe. (Index: {new_index})")

    def move_camera(self, direction):
        """Kamera mozgatása a WASD gombokkal."""
        self.camera.setPos(self.camera, direction * 2)

    def update_hud_text(self):
        """Frissíti a HUD szöveges információit."""
        current_system = self.systems[self.current_system_index]
        pos = current_system['pos']
        
        text = (
            f"Jelenlegi rendszer: {current_system['name']} (ID: {current_system['id']})\n"
            f"Koordináták: X={pos.x:.1f}, Y={pos.y:.1f}, Z={pos.z:.1f}\n"
            f"\n"
            f"Kezelőszervek:\n"
            f"WASD: Kamera mozgása\n"
            f"1: Ugrás véletlen rendszerbe\n"
            f"MAP: Térkép 2D vetülete a jelenlegi rendszerről (jobb fent)"
        )
        self.hud_text.setText(text)

# --- INDÍTÁS ---
app = StarSystemGenerator()
app.run()