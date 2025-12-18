from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    Shader, Texture, PNMImage, 
    NodePath, Vec3, Vec4, WindowProperties,
    ColorBlendAttrib
)
import random
import math

# --- GLSL SHADEREK ---

# 1. TUNNEL & STARS SHADER: Az elsuhanó csillagokhoz és az alagúthoz
TUNNEL_SHADER_V = """
#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 texcoord;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
}
"""

TUNNEL_SHADER_F = """
#version 120
uniform sampler2D p3d_Texture0;
uniform float time;
varying vec2 texcoord;

void main() {
    vec2 uv = texcoord;
    
    // Gyors mozgás lefelé
    float speed = 4.0;
    float v_scroll = uv.y - (time * speed);
    
    // Két rétegű zaj a mélységért
    // Réteg 1: Lassabb, elmosódott háttérköd
    vec4 fog = texture2D(p3d_Texture0, vec2(uv.x, v_scroll * 0.1));
    
    // Réteg 2: Gyors, éles csillag-csíkok
    // Nagyon összenyomjuk az X tengelyen, hogy vékony vonalak legyenek
    vec4 streaks = texture2D(p3d_Texture0, vec2(uv.x * 8.0, v_scroll * 0.05));
    
    // Színvilág
    vec3 deepBlue = vec3(0.01, 0.05, 0.2);
    vec3 brightCyan = vec3(0.4, 0.7, 1.0);
    vec3 starWhite = vec3(1.0, 1.0, 1.0);
    
    // Csillagcsík logika: csak a legvilágosabb részek maradjanak meg a zajból
    float starMask = smoothstep(0.7, 0.95, streaks.r);
    vec3 starFinal = starWhite * starMask * 2.0; // 2.0 a fényerő (bloom-szerű)
    
    vec3 finalColor = mix(deepBlue, brightCyan, fog.r * 0.4);
    finalColor += starFinal;
    
    gl_FragColor = vec4(finalColor, 1.0);
}
"""

# 2. WARP BUBBLE SHADER: A hajó körüli energiamezőhöz
BUBBLE_SHADER_F = """
#version 120
uniform float time;
varying vec2 texcoord;
varying vec3 worldPos;

void main() {
    // Fresnel-szerű effekt: a gömb szélei fényesebbek
    float distanceToCenter = length(texcoord - vec2(0.5, 0.5)) * 2.0;
    float edge = pow(distanceToCenter, 3.0);
    
    // Pulzáló kék fény
    float pulse = sin(time * 3.0) * 0.2 + 0.8;
    vec3 bubbleColor = vec4(0.0, 0.5, 1.0, 1.0).rgb;
    
    // Fodrozódás effekt a felületen
    float ripples = sin(distanceToCenter * 20.0 - time * 10.0) * 0.1;
    
    float alpha = (edge + ripples) * 0.5 * pulse;
    
    gl_FragColor = vec4(bubbleColor * (edge + 0.5), alpha);
}
"""

class HyperSpaceJump(ShowBase):
    def __init__(self):
        super().__init__()

        props = WindowProperties()
        props.setTitle("EVE Online Warp Drive Effect")
        self.win.requestProperties(props)
        self.setBackgroundColor(0, 0, 0.02)

        # 1. Textúra a csillagokhoz
        self.noise_tex = self.create_noise_texture(512, 512)

        # 2. A Warp Alagút (Hosszú cső)
        self.tunnel = self.loader.loadModel("models/misc/sphere")
        self.tunnel.reparentTo(self.render)
        self.tunnel.setScale(15, 150, 15)
        self.tunnel.setPos(0, 70, 0)
        self.tunnel.setTwoSided(True)
        self.tunnel.setTexture(self.noise_tex)
        
        tunnel_sh = Shader.make(Shader.SL_GLSL, TUNNEL_SHADER_V, TUNNEL_SHADER_F)
        self.tunnel.setShader(tunnel_sh)

        # 3. A Hajó (Placeholder)
        self.ship = self.loader.loadModel("models/misc/sphere") # Később lecserélhető hajóra
        self.ship.reparentTo(self.render)
        self.ship.setScale(0.5, 1.2, 0.3)
        self.ship.setColor(0.2, 0.2, 0.2, 1.0)
        self.ship.setPos(0, 5, 0)

        # 4. Warp Buborék a hajó körül
        self.bubble = self.loader.loadModel("models/misc/sphere")
        self.bubble.reparentTo(self.ship) # A hajóhoz rögzítjük
        self.bubble.setScale(2.5, 1.5, 2.5) # Kicsit nagyobb, mint a hajó
        
        # Áttetszőség beállítása
        self.bubble.setTransparency(True)
        self.bubble.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add)) # Additív keverés a ragyogáshoz
        
        bubble_sh = Shader.make(Shader.SL_GLSL, TUNNEL_SHADER_V, BUBBLE_SHADER_F)
        self.bubble.setShader(bubble_sh)

        # Kamera
        self.disableMouse()
        self.camera.setPos(0, -15, 5)
        self.camera.lookAt(0, 20, 0)

        self.taskMgr.add(self.update_scene, "UpdateScene")

    def create_noise_texture(self, w, h):
        img = PNMImage(w, h)
        for x in range(w):
            for y in range(h):
                v = random.random()
                # Csak ritka, erős pontok kellenek a csillagokhoz
                val = pow(v, 10.0) 
                img.setGray(x, y, val)
        tex = Texture("noise")
        tex.load(img)
        tex.setWrapU(Texture.WM_repeat)
        tex.setWrapV(Texture.WM_repeat)
        tex.setMinfilter(Texture.FT_linear_mipmap_linear)
        return tex

    def update_scene(self, task):
        t = task.time
        
        # Shader paraméterek
        self.tunnel.setShaderInput("time", t)
        self.bubble.setShaderInput("time", t)

        # Kamera rázkódás
        shake = math.sin(t * 20.0) * 0.02
        self.camera.setX(shake)
        self.camera.setZ(5 + shake)
        
        # Hajó enyhe lebegése
        self.ship.setZ(math.sin(t * 2.0) * 0.1)
        self.ship.setR(math.sin(t * 1.5) * 2.0)

        return Task.cont

if __name__ == "__main__":
    app = EveWarpEffect()
    app.run()