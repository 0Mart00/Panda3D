from direct.showbase.ShowBase import ShowBase
from panda3d.core import LVector2, loadPrcFileData, TextNode
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
# DirectScrolledList helyett DirectScrolledFrame-et importálunk
from direct.gui.DirectScrolledFrame import DirectScrolledFrame 
from direct.gui import DirectGuiGlobals as DGG
from direct.task import Task
import random
from panda3d.core import Point3

# --- KONFIGURÁCIÓ ---
WINDOW_SIZE = 750
FRAME_SIZE = 500
RESIZE_TOLERANCE = 0.05 
SCREEN_LIMIT = 1.0 
MIN_FRAME_SIZE = 0.05 

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
# Zoom limiterek (a kamera Y pozíciója negatív, ahol a 0 a legközelebbi)
CAMERA_ZOOM_MAX_DIST = -1.0  # Legközelebb
CAMERA_ZOOM_MIN_DIST = -50.0 # Legtávolabb
# --------------------

prc_data = f"""
window-title Dinamikus Gomb & ScrolledList Görgetéssel
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
        self.internal_button = None
        self.scroll_frame = None # scroll_list helyett scroll_frame
        self.frame1 = None 
        self.frame2 = None 
        self.frame_list = []
        
        self.default_cam_zoom_speed = 1.0 
        
        # Kezdeti kamera pozíció beállítása (a manuális zoomhoz)
        base.camera.setY(CAMERA_DEFAULT_Y)
        
        self._setup_panels()
        self._setup_drag_events() 
        self._setup_scroll_events()

    def _internal_button_click(self):
        self.status_text.setText("Belső Gomb Megnyomva!")

    def _internal_button_stop_event(self, event):
        # Megakadályozza, hogy a Drag/Resize eseményt is kiváltsa a gombnyomás
        return event.stop()
        
    def _setup_panels(self):
        self.status_text = OnscreenText(
            text="Húzd a Frame-et, vagy használd a görgőt a listán!",
            pos=(0, 0.9), 
            scale=0.07, 
            fg=(1, 1, 1, 1), 
            mayChange=True
        )
        
        panel_half_scale = FRAME_SIZE / WINDOW_SIZE / 2 
        initial_width = panel_half_scale * 2
        initial_height = panel_half_scale * 2
        
        # --- FRAME 1 (Kék) ---
        self.frame1 = DirectFrame(
            frameColor=(0.1, 0.1, 0.8, 0.9),
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(-0.2, 0, -0.2), 
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
        # Ez az esemény megakadályozza, hogy a DirectButton kattintásával a frame húzása is elinduljon
        self.internal_button.bind('press', self._internal_button_stop_event)
        self._update_button_scale(width=initial_width, height=initial_height)
        
        # --- FRAME 2 (Narancs - Görgethető Lista) ---
        self.frame2 = DirectFrame(
            frameColor=(0.8, 0.5, 0.1, 0.9), 
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(0.3, 0, 0.3), 
            text="Frame 2\n(Görgess itt!)", 
            text_scale=0.05,
            text_pos=(0, 0.25)
        )
        self.frame_list.append(self.frame2)

        # --- DirectScrolledFrame LÉTREHOZÁSA ---
        
        # Kiszámoljuk a vászon (canvas) méretét az elemek alapján
        canvas_height = SCROLL_LIST_NUM_ITEMS * (SCROLL_ITEM_HEIGHT + 0.01) # Kis térköz
        
        self.scroll_frame = DirectScrolledFrame(
            parent=self.frame2,
            frameSize=(-0.4, 0.4, -0.4, 0.4), # Kezdeti méret
            canvasSize=(-0.3, 0.3, -canvas_height, 0), # A vászon mérete (lefelé nyúlik)
            scrollBarWidth=0.04,
            frameColor=(0.3, 0.3, 0.3, 0.8),
            pos=(0, 0, -0.1),
            scale=(1, 1, 1),
            manageScrollBars=True, # Fontos: engedjük, hogy kezelje a scrollbarokat
            autoHideScrollBars=False # Mindig mutassa a görgetősávot, ha kell
        )
        
        # Elemek hozzáadása a vászonhoz (getCanvas())
        for i in range(SCROLL_LIST_NUM_ITEMS):
            color = (random.random(), random.random(), random.random(), 1)
            # Y pozíció: fentről lefelé haladva
            y_pos = -0.05 - (i * (SCROLL_ITEM_HEIGHT + 0.01))
            
            btn = DirectButton(
                text=f"Lista Elem #{i + 1}",
                text_scale=0.05,
                text_align=TextNode.ALeft,
                text_pos=(-0.1, -0.015),
                frameColor=color,
                frameSize=(-0.3, 0.3, -SCROLL_ITEM_HEIGHT/2, SCROLL_ITEM_HEIGHT/2),
                pos=(0, 0, y_pos),
                relief=1,
                parent=self.scroll_frame.getCanvas(), # FONTOS: a vászonhoz adjuk!
                command=lambda i=i: self.status_text.setText(f"Elem: {i+1} kiválasztva")
            )
            # A gomb ne zavarja be a görgetést, ha "üres" helyre kattintunk a gombon,
            # de mivel a DirectButton elfogja az eseményeket, a görgőzés globálisan van kezelve.

        self._update_frame2_content(initial_width, initial_height)

    # --- GÖRGETŐS FUNKCIÓK ---

    def _setup_scroll_events(self):
        # Globalis görgetés események
        # A handle_scroll logika alapján, itt paramétereket adunk át
        self.accept('wheel_up', self._on_scroll, [-0.05]) # Felfelé csökkentjük az értéket (felfelé megy a tartalom)
        self.accept('wheel_down', self._on_scroll, [0.05]) # Lefelé növeljük

    def _is_cursor_strictly_inside(self, frame):
        """Eldönti, hogy a kurzor egy frame-en belül van-e (frameSize alapján)."""
        if not base.mouseWatcherNode.hasMouse():
            return False

        mw = base.mouseWatcherNode
        mouse_render2d = Point3(mw.getMouseX(), 0, mw.getMouseY())

        # render2d → frame lokális tér
        local = frame.getRelativePoint(render2d, mouse_render2d)

        min_x, max_x, min_z, max_z = frame['frameSize']
        return min_x <= local.x <= max_x and min_z <= local.z <= max_z
    
    def _is_mouse_over_scroll_frame(self):
        """True, ha az egér a scroll frame látható területe felett van (megbízható ellenőrzés)."""
        if not base.mouseWatcherNode.hasMouse():
            return False

        mw = base.mouseWatcherNode
        # Egér pozíció render2d koordinátákban
        mouse_render2d = Point3(mw.getMouseX(), 0, mw.getMouseY())

        # A scroll_frame lokális terébe transzformálunk
        # Ez kezeli a parent (frame2) mozgatását és skálázását is!
        local = self.scroll_frame.getRelativePoint(render2d, mouse_render2d)

        # A DirectScrolledFrame frameSize-a a látható ablak mérete
        # A scroll_frame dictionary-ből olvassuk ki a pontos határokat
        min_x, max_x, min_z, max_z = self.scroll_frame['frameSize']
        
        return min_x <= local.x <= max_x and min_z <= local.z <= max_z

    def _on_scroll(self, amount):
        """Közös görgető függvény, ami a mintakód logikáját követi."""
        if self.active_frame is not None:
            return
            
        # Ha a ScrollFrame felett vagyunk, akkor a menüt görgetjük
        if self._is_mouse_over_scroll_frame():
            # A DirectScrolledFrame görgető sávja
            scroll_bar = self.scroll_frame.verticalScroll
            
            # Ellenőrizzük, hogy létezik-e és nem rejtett
            if scroll_bar and not scroll_bar.isHidden():
                current_val = scroll_bar['value']
                
                # A scrollbar range-ét lekérdezzük (alapértelmezett: 0-1, de biztosra megyünk)
                scroll_range = scroll_bar['range']
                min_val = scroll_range[0]
                max_val = scroll_range[1]
                
                # Kiszámoljuk az új értéket és korlátozzuk a range-en belül
                new_val = max(min_val, min(max_val, current_val + amount))
                
                # Beállítjuk az új értéket
                scroll_bar['value'] = new_val
        else:
            # Egyébként a kamerát zoomoljuk (ahogy az eredeti kódban is volt)
            # Itt az 'amount' iránya fordított a kamera Y-hoz képest a scrollbarhoz viszonyítva
            
            # Negatív amount (wheel_up) -> közelebb megyünk
            # Pozitív amount (wheel_down) -> távolodunk
            
            current_y = base.camera.getY()
            if amount < 0: # Wheel Up
                base.camera.setY(min(CAMERA_ZOOM_MAX_DIST, current_y + CAMERA_ZOOM_STEP))
            else: # Wheel Down
                base.camera.setY(max(CAMERA_ZOOM_MIN_DIST, current_y - CAMERA_ZOOM_STEP))

    def _on_scroll_up(self):
        # Kompatibilitás miatt meghagyva, de az _on_scroll kezeli
        self._on_scroll(-0.05)

    def _on_scroll_down(self):
         # Kompatibilitás miatt meghagyva, de az _on_scroll kezeli
        self._on_scroll(0.05)


    # Az alábbi _update_button_scale a Frame 1 méretezését kezeli
    def _update_button_scale(self, width, height):
        if not self.internal_button:
            return

        target_width = width * INTERNAL_BUTTON_FRACTION
        target_height = height * INTERNAL_BUTTON_FRACTION

        base_width = BUTTON_BASE_HALF_SIZE * 2
        base_height = BUTTON_BASE_HALF_SIZE * 2

        scale_x = target_width / base_width
        scale_y = target_height / base_height

        self.internal_button.setScale(scale_x, 1, scale_y) 

        visual_size = TARGET_FRAME_TEXT_SCALE 
        ts_x = visual_size / scale_x
        ts_y = visual_size / scale_y

        self.internal_button['text_scale'] = (ts_x, ts_y)

    # Az alábbi _update_frame2_content a Frame 2 tartalmának (scroll frame) méretezését és pozícióját kezeli
    def _update_frame2_content(self, width, height):
        if not self.scroll_frame:
            return
        
        target_width = width * SCROLL_LIST_FRACTION
        target_height = height * SCROLL_LIST_FRACTION

        # Az alap méretek, amihez viszonyítunk
        base_scroll_width = 0.8 
        base_scroll_height = 0.8 
        
        scale_x = target_width / base_scroll_width
        scale_y = target_height / base_scroll_height
        
        self.scroll_frame.setScale(scale_x, 1, scale_y)
        
        # Új pozíció beállítása
        # A Z pozíció korrekciója, hogy a frame belsejében maradjon
        Z_target = -0.1 * scale_y 
        self.scroll_frame.setZ(Z_target)


    def _check_interaction_area(self, mouse_x_norm, mouse_y_norm, frame):
        """A korábbi függvény a méretezéshez/húzáshoz (változatlan)"""
        frame_pos = frame.getPos()
        frame_center_x = frame_pos.getX()
        frame_center_y = frame_pos.getZ()
        
        min_x_size, max_x_size, min_y_size, max_y_size = frame['frameSize']
        
        min_x_abs = frame_center_x + min_x_size
        max_x_abs = frame_center_x + max_x_size
        min_y_abs = frame_center_y + min_y_size
        max_y_abs = frame_center_y + max_y_size
        
        tolerance = RESIZE_TOLERANCE 
        
        is_inside = (min_x_abs <= mouse_x_norm <= max_x_abs and 
                      min_y_abs <= mouse_y_norm <= max_y_abs)

        if not is_inside: return None, None
            
        is_right = (max_x_abs - tolerance) < mouse_x_norm < (max_x_abs + tolerance)
        is_left  = (min_x_abs - tolerance) < mouse_x_norm < (min_x_abs + tolerance)
        is_top   = (max_y_abs - tolerance) < mouse_y_norm < (max_y_abs + tolerance)
        is_bottom= (min_y_abs - tolerance) < mouse_y_norm < (min_y_abs + tolerance) 
        
        corner = None
        if is_right and is_top: corner = 'tr'
        elif is_left and is_top: corner = 'tl'
        elif is_right and is_bottom: corner = 'br'
        elif is_left and is_bottom: corner = 'bl'
        
        if corner: return 'resize', corner
            
        return 'drag', None

    def start_interaction_check(self):
        if not base.mouseWatcherNode.hasMouse(): return
        mouse_norm = base.mouseWatcherNode.getMouse()
        mouse_x = mouse_norm.getX()
        mouse_y = mouse_norm.getY()
        
        self.is_dragging = False
        self.is_resizing = False
        self.active_frame = None

        # Hátulról előre haladva ellenőrizzük a frame-eket
        for frame in reversed(self.frame_list):
            action, corner = self._check_interaction_area(mouse_x, mouse_y, frame)
            
            if action:
                self.active_frame = frame
                
                # A legutolsó interakcióba lépő frame kerüljön a lista végére (Z-index/rajzolási sorrend)
                self.frame_list.remove(frame)
                self.frame_list.append(frame)
                frame.reparentTo(base.aspect2d) # Z-index biztosítása
                
                if action == 'resize':
                    self.is_resizing = True
                    self.resizing_corner = corner
                    # Átmeneti színváltozás
                    self.active_frame['frameColor'] = (0.8, 0.1, 0.8, 0.9) 
                        
                elif action == 'drag':
                    self.is_dragging = True
                    frame_pos = frame.getPos()
                    self.drag_offset = LVector2(frame_pos.getX() - mouse_x, frame_pos.getZ() - mouse_y)
                    # Átmeneti színváltozás
                    self.active_frame['frameColor'] = (0.0, 0.8, 0.0, 0.9) 
                
                self.status_text.setText(f"{'MÉRETEZÉS' if self.is_resizing else 'HÚZÁS'}")
                
                # Frissítsük a belső tartalmat az első interakciókor is.
                current_size = frame['frameSize']
                w = current_size[1] - current_size[0]
                h = current_size[3] - current_size[2]
                
                if frame == self.frame1:
                    self._update_button_scale(w, h)
                elif frame == self.frame2:
                    self._update_frame2_content(w, h)

                return # Elhagyjuk a ciklust, amint találtunk egy interakciót

        self.status_text.setText("ÜRES TERÜLET")
        self.taskMgr.doMethodLater(1.5, self.reset_status_text, 'reset_task')

    def _setup_drag_events(self):
        self.accept('mouse1', self.start_interaction_check) 
        self.accept('mouse1-up', self.stop_interaction)
        self.taskMgr.add(self.interaction_task, 'interaction_task')


    def interaction_task(self, task):
        if not self.active_frame or not base.mouseWatcherNode.hasMouse():
            return Task.cont
            
        mouse_norm = base.mouseWatcherNode.getMouse()
        mouse_x = mouse_norm.getX()
        mouse_y = mouse_norm.getY()
        frame = self.active_frame
        
        min_x_size, max_x_size, min_y_size, max_y_size = frame['frameSize']
        
        if self.is_dragging:
            potential_new_x = mouse_x + self.drag_offset.getX()
            potential_new_y = mouse_y + self.drag_offset.getY()
            
            half_width = max_x_size
            half_height = max_y_size

            # Korlátozás a képernyő határaihoz
            new_x = max(-SCREEN_LIMIT + half_width, min(SCREEN_LIMIT - half_width, potential_new_x))
            new_y = max(-SCREEN_LIMIT + half_height, min(SCREEN_LIMIT - half_height, potential_new_y))

            frame.setPos(new_x, 0, new_y)
            
        elif self.is_resizing:
            current_x, current_y = frame.getX(), frame.getZ()
            
            min_x_abs = current_x + min_x_size
            max_x_abs = current_x + max_x_size
            min_y_abs = current_y + min_y_size
            max_y_abs = current_y + max_y_size
            
            potential_min_x_abs = min_x_abs
            potential_max_x_abs = max_x_abs
            potential_min_y_abs = min_y_abs
            potential_max_y_abs = max_y_abs
            
            if 'r' in self.resizing_corner: potential_max_x_abs = mouse_x
            elif 'l' in self.resizing_corner: potential_min_x_abs = mouse_x
            
            if 't' in self.resizing_corner: potential_max_y_abs = mouse_y
            elif 'b' in self.resizing_corner: potential_min_y_abs = mouse_y
            
            # Korlátozás a képernyő határaihoz
            min_x_abs = max(-SCREEN_LIMIT, potential_min_x_abs)
            max_x_abs = min( SCREEN_LIMIT, potential_max_x_abs)
            min_y_abs = max(-SCREEN_LIMIT, potential_min_y_abs)
            max_y_abs = min( SCREEN_LIMIT, potential_max_y_abs)

            width = max(MIN_FRAME_SIZE, max_x_abs - min_x_abs)
            height = max(MIN_FRAME_SIZE, max_y_abs - min_y_abs)

            # Kényszerítjük a minimális méretet
            if width <= MIN_FRAME_SIZE:
                if 'l' in self.resizing_corner:
                    min_x_abs = max_x_abs - MIN_FRAME_SIZE
                else: 
                    max_x_abs = min_x_abs + MIN_FRAME_SIZE
                width = MIN_FRAME_SIZE

            if height <= MIN_FRAME_SIZE:
                if 'b' in self.resizing_corner:
                    min_y_abs = max_y_abs - MIN_FRAME_SIZE
                else: 
                    max_y_abs = min_y_abs + MIN_FRAME_SIZE
                height = MIN_FRAME_SIZE

            # Új frame méret és pozíció beállítása
            frame['frameSize'] = (-width / 2, width / 2, -height / 2, height / 2)
            new_center_x = min_x_abs + width / 2
            new_center_y = min_y_abs + height / 2
            frame.setPos(new_center_x, 0, new_center_y)
            
            # Belső tartalom frissítése méretezés után
            if frame == self.frame1:
                self._update_button_scale(width, height)
            elif frame == self.frame2:
                self._update_frame2_content(width, height)
            
            self.status_text.setText(f"MÉRETEZÉS: W:{width:.2f}, H:{height:.2f}")

        return Task.cont

    # Az alábbi _update_button_scale a Frame 1 méretezését kezeli
    def _update_button_scale(self, width, height):
        if not self.internal_button:
            return

        target_width = width * INTERNAL_BUTTON_FRACTION
        target_height = height * INTERNAL_BUTTON_FRACTION

        base_width = BUTTON_BASE_HALF_SIZE * 2
        base_height = BUTTON_BASE_HALF_SIZE * 2

        scale_x = target_width / base_width
        scale_y = target_height / base_height

        self.internal_button.setScale(scale_x, 1, scale_y) 

        visual_size = TARGET_FRAME_TEXT_SCALE 
        ts_x = visual_size / scale_x
        ts_y = visual_size / scale_y

        self.internal_button['text_scale'] = (ts_x, ts_y)

    # Az alábbi _update_frame2_content a Frame 2 tartalmának (scroll list) méretezését és pozícióját kezeli
    def _update_frame2_content(self, width, height):
        if not self.scroll_frame:
            return
        
        target_width = width * SCROLL_LIST_FRACTION
        target_height = height * SCROLL_LIST_FRACTION

        # Az eredeti DirectScrolledList mérete a inicializáláskor
        base_scroll_width = 0.8 # (0.4 * 2, ha a frameSize -0.4, 0.4 lenne) - A tartalomhoz igazítottuk
        base_scroll_height = 0.8 
        
        scale_x = target_width / base_scroll_width
        scale_y = target_height / base_scroll_height
        
        self.scroll_frame.setScale(scale_x, 1, scale_y)
        
        # Új pozíció beállítása, hogy a lista a frame belsejében maradjon
        frame_half_height = height / 2
        
        # Az eredeti frame-ben a lista a (-0.1) Z pozícióban volt
        Z_target = -0.1 * scale_y 
        
        self.scroll_frame.setZ(Z_target)


    def stop_interaction(self):
        if self.active_frame:
            # Visszaállítjuk az eredeti színt
            if self.active_frame == self.frame1:
                 self.active_frame['frameColor'] = (0.1, 0.1, 0.8, 0.9) 
            elif self.active_frame == self.frame2:
                 self.active_frame['frameColor'] = (0.8, 0.5, 0.1, 0.9) 
            
            self.is_dragging = False
            self.is_resizing = False
            self.active_frame = None
            self.resizing_corner = None
            self.taskMgr.doMethodLater(1.5, self.reset_status_text, 'reset_task')
        
        else:
            self.taskMgr.doMethodLater(1.5, self.reset_status_text, 'reset_task')


    def reset_status_text(self, task):
        self.status_text.setText("Húzd a Frame-et, vagy használd a görgőt a listán!")
        return task.done
    

if __name__ == '__main__':
    app = ManualFrameApp()
    app.run()