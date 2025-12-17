from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Geom, GeomNode, GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    GeomPoints, NodePath, Shader, LVector3, LColor, TransparencyAttrib,
    RenderModeAttrib, AntialiasAttrib
)
import random
import math

# -----------------------------------------------------------------------------
# VERTEX SHADER - Fizikai szimuláció (Lencsehatás & Doppler)
# -----------------------------------------------------------------------------
vert_shader = """
#version 120

attribute vec4 p3d_Vertex;
attribute vec4 p3d_Color;
attribute vec2 p3d_MultiTexCoord0; // x: sebesség, y: véletlen offset

uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ProjectionMatrix;
uniform float time;

varying vec4 v_color;

void main() {
    // 1. KEPLER-MOZGÁS (Forgás)
    float speed = p3d_MultiTexCoord0.x;
    float angle = time * speed * 0.8 + p3d_MultiTexCoord0.y;
    
    float co = cos(angle);
    float si = sin(angle);
    
    vec4 pos = p3d_Vertex;
    float x = pos.x * co - pos.y * si;
    float y = pos.x * si + pos.y * co;
    pos.x = x;
    pos.y = y;

    // 2. NÉZETI TRANSZFORMÁCIÓ
    vec4 viewPos = p3d_ModelViewMatrix * pos;
    
    // 3. GRAVITÁCIÓS LENCSEHATÁS (Warping)
    vec4 holeCenterView = p3d_ModelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
    vec2 offset = viewPos.xy - holeCenterView.xy;
    float dist = length(offset);
    
    float distortion = 0.0;
    if (dist > 0.1) {
        distortion = 14.0 / (dist * dist + 0.4); 
    }
    viewPos.xy += normalize(offset) * distortion;

    // 4. DOPPLER-EFFEKTUS (Relativisztikus beaming)
    vec3 viewDir = normalize(-viewPos.xyz);
    vec3 velVector = vec3(-sin(atan(y, x)), cos(atan(y, x)), 0.0);
    float doppler = dot(normalize(velVector), viewDir);
    
    // Szín és intenzitás fokozása fehér háttérhez
    vec4 finalColor = p3d_Color;
    float beamIntensity = 1.3 + doppler * 0.9; 
    beamIntensity = pow(beamIntensity, 2.2); 
    
    // Sötétebb, telítettebb árnyalatok a széleken, hogy ne vesszenek el a fehérben
    finalColor.r *= (1.0 - doppler * 0.4);
    finalColor.b *= (1.1 + doppler * 0.5);
    
    finalColor.rgb *= beamIntensity; 
    v_color = finalColor;
    
    gl_Position = p3d_ProjectionMatrix * viewPos;
    
    // 5. DINAMIKUS PONTMÉRET (Megnövelve a ragyogáshoz)
    gl_PointSize = (8.0 + distortion * 1.0) * (40.0 / length(viewPos.xyz));
    if(gl_PointSize < 4.0) gl_PointSize = 4.0;
    if(gl_PointSize > 64.0) gl_PointSize = 64.0;
}
"""

# -----------------------------------------------------------------------------
# FRAGMENT SHADER - Ragyogás effektus
# -----------------------------------------------------------------------------
frag_shader = """
#version 120

varying vec4 v_color;

void main() {
    // Sugaras gradiens a ponton belül
    vec2 coord = gl_PointCoord - vec2(0.5);
    float r = length(coord) * 2.0; 
    
    if(r > 1.0) {
        discard;
    }
    
    // Új eloszlási görbe: erősebb belső mag, lágyabb külső aura
    float alpha = pow(1.0 - r, 1.8);
    
    // A színek telítettségét megőrizzük a széleken
    gl_FragColor = vec4(v_color.rgb, v_color.a * alpha);
}
"""

class BlackHoleSimulation(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # --- FEHÉR HÁTTÉR BEÁLLÍTÁSA ---
        self.setBackgroundColor(1, 1, 1)
        self.render.setAntialias(AntialiasAttrib.MMultisample)
        
        # Kamera pozíció
        self.disableMouse()
        self.camera.setPos(0, -70, 15)
        self.camera.lookAt(0, 0, 0)
        
        # Shader inicializálás
        self.shader = Shader.make(Shader.SL_GLSL, vert_shader, frag_shader)
        
        # 1. Akkréciós Korong (Sűrűbb pontfelhő)
        self.disk_node = self.create_accretion_disk(
            num_points=25000, # Megemelt vertexszám a folyamatos ragyogásért
            min_radius=5.0,
            max_radius=25.0
        )
        self.setup_visuals(self.disk_node)

        # 2. Foton Gyűrű (Belső izzó perem)
        self.photon_ring = self.create_photon_ring(
            num_points=5000,
            radius=4.3 
        )
        self.setup_visuals(self.photon_ring)
        
        # 3. Eseményhorizont (A központi feketeség)
        self.event_horizon = self.loader.loadModel("models/smiley")
        if self.event_horizon:
            self.event_horizon.reparentTo(self.render)
            self.event_horizon.setScale(4.0)
            self.event_horizon.setColor(0, 0, 0, 1)
            self.event_horizon.setTextureOff(1)
            self.event_horizon.setLightOff()
            self.event_horizon.setBin("fixed", 0) 
            self.event_horizon.setDepthTest(True)
            self.event_horizon.setDepthWrite(True)

        # 4. Háttér csillagok (Feketére állítva a fehér háttérhez)
        self.stars = self.create_stars(2000)
        self.stars.setRenderMode(RenderModeAttrib.MPoint, 2)
        
        # Irányítás
        self.accept("arrow_left", self.rotate_cam, [-1])
        self.accept("arrow_right", self.rotate_cam, [1])
        self.accept("arrow_up", self.zoom_cam, [1])
        self.accept("arrow_down", self.zoom_cam, [-1])
        
        self.time = 0.0
        self.taskMgr.add(self.update, "updateTask")
        
        print("FEKETE LYUK AKTÍV: Megemelt ragyogás és sűrűség fehér háttérhez.")

    def setup_visuals(self, node):
        node.setShader(self.shader)
        node.setShaderInput("time", 0.0)
        # MDual transzparencia a megfelelő rétegződéshez
        node.setTransparency(TransparencyAttrib.MAlpha)
        node.setRenderMode(RenderModeAttrib.MPoint, 1)
        node.setDepthWrite(False) 

    def create_accretion_disk(self, num_points, min_radius, max_radius):
        format = GeomVertexFormat.getV3c4t2()
        vdata = GeomVertexData('disk_data', format, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        texcoord = GeomVertexWriter(vdata, 'texcoord')
        
        for i in range(num_points):
            r_norm = random.random()
            r_norm = 1.0 - (r_norm * r_norm)
            r = min_radius + r_norm * (max_radius - min_radius)
            
            theta = random.uniform(0, 2 * math.pi)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = random.gauss(0, 0.1) * (18.0 / r) 
            
            vertex.addData3(x, y, z)
            
            # Mélyebb, telítettebb színek, hogy "ragyogjanak" a fehéren
            norm_dist = (r - min_radius) / (max_radius - min_radius)
            if norm_dist < 0.12:
                # Belső rész (Élénk Lila/Kék)
                c = (0.2, 0.4, 1.0, 0.9)
            elif norm_dist < 0.4:
                # Középső rész (Erős Narancs)
                c = (1.0, 0.3, 0.0, 0.8)
            else:
                # Külső rész (Sötétvörös)
                c = (0.6, 0.0, 0.0, 0.6)
                
            noise = random.uniform(0.9, 1.4)
            color.addData4(c[0]*noise, c[1]*noise, c[2]*noise, c[3])
            
            speed = 10.0 / math.sqrt(r)
            texcoord.addData2(speed, random.uniform(0, 100))
            
        geom = Geom(vdata)
        geom.addPrimitive(GeomPoints(Geom.UHStatic))
        node = GeomNode('disk_geom')
        node.addGeom(geom)
        return self.render.attachNewNode(node)

    def create_photon_ring(self, num_points, radius):
        format = GeomVertexFormat.getV3c4t2()
        vdata = GeomVertexData('photon_ring', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        texcoord = GeomVertexWriter(vdata, 'texcoord')
        
        for i in range(num_points):
            theta = random.uniform(0, 2 * math.pi)
            r = radius + random.uniform(-0.1, 0.1)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = random.uniform(-0.05, 0.05)
            
            vertex.addData3(x, y, z)
            # Világító türkizkék
            color.addData4(0.0, 0.6, 0.9, 1.0)
            
            speed = 15.0 / math.sqrt(r)
            texcoord.addData2(speed, random.uniform(0, 100))
            
        geom = Geom(vdata)
        geom.addPrimitive(GeomPoints(Geom.UHStatic))
        node = GeomNode('photon_geom')
        node.addGeom(geom)
        return self.render.attachNewNode(node)

    def create_stars(self, count):
        format = GeomVertexFormat.getV3c4()
        vdata = GeomVertexData('stars', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        
        for _ in range(count):
            theta = random.uniform(0, 2*math.pi)
            phi = random.uniform(0, math.pi)
            r = random.uniform(250, 400)
            
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            
            vertex.addData3(x, y, z)
            color.addData4(0.05, 0.05, 0.05, 1.0) # Majdnem fekete csillagok
                
        geom = Geom(vdata)
        geom.addPrimitive(GeomPoints(Geom.UHStatic))
        node = GeomNode('stars')
        node.addGeom(geom)
        return self.render.attachNewNode(node)

    def update(self, task):
        self.time += globalClock.getDt()
        self.disk_node.setShaderInput("time", self.time)
        self.photon_ring.setShaderInput("time", self.time)
        return task.cont

    def rotate_cam(self, dir):
        h = self.camera.getH() + dir * 1.5
        self.camera.setH(h)
        rad = math.radians(h)
        dist = 70
        self.camera.setX(math.sin(rad) * dist * -1)
        self.camera.setY(math.cos(rad) * dist * -1)
        self.camera.lookAt(0,0,0)

    def zoom_cam(self, dir):
        pos = self.camera.getPos()
        dist = pos.length()
        if dir > 0 and dist > 12:
            self.camera.setPos(pos * 0.95)
        elif dir < 0 and dist < 300:
            self.camera.setPos(pos * 1.05)

app = BlackHoleSimulation()
app.run()