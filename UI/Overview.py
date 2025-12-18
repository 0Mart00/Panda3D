from direct.showbase.ShowBase import ShowBase
from panda3d.core import LVector2, loadPrcFileData, TextNode
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectScrolledFrame import DirectScrolledFrame 
from direct.gui import DirectGuiGlobals as DGG
from direct.task import Task
import random
from panda3d.core import Point3

# --- KONFIGURÁCIÓ ---
WINDOW_SIZE = 1024 # Kicsit nagyobbra vettem, hogy elférjen a 3 frame
FRAME_SIZE = 500
RESIZE_TOLERANCE = 0.05 
SCREEN_LIMIT = 1.3 
MIN_FRAME_SIZE = 0.2 

TARGET_FRAME_TEXT_SCALE = 0.07 

# --- SKÁLÁZÁSI PARAMÉTEREK ---
BUTTON_BASE_HALF_SIZE = 0.1 
INTERNAL_BUTTON_FRACTION = 0.8 

# --- GÖRGŐS LISTA PARAMÉTEREK ---
SCROLL_LIST_NUM_ITEMS = 30
SCROLL_ITEM_HEIGHT = 0.1
SCROLL_LIST_FRACTION = 0.9 

# --- KAMERA BEÁLLÍTÁSOK (Kézi zoomoláshoz) ---
CAMERA_DEFAULT_Y = -10.0
CAMERA_ZOOM_STEP = 1.5
CAMERA_ZOOM_MAX_DIST = -1.0 
CAMERA_ZOOM_MIN_DIST = -50.0 
# --------------------

prc_data = f"""
window-title Dinamikus Framek & Szűrés
win-size {WINDOW_SIZE} {WINDOW_SIZE}
"""
loadPrcFileData("", prc_data)


class ManualFrameApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self) 
        self.is_dragging = False
        self.is_resizing = False 
        self.drag_offset = LVector2(0, 0) 
        self.active_frame = None 
        self.resizing_corner = None
        
        # Referenciák az elemekhez
        self.internal_button = None
        self.scroll_frame2 = None 
        self.scroll_frame3 = None 
        self.filter_buttons = [] # A szűrő gombok listája
        
        self.frame1 = None 
        self.frame2 = None 
        self.frame3 = None
        self.frame_list = []
        
        # Adatok a 3-as framehez (hogy tudjuk szűrni)
        self.frame3_data = [] 
        self.current_filter = "Mind"

        self.default_cam_zoom_speed = 1.0 
        base.camera.setY(CAMERA_DEFAULT_Y)
        
        self._generate_data() # Adatok generálása a 3-as framehez
        self._setup_panels()
        self._setup_drag_events() 
        self._setup_scroll_events()

    def _generate_data(self):
        """Generálunk adatokat a Frame 3-hoz (színkódokkal)."""
        for i in range(30):
            # Véletlenszerűen Piros vagy Zöld típus
            type_tag = "Piros" if random.random() > 0.5 else "Zöld"
            color = (1, 0.5, 0.5, 1) if type_tag == "Piros" else (0.5, 1, 0.5, 1)
            self.frame3_data.append({
                "id": i,
                "text": f"Adat {i+1} ({type_tag})",
                "type": type_tag,
                "color": color
            })

    def _internal_button_click(self):
        self.status_text.setText("Belső Gomb Megnyomva (Frame 1)!")

    def _stop_event_propagation(self, event):
        """Megakadályozza, hogy a gombnyomás Drag/Resize eseményt indítson."""
        return event.stop()
        
    def _setup_panels(self):
        self.status_text = OnscreenText(
            text="Húzd a Frame-eket, használd a görgőt, vagy szűrj a Frame 3-ban!",
            pos=(0, 0.9), 
            scale=0.06, 
            fg=(1, 1, 1, 1), 
            mayChange=True
        )
        
        panel_half_scale = 0.25 # Alapméret
        initial_width = panel_half_scale * 2
        initial_height = panel_half_scale * 2
        
        # --- FRAME 1 (Kék - Skálázós gomb) ---
        self.frame1 = DirectFrame(
            frameColor=(0.1, 0.1, 0.8, 0.9),
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(-0.5, 0, 0.2), 
            text="Frame 1\n(Skálázós Gomb)", 
            text_scale=0.05, 
            text_pos=(0, 0.25)
        )
        self.frame_list.append(self.frame1)

        self.internal_button = DirectButton(
            parent=self.frame1, 
            frameColor=(0.1, 0.8, 0.1, 1),
            frameSize=(-BUTTON_BASE_HALF_SIZE, BUTTON_BASE_HALF_SIZE, 
                        -BUTTON_BASE_HALF_SIZE, BUTTON_BASE_HALF_SIZE), 
            pos=(0, 0, 0), 
            text="Auto Gomb",
            command=self._internal_button_click,
            scale=(1, 1, 1)
        )
        self.internal_button.bind('press', self._stop_event_propagation)
        self._update_button_scale(width=initial_width, height=initial_height)
        
        # --- FRAME 2 (Narancs - Görgethető Lista) ---
        self.frame2 = DirectFrame(
            frameColor=(0.8, 0.5, 0.1, 0.9), 
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(0.0, 0, -0.4), 
            text="Frame 2\n(Sima Lista)", 
            text_scale=0.05,
            text_pos=(0, 0.25)
        )
        self.frame_list.append(self.frame2)

        canvas_height = SCROLL_LIST_NUM_ITEMS * (SCROLL_ITEM_HEIGHT + 0.01)
        self.scroll_frame2 = DirectScrolledFrame(
            parent=self.frame2,
            frameSize=(-0.2, 0.2, -0.2, 0.2), 
            canvasSize=(-0.15, 0.15, -canvas_height, 0),
            scrollBarWidth=0.04,
            frameColor=(0.3, 0.3, 0.3, 0.8),
            manageScrollBars=True,
            autoHideScrollBars=False
        )
        # Elemek Frame 2-be
        for i in range(SCROLL_LIST_NUM_ITEMS):
            color = (random.random(), random.random(), random.random(), 1)
            y_pos = -0.05 - (i * (SCROLL_ITEM_HEIGHT + 0.01))
            DirectButton(
                text=f"F2 Elem #{i + 1}",
                text_scale=0.04,
                text_align=TextNode.ALeft,
                frameColor=color,
                frameSize=(-0.2, 0.2, -0.04, 0.04),
                pos=(0, 0, y_pos),
                parent=self.scroll_frame2.getCanvas(),
                command=lambda i=i: self.status_text.setText(f"Frame 2 Elem: {i+1}")
            ).bind('press', self._stop_event_propagation)

        self._update_frame2_content(initial_width, initial_height)

        # --- FRAME 3 (Szürkéskék - Szűrhető Lista) ---
        self.frame3 = DirectFrame(
            frameColor=(0.2, 0.3, 0.4, 0.95),
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(0.5, 0, 0.2),
            text="Frame 3 Overview",
            text_scale=0.05,
            text_fg=(1,1,1,1),
            text_pos=(0, 0.42), # Cím egészen fent
            text_align=TextNode.ACenter
        )
        self.frame_list.append(self.frame3)
        
        # Szűrő gombok létrehozása Frame 3-hoz
        filter_opts = ["Mind", "Piros", "Zöld"]
        for idx, lbl in enumerate(filter_opts):
            btn = DirectButton(
                parent=self.frame3,
                text=lbl,
                text_scale=0.04,
                frameSize=(-0.12, 0.12, -0.03, 0.03), # Fix gomb méret
                pos=(0, 0, 0), # Később pozicionáljuk
                command=self._apply_filter,
                extraArgs=[lbl]
            )
            btn.bind('press', self._stop_event_propagation)
            self.filter_buttons.append(btn)
            
        # Scroll frame Frame 3-hoz
        self.scroll_frame3 = DirectScrolledFrame(
            parent=self.frame3,
            frameSize=(-0.2, 0.2, -0.2, 0.2),
            canvasSize=(-0.2, 0.2, -1, 0), # Dinamikus lesz
            scrollBarWidth=0.04,
            frameColor=(0.1, 0.15, 0.2, 1),
            manageScrollBars=True,
            autoHideScrollBars=False
        )
        
        # Inicializáljuk a tartalmat és a méretet
        self._apply_filter("Mind") # Ez feltölti a listát
        self._update_frame3_content(initial_width, initial_height)


    # --- SZŰRÉSI LOGIKA (Frame 3) ---
    def _apply_filter(self, filter_type):
        self.current_filter = filter_type
        self.status_text.setText(f"Szűrő alkalmazva: {filter_type}")
        
        # 1. Töröljük a jelenlegi elemeket a vászonról
        for child in self.scroll_frame3.getCanvas().getChildren():
            child.removeNode()
            
        # 2. Kiválogatjuk az adatokat
        filtered_data = []
        for item in self.frame3_data:
            if filter_type == "Mind" or item["type"] == filter_type:
                filtered_data.append(item)
                
        # 3. Újraépítjük a listát
        item_h = 0.08
        spacing = 0.01
        current_y = -0.05
        
        for item in filtered_data:
            btn = DirectButton(
                parent=self.scroll_frame3.getCanvas(),
                text=item["text"],
                text_scale=0.04,
                text_fg=(0,0,0,1),
                frameColor=item["color"],
                frameSize=(-0.25, 0.25, -item_h/2, item_h/2),
                pos=(0, 0, current_y),
                command=lambda t=item["text"]: self.status_text.setText(f"Kiválasztva: {t}")
            )
            btn.bind('press', self._stop_event_propagation) # Fontos a drag tiltásához
            current_y -= (item_h + spacing)
            
        # 4. Beállítjuk a vászon méretét az új tartalomhoz
        canvas_h = abs(current_y)
        self.scroll_frame3['canvasSize'] = (-0.28, 0.28, -canvas_h, 0)

    # --- MÉRETEZÉSI LOGIKA ---

    def _update_button_scale(self, width, height):
        # Frame 1 logika
        if not self.internal_button: return
        target_width = width * INTERNAL_BUTTON_FRACTION
        target_height = height * INTERNAL_BUTTON_FRACTION
        base_sz = BUTTON_BASE_HALF_SIZE * 2
        self.internal_button.setScale(target_width / base_sz, 1, target_height / base_sz) 
        ts = TARGET_FRAME_TEXT_SCALE 
        self.internal_button['text_scale'] = (ts / (target_width/base_sz), ts / (target_height/base_sz))

    def _update_frame2_content(self, width, height):
        # Frame 2 logika (Sima lista)
        if not self.scroll_frame2: return
        
        # Margók
        margin = 0.05
        # A rendelkezésre álló hely: teljes szélesség mínusz margó, magasság kicsit kevesebb a fejléc miatt
        list_width = width - (margin * 2)
        list_height = height - (margin * 3) # Fent nagyobb hely a címnek
        
        # FrameSize beállítása közvetlenül (nem scale, hogy a scrollbar ne torzuljon annyira)
        # Bár a DirectScrolledFrame scale-ezése egyszerűbb a tartalom szempontjából
        
        # Itt maradunk a scale megoldásnál a példa kedvéért, de pozícionáljuk
        base_w, base_h = 0.4, 0.4 # Kezdeti méret amire a scale vonatkozik
        
        # A scroll frame méretét igazítjuk
        # A Z pozíciót lejjebb toljuk, mert a cím fent van
        self.scroll_frame2.setScale(list_width / base_w * 0.4, 1, list_height / base_h * 0.4)
        self.scroll_frame2.setZ( - (height/2) + (list_height/2) - margin ) # Alulra igazítva, kis margóval


    def _update_frame3_content(self, width, height):
        """
        Frame 3 elrendezés frissítése:
        - Cím (automatikus a DirectFrame-től)
        - Szűrő sáv (fix magasság, de szélességben igazodik)
        - Scroll lista (maradék hely kitöltése)
        """
        if not self.scroll_frame3: return
        
        half_w = width / 2
        half_h = height / 2
        
        # 1. Szűrő gombok elhelyezése
        # A gombok legyenek a cím alatt.
        # Tegyük fel, hogy a cím kb a felső 15%-ot foglalja el.
        filter_y = half_h - 0.15 # Egy kicsit lejjebb a tetőtől
        
        # Gombok elosztása vízszintesen
        btn_spacing = width / 3.5
        start_x = -btn_spacing
        
        for i, btn in enumerate(self.filter_buttons):
            # A gombokat nem torzítjuk (scale), csak pozícionáljuk
            btn.setPos(start_x + (i * btn_spacing), 0, filter_y)
            # Opcionális: ha nagyon kicsi a frame, a gombokat kicsinyíthetjük
            btn_scale = min(1.0, width * 1.5) 
            btn.setScale(btn_scale)

        # 2. Scroll Frame méretezése
        # A szűrő gombok alatt kezdődik és az aljáig tart
        filter_area_height = 0.25 # Hely a gomboknak
        list_top = half_h - filter_area_height
        list_bottom = -half_h + 0.05 # Alsó margó
        
        list_height = list_top - list_bottom
        list_width = width - 0.1 # Oldalsó margók
        
        # A DirectScrolledFrame frameSize-át állítjuk be közvetlenül, nem a Scale-t.
        # Így a görgetősáv fix szélességű marad, nem nyúlik meg.
        
        sf_half_w = list_width / 2
        sf_half_h = list_height / 2
        
        self.scroll_frame3['frameSize'] = (-sf_half_w, sf_half_w, -sf_half_h, sf_half_h)
        
        # A tartalom gombok szélességét is igazíthatjuk a vászonhoz
        # (Ez egy kicsit bonyolultabb, most csak a vászon szélességét állítjuk)
        current_canvas = self.scroll_frame3['canvasSize']
        # Canvas szélességét igazítjuk a látható kerethez (kis ráhagyással a scrollbarnak)
        self.scroll_frame3['canvasSize'] = (-(sf_half_w-0.05), (sf_half_w-0.05), current_canvas[2], current_canvas[3])
        
        # Pozíció: A lista középpontja
        center_y = list_bottom + sf_half_h
        self.scroll_frame3.setPos(0, 0, center_y)


    # --- GÖRGETÉS ÉS INTERAKCIÓ ---

    def _setup_scroll_events(self):
        self.accept('wheel_up', self._on_scroll, [-1]) 
        self.accept('wheel_down', self._on_scroll, [1])

    def _setup_drag_events(self):
        """Egér események beállítása a húzáshoz és átméretezéshez."""
        self.accept('mouse1', self.start_interaction_check) 
        self.accept('mouse1-up', self.stop_interaction)
        self.taskMgr.add(self.interaction_task, 'interaction_task')

    def _get_hovered_scroll_frame(self):
        """Megnézi, hogy melyik görgethető lista felett van az egér."""
        if not base.mouseWatcherNode.hasMouse(): return None
        mw = base.mouseWatcherNode
        m_pos = Point3(mw.getMouseX(), 0, mw.getMouseY())

        # Lista a potenciális scroll frame-ekről
        candidates = [self.scroll_frame2, self.scroll_frame3]
        
        for sf in candidates:
            if sf is None: continue
            
            # Transzformálás a scroll frame lokális terébe
            local = sf.getRelativePoint(render2d, m_pos)
            f_size = sf['frameSize']
            
            if f_size[0] <= local.x <= f_size[1] and f_size[2] <= local.z <= f_size[3]:
                return sf
        
        return None

    def _on_scroll(self, direction):
        if self.active_frame is not None: return

        target_sf = self._get_hovered_scroll_frame()
        
        if target_sf:
            # Görgetés a talált listán
            scroll_bar = target_sf.verticalScroll
            if scroll_bar and not scroll_bar.isHidden():
                scroll_step = 0.05 * direction
                current_val = scroll_bar['value']
                # Fontos: a scrollbar értéke 0 és 1 között van általában, 
                # de a DirectScrolledFrame néha furcsán skálázza.
                # A range property megmondja a határokat.
                r = scroll_bar['range']
                new_val = max(r[0], min(r[1], current_val + scroll_step))
                scroll_bar['value'] = new_val
        else:
            # Kamera zoom, ha nem lista felett vagyunk
            current_y = base.camera.getY()
            # direction: -1 (up/közelít), 1 (down/távolít)
            if direction < 0: 
                base.camera.setY(min(CAMERA_ZOOM_MAX_DIST, current_y + CAMERA_ZOOM_STEP))
            else:
                base.camera.setY(max(CAMERA_ZOOM_MIN_DIST, current_y - CAMERA_ZOOM_STEP))

    # --- INTERAKCIÓS ELLENŐRZÉS (DRAG/RESIZE) ---

    def _check_interaction_area(self, mouse_x, mouse_y, frame):
        frame_pos = frame.getPos()
        min_x, max_x, min_z, max_z = frame['frameSize']
        
        # Abszolút határok
        abs_x1 = frame_pos.getX() + min_x
        abs_x2 = frame_pos.getX() + max_x
        abs_z1 = frame_pos.getZ() + min_z
        abs_z2 = frame_pos.getZ() + max_z
        
        if not (abs_x1 <= mouse_x <= abs_x2 and abs_z1 <= mouse_y <= abs_z2):
            return None, None
            
        t = RESIZE_TOLERANCE
        is_r = abs(mouse_x - abs_x2) < t
        is_l = abs(mouse_x - abs_x1) < t
        is_t = abs(mouse_y - abs_z2) < t
        is_b = abs(mouse_y - abs_z1) < t
        
        corner = None
        if is_r and is_t: corner = 'tr'
        elif is_l and is_t: corner = 'tl'
        elif is_r and is_b: corner = 'br'
        elif is_l and is_b: corner = 'bl'
        
        if corner: return 'resize', corner
        return 'drag', None

    def start_interaction_check(self):
        if not base.mouseWatcherNode.hasMouse(): return
        m = base.mouseWatcherNode.getMouse()
        mx, my = m.getX(), m.getY()
        
        self.is_dragging = False
        self.is_resizing = False
        self.active_frame = None

        # Fordított sorrend, hogy a legfelsőt (utoljára rajzoltat) találjuk meg először
        for frame in reversed(self.frame_list):
            action, corner = self._check_interaction_area(mx, my, frame)
            
            if action:
                self.active_frame = frame
                # Előtérbe hozás
                self.frame_list.remove(frame)
                self.frame_list.append(frame)
                frame.reparentTo(base.aspect2d)
                
                if action == 'resize':
                    self.is_resizing = True
                    self.resizing_corner = corner
                    self.active_frame['frameColor'] = (0.8, 0.1, 0.8, 0.9)
                elif action == 'drag':
                    self.is_dragging = True
                    p = frame.getPos()
                    self.drag_offset = LVector2(p.getX() - mx, p.getZ() - my)
                    self.active_frame['frameColor'] = (0.0, 0.8, 0.0, 0.9)
                
                self.status_text.setText(f"{'MÉRETEZÉS' if self.is_resizing else 'HÚZÁS'}: {frame['text']}")
                
                # Azonnali frissítés, hogy inicializáljuk a méreteket kattintáskor
                self._refresh_active_frame_content()
                return

        self.status_text.setText("ÜRES TERÜLET")
        self.taskMgr.doMethodLater(1.5, self.reset_status_text, 'reset_task')

    def _refresh_active_frame_content(self):
        """Segédfüggvény a tartalom frissítéséhez az aktív framen."""
        if not self.active_frame: return
        
        fs = self.active_frame['frameSize']
        w = fs[1] - fs[0]
        h = fs[3] - fs[2]
        
        if self.active_frame == self.frame1:
            self._update_button_scale(w, h)
        elif self.active_frame == self.frame2:
            self._update_frame2_content(w, h)
        elif self.active_frame == self.frame3:
            self._update_frame3_content(w, h)

    def interaction_task(self, task):
        if not self.active_frame or not base.mouseWatcherNode.hasMouse():
            return Task.cont
            
        m = base.mouseWatcherNode.getMouse()
        mx, my = m.getX(), m.getY()
        frame = self.active_frame
        fs = frame['frameSize'] # (minx, maxx, minz, maxz)
        
        if self.is_dragging:
            nx = mx + self.drag_offset.getX()
            ny = my + self.drag_offset.getY()
            # Képernyőhatárok (egyszerűsítve)
            hw, hh = fs[1], fs[3]
            nx = max(-SCREEN_LIMIT+hw, min(SCREEN_LIMIT-hw, nx))
            ny = max(-SCREEN_LIMIT+hh, min(SCREEN_LIMIT-hh, ny))
            frame.setPos(nx, 0, ny)
            
        elif self.is_resizing:
            cur_x, cur_y = frame.getX(), frame.getZ()
            # Jelenlegi határok abszolút pozícióban
            abs_min_x = cur_x + fs[0]
            abs_max_x = cur_x + fs[1]
            abs_min_y = cur_y + fs[2]
            abs_max_y = cur_y + fs[3]
            
            # Melyik oldalt mozgatjuk?
            if 'r' in self.resizing_corner: abs_max_x = mx
            elif 'l' in self.resizing_corner: abs_min_x = mx
            if 't' in self.resizing_corner: abs_max_y = my
            elif 'b' in self.resizing_corner: abs_min_y = my
            
            # Limitek
            abs_min_x = max(-SCREEN_LIMIT, abs_min_x)
            abs_max_x = min(SCREEN_LIMIT, abs_max_x)
            abs_min_y = max(-SCREEN_LIMIT, abs_min_y)
            abs_max_y = min(SCREEN_LIMIT, abs_max_y)

            w = max(MIN_FRAME_SIZE, abs_max_x - abs_min_x)
            h = max(MIN_FRAME_SIZE, abs_max_y - abs_min_y)

            # Ha túl kicsi, korrigáljuk a határokat
            if w <= MIN_FRAME_SIZE:
                if 'l' in self.resizing_corner: abs_min_x = abs_max_x - MIN_FRAME_SIZE
                else: abs_max_x = abs_min_x + MIN_FRAME_SIZE
                w = MIN_FRAME_SIZE
            if h <= MIN_FRAME_SIZE:
                if 'b' in self.resizing_corner: abs_min_y = abs_max_y - MIN_FRAME_SIZE
                else: abs_max_y = abs_min_y + MIN_FRAME_SIZE
                h = MIN_FRAME_SIZE

            # Új középpont és méret
            new_cx = abs_min_x + w/2
            new_cy = abs_min_y + h/2
            
            frame['frameSize'] = (-w/2, w/2, -h/2, h/2)
            frame.setPos(new_cx, 0, new_cy)
            
            # Tartalom frissítése
            self._refresh_active_frame_content()
            self.status_text.setText(f"MÉRETEZÉS: W:{w:.2f}, H:{h:.2f}")

        return Task.cont

    def stop_interaction(self):
        if self.active_frame:
            # Színek visszaállítása
            if self.active_frame == self.frame1: c = (0.1, 0.1, 0.8, 0.9)
            elif self.active_frame == self.frame2: c = (0.8, 0.5, 0.1, 0.9)
            elif self.active_frame == self.frame3: c = (0.2, 0.3, 0.4, 0.95)
            self.active_frame['frameColor'] = c
            
            self.is_dragging = False
            self.is_resizing = False
            self.active_frame = None
            self.resizing_corner = None
            self.taskMgr.doMethodLater(1.5, self.reset_status_text, 'reset_task')

    def reset_status_text(self, task):
        self.status_text.setText("Kész. Válassz egy másik műveletet!")
        return task.done
    

if __name__ == '__main__':
    app = ManualFrameApp()
    app.run()