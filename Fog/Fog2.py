from direct.showbase.ShowBase import ShowBase
from panda3d.core import Shader

class ShaderFogDemo(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # Modell
        self.environ = self.loader.loadModel("models/environment")
        self.environ.reparentTo(self.render)
        self.environ.setScale(0.25, 0.25, 0.25)
        self.environ.setPos(-8, 42, 0)
        
        # Shader betöltése
        self.fog_shader = Shader.load(Shader.SL_GLSL, 
                                      vertex="fog_vert.glsl", 
                                      fragment="fog_frag.glsl")
        self.environ.setShader(self.fog_shader)

        # Kezdeti értékek
        self.density = 0.02
        self.environ.setShaderInput("fogDensity", self.density)
        self.environ.setShaderInput("fogEnd", 100.0) # Ha lineárist használsz

        # Háttérszín igazítása a shaderben lévő ködszínhez
        self.setBackgroundColor(0.5, 0.6, 0.7)

        # Irányítás
        self.accept("arrow_up", self.update_fog, [0.005])
        self.accept("arrow_down", self.update_fog, [-0.005])
        print("Használd a FEL/LE nyilakat a sűrűség állításához!")

    def update_fog(self, change):
        self.density += change
        if self.density < 0: self.density = 0
        
        # Érték küldése a shadernek
        self.environ.setShaderInput("fogDensity", self.density)
        print(f"Új sűrűség: {self.density:.4f}")

app = ShaderFogDemo()
app.run()