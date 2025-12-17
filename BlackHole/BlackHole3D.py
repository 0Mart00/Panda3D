import sys
import math
import random
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import (
    Geom, GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    GeomTriangles, GeomNode, NodePath,
    Shader, Texture,
    Vec3, Vec4, Point3
)

# -----------------------------------------------------------------------------
# GLSL SHADERS (Beágyazott sztringekként a hordozhatóság érdekében)
# -----------------------------------------------------------------------------

# Vertex Shader: Transzformálja a vertexeket és továbbítja az UV-kat
VERT_SHADER = """
#version 130

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;

uniform mat4 p3d_ModelViewProjectionMatrix;

out vec2 v_uv;
out vec4 v_pos;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    v_uv = p3d_MultiTexCoord0;
    v_pos = p3d_Vertex;
}
"""

# Fragment Shader: Akkréciós korong (Zaj, Rotáció, Szín)
FRAG_SHADER_DISK = """
#version 130

in vec2 v_uv;
uniform float u_time;

// Procedurális Simplex Noise (egyszerűsített változat GLSL-hez)
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
             -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy) );
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
        + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m ;
    m = m*m ;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}

void main() {
    // Középponttól való távolság (UV 0.5, 0.5 a középpont)
    vec2 centered_uv = v_uv - 0.5;
    float dist = length(centered_uv) * 2.0; // 0 és 1 közötti sugár
    float angle = atan(centered_uv.y, centered_uv.x);

    // Lyuk közepe (Eseményhorizont vágás)
    if (dist < 0.25) discard;
    if (dist > 1.0) discard;

    // Differenciális Rotáció:
    // A belső részek gyorsabban forognak (Kepler-törvény imitáció: speed ~ 1/r)
    float speed = 2.0 / (dist + 0.1); 
    float rotation = angle + u_time * speed * 0.5;

    // Zaj generálás (több réteg a részletességért)
    float n1 = snoise(vec2(rotation * 3.0, dist * 5.0 - u_time));
    float n2 = snoise(vec2(rotation * 10.0, dist * 15.0));
    
    // Kombinált zajminta
    float noise = (n1 + 0.5 * n2);
    
    // Intenzitás és Alpha
    // Lágy szélek (fade in/out)
    float alpha = smoothstep(0.25, 0.35, dist) * (1.0 - smoothstep(0.8, 1.0, dist));
    
    // Pulzálás
    float pulse = 1.0 + 0.1 * sin(u_time * 2.0);
    
    // Színkeverés: Hőmérséklet alapú (Fekete -> Vörös -> Narancs -> Fehér)
    // A zaj befolyásolja a fényerőt
    float brightness = (noise * 0.5 + 0.5) * alpha * pulse * (1.5 / dist);
    
    vec3 col_inner = vec3(1.0, 0.9, 0.8); // Fehér/Sárga mag
    vec3 col_outer = vec3(1.0, 0.2, 0.05); // Vörös szél
    
    vec3 final_color = mix(col_outer, col_inner, brightness * brightness);
    
    // HDR-szerű boost a Bloom filternek
    gl_FragColor = vec4(final_color * 2.5, alpha);
}
"""

# Fragment Shader: Fekete Lyuk (Singularity)
# Egyszerű tiszta fekete, de lehetne ide írni lencsézést is (bár az komplexebb)
FRAG_SHADER_BLACK = """
#version 130
void main() {
    gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
}
"""

# -----------------------------------------------------------------------------
# ALKALMAZÁS OSZTÁLY
# -----------------------------------------------------------------------------

class BlackHoleSim(ShowBase):
    def __init__(self):
        super().__init__()
        
        # Ablak beállítások
        self.set_background_color(0, 0, 0)
        self.disable_mouse() # Saját kamera irányítást írhatnánk, de most fix pályát használunk
        self.cam.set_pos(0, -15, 5)
        self.cam.look_at(0, 0, 0)
        
        # 1. Háttér (Csillagok)
        self.create_starfield(num_stars=2000)

        # 2. Fekete Lyuk (Eseményhorizont)
        self.singularity = self.create_event_horizon()
        
        # 3. Akkréciós Korong
        self.accretion_disk = self.create_accretion_disk()
        
        # 4. Post-Processing (Bloom effekt a ragyogáshoz)
        self.filters = CommonFilters(self.win, self.cam)
        filter_ok = self.filters.setBloom(
            blend=(0, 0, 0, 1), 
            mintrigger=0.6, 
            desat=0.1, 
            intensity=2.0, 
            size="medium"
        )
        if not filter_ok:
            print("Figyelem: A videokártya nem támogatja a Bloom effektet.")

        # 5. Animációs Task indítása
        self.task_mgr.add(self.update_scene, "UpdateSceneTask")
        
        # Orbitális kamera mozgás változói
        self.orbit_angle = 0.0

    def create_starfield(self, num_stars=1000):
        """Procedurális pontfelhő létrehozása a háttérnek."""
        format = GeomVertexFormat.get_v3c4()
        vdata = GeomVertexData('stars', format, Geom.UH_static)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        
        for _ in range(num_stars):
            # Véletlenszerű pontok egy gömbhéjon
            x = random.uniform(-1, 1)
            y = random.uniform(-1, 1)
            z = random.uniform(-1, 1)
            
            # Normalizálás és skálázás (messze legyenek)
            d = math.sqrt(x*x + y*y + z*z)
            if d == 0: continue
            scale = random.uniform(50, 100)
            
            vertex.add_data3(x/d * scale, y/d * scale, z/d * scale)
            
            # Csillag fényerő variáció
            brightness = random.uniform(0.4, 1.0)
            color.add_data4(brightness, brightness, brightness, 1)
            
        points = GeomNode('star_points')
        geom = Geom(vdata)
        from panda3d.core import GeomPoints
        pts = GeomPoints(Geom.UH_static)
        pts.add_next_vertices(num_stars)
        geom.add_primitive(pts)
        points.add_geom(geom)
        
        star_np = self.render.attach_new_node(points)
        star_np.set_light_off() # A csillagok ne reagáljanak fényekre (unlit)

    def create_procedural_sphere(self, radius=1.0, rows=30, segs=30):
        """GeomVertexData alapú gömb generálása kódolva (nincs modell betöltés)."""
        format = GeomVertexFormat.get_v3()
        vdata = GeomVertexData('sphere', format, Geom.UH_static)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Vertexek generálása
        for i in range(rows + 1):
            lat = (math.pi * i) / rows - (math.pi / 2.0)
            z = radius * math.sin(lat)
            r_plane = radius * math.cos(lat)
            
            for j in range(segs + 1):
                lon = (2 * math.pi * j) / segs
                x = r_plane * math.cos(lon)
                y = r_plane * math.sin(lon)
                vertex.add_data3(x, y, z)
                
        # Háromszögek (Triangles) összekötése
        geom = Geom(vdata)
        tris = GeomTriangles(Geom.UH_static)
        
        for i in range(rows):
            for j in range(segs):
                v1 = i * (segs + 1) + j
                v2 = v1 + 1
                v3 = (i + 1) * (segs + 1) + j
                v4 = v3 + 1
                
                # Két háromszög per négyszög
                tris.add_vertices(v1, v2, v3)
                tris.add_vertices(v2, v4, v3)
                
        geom.add_primitive(tris)
        node = GeomNode('sphere_node')
        node.add_geom(geom)
        return node

    def create_event_horizon(self):
        """A központi fekete gömb létrehozása."""
        geom_node = self.create_procedural_sphere(radius=1.5, rows=40, segs=40)
        np = self.render.attach_new_node(geom_node)
        
        # Shader betöltése (Tiszta fekete)
        shader = Shader.make(Shader.SL_GLSL, VERT_SHADER, FRAG_SHADER_BLACK)
        np.set_shader(shader)
        
        return np

    def create_accretion_disk(self):
        """Egy lapos négyzet (Quad) létrehozása, amire a gyűrű shader kerül."""
        # Azért Quad-ot használunk, mert a "lyukat" és a formát a Shader alpha csatornája vágja ki
        # Ez egyszerűbb és szebb éleket ad, mint a geometria vágása.
        
        format = GeomVertexFormat.get_v3t2() # Kell pozíció és UV
        vdata = GeomVertexData('disk', format, Geom.UH_static)
        vertex = GeomVertexWriter(vdata, 'vertex')
        texcoord = GeomVertexWriter(vdata, 'texcoord')
        
        size = 8.0 # A korong mérete
        
        # 4 sarokpont
        vertex.add_data3(-size, -size, 0); texcoord.add_data2(0, 0)
        vertex.add_data3( size, -size, 0); texcoord.add_data2(1, 0)
        vertex.add_data3( size,  size, 0); texcoord.add_data2(1, 1)
        vertex.add_data3(-size,  size, 0); texcoord.add_data2(0, 1)
        
        geom = Geom(vdata)
        tris = GeomTriangles(Geom.UH_static)
        # Két háromszög
        tris.add_vertices(0, 1, 2)
        tris.add_vertices(0, 2, 3)
        
        geom.add_primitive(tris)
        node = GeomNode('disk_node')
        node.add_geom(geom)
        
        np = self.render.attach_new_node(node)
        
        # Átlátszóság beállítása
        np.set_transparency(True)
        # Kétoldalú renderelés (hogy alulról is látszódjon)
        np.set_two_sided(True)
        
        # Shader beállítása
        shader = Shader.make(Shader.SL_GLSL, VERT_SHADER, FRAG_SHADER_DISK)
        np.set_shader(shader)
        np.set_shader_input("u_time", 0.0)
        
        # Döntés, hogy jobban látszódjon a perspektíva
        np.set_hpr(0, -15, 0) 
        
        return np

    def update_scene(self, task):
        """Minden frame-ben lefutó frissítés."""
        time = task.time
        
        # 1. Shader Uniform frissítése (Animáció)
        self.accretion_disk.set_shader_input("u_time", time)
        
        # 2. Kamera lassú keringése
        # Orbitális távolság és magasság
        dist = 18.0
        height = 4.0 + math.sin(time * 0.1) * 2.0 # Enyhe le-fel hullámzás
        
        self.orbit_angle = time * 0.2 # Forgási sebesség
        
        cam_x = math.sin(self.orbit_angle) * dist
        cam_y = -math.cos(self.orbit_angle) * dist
        
        self.cam.set_pos(cam_x, cam_y, height)
        self.cam.look_at(0, 0, 0)
        
        # 3. Eseményhorizont (Singularity) mindig nézzen a kamera felé (ha lenne rajta effekt)
        # De mivel gömb, ez nem feltétlen szükséges, hacsak nem Billboard hatást akarunk.
        
        return Task.cont

# -----------------------------------------------------------------------------
# FŐ PROGRAM INDÍTÁSA
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app = BlackHoleSim()
    app.run()