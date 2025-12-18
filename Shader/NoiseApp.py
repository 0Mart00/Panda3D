from direct.showbase.ShowBase import ShowBase
from panda3d.core import Shader

# Vertex Shader szövegként
vert = """
#version 150
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
uniform mat4 p3d_ModelViewProjectionMatrix;
out vec2 texcoord;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
}
"""

# Fragment Shader szövegként
frag = """
#version 150
uniform float osg_FrameTime;
in vec2 texcoord;
out vec4 fragColor;
float rand(vec2 co){ return fract(sin(dot(co.xy, vec2(12.9898,78.233))) * 43758.5453); }
void main() {
    float angle = osg_FrameTime * 0.5;
    mat2 rot = mat2(cos(angle), -sin(angle), sin(angle), cos(angle));
    vec2 uv = (rot * (texcoord - 0.5)) * 32.0;
    float n = rand(floor(uv + osg_FrameTime * 0.1)); // Nagyon alap zaj
    fragColor = vec4(vec3(n), 1.0);
}
"""

class NoiseApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.cube = self.loader.loadModel("models/box")
        self.cube.reparentTo(self.render)
        self.cube.setPos(0, 10, 0)

        # Shader készítése közvetlenül a szövegből
        shader = Shader.make(Shader.SL_GLSL, vert, frag)
        
        if shader:
            self.cube.setShader(shader)
        else:
            print("Hiba a shader összeállításakor!")

app = GeneratedNoiseApp()
app.run()