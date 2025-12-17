from direct.showbase.ShowBase import ShowBase
from panda3d.core import Fog, TextNode
from direct.gui.OnscreenText import OnscreenText

class FogController(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # 1. Környezet betöltése
        # A Panda3D alapértelmezett környezeti modellje
        self.environ = self.loader.loadModel("models/environment")
        self.environ.reparentTo(self.render)
        self.environ.setScale(0.25, 0.25, 0.25)
        self.environ.setPos(-8, 42, 0)

        # 2. Köd (Fog) objektum létrehozása
        self.fog_color = (0.5, 0.6, 0.7) # Szürkéskék alapszín
        self.my_fog = Fog("UniversalFog")
        self.my_fog.setColor(*self.fog_color)
        
        # Kezdeti értékek a paraméterezhetőséghez
        self.density = 0.01      # Sűrűség (Exponenciális módhoz)
        self.fog_range = 100.0   # Kiterjedés (Lineáris módhoz)
        self.mode = "EXP"        # Kezdő mód: Exponenciális

        # Köd beállítások inicializálása
        self.update_fog_settings()
        
        # A köd hozzárendelése a render fához és a háttérszín beállítása
        self.render.setFog(self.my_fog)
        self.setBackgroundColor(*self.fog_color)

        # 3. Felhasználói felület (UI) megjelenítése
        self.inst_text = OnscreenText(
            text="[M]: Mód váltás (EXP / LINEAR)\n"
                 "[FEL/LE NYÍL]: Érték állítása\n"
                 "Egérrel mozoghatsz a térben",
            pos=(-1.3, 0.9), scale=0.06, fg=(1, 1, 1, 1), align=TextNode.ALeft
        )
        
        self.status_text = OnscreenText(
            text="", pos=(-1.3, -0.9), scale=0.07, 
            fg=(1, 1, 0, 1), align=TextNode.ALeft, mayChange=True
        )

        # 4. Irányítás eseménykezelőinek beállítása
        self.accept("m", self.toggle_mode)
        self.accept("arrow_up", self.adjust_value, [1.1])
        self.accept("arrow_down", self.adjust_value, [0.9])
        self.accept("arrow_up-repeat", self.adjust_value, [1.02])
        self.accept("arrow_down-repeat", self.adjust_value, [0.98])

        self.update_status()

    def update_fog_settings(self):
        """Frissíti a köd paramétereit a választott mód alapján."""
        if self.mode == "EXP":
            # Exponenciális négyzetes sűrűség (M_exponential_squared)
            # Ez adja a legszebb, fokozatos átmenetet
            self.my_fog.setMode(Fog.M_exponential_squared)
            # A sűrűség beállítása
            self.my_fog.setExpDensity(self.density)
        else:
            # Lineáris kiterjedés (M_linear)
            self.my_fog.setMode(Fog.M_linear)
            # setLinearRange(eleje, vége) méterben/egységben
            self.my_fog.setLinearRange(0, self.fog_range)

    def toggle_mode(self):
        """Vált az exponenciális sűrűség és a lineáris kiterjedés között."""
        self.mode = "LINEAR" if self.mode == "EXP" else "EXP"
        self.update_fog_settings()
        self.update_status()

    def adjust_value(self, factor):
        """Módosítja az aktuális ködparamétert (sűrűség vagy hatótáv)."""
        if self.mode == "EXP":
            self.density *= factor
            # Biztonsági korlátok a sűrűségnek
            self.density = max(0.0001, min(self.density, 0.5))
        else:
            self.fog_range *= factor
            # Biztonsági korlátok a távolságnak
            self.fog_range = max(1.0, min(self.fog_range, 5000.0))
        
        self.update_fog_settings()
        self.update_status()

    def update_status(self):
        """Frissíti a képernyőn látható állapotjelző szöveget."""
        if self.mode == "EXP":
            msg = f"Mód: EXPONENCIÁLIS\nSűrűség: {self.density:.5f}"
        else:
            msg = f"Mód: LINEÁRIS\nKiterjedés (vége): {self.fog_range:.1f} egység"
        self.status_text.setText(msg)

# Alkalmazás példányosítása és futtatása
app = FogController()
app.run()