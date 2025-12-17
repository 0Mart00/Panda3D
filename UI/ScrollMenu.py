from direct.showbase.ShowBase import ShowBase
from panda3d.core import LVector2, loadPrcFileData, TextNode
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectScrolledList import DirectScrolledList
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
        self.scroll_list = None 
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

        # --- GÖRGŐS LISTA --- 
        list_items = []
        for i in range(SCROLL_LIST_NUM_ITEMS):
            color = (random.random(), random.random(), random.random(), 1)
            item = DirectButton(
                text=f"Lista Elem #{i + 1}",
                text_scale=0.05,
                text_align=TextNode.ALeft,
                text_pos=(-0.1, -0.015),
                frameColor=color,
                frameSize=(-0.3, 0.3, -SCROLL_ITEM_HEIGHT/2, SCROLL_ITEM_HEIGHT/2),
                relief=1,
                command=lambda i=i: self.status_text.setText(f"Elem: {i+1} kiválasztva")
            )
            list_items.append(item)
            
        self.scroll_list = DirectScrolledList(
            parent=self.frame2,
            # A gombok definíciója megmarad a belső logika miatt, de elrejtjük őket
            decButton_pos=( 0.4, 0,  0.22), 
            decButton_text = "Fel",
            decButton_text_scale = 0.05,
            incButton_pos=( 0.4, 0, -0.22),
            incButton_text = "Le",
            incButton_text_scale = 0.05,
            frameColor = (0.3, 0.3, 0.3, 0.8),
            itemFrame_frameColor = (0.5, 0.5, 0.5, 1),
            items = list_items,
            numItemsVisible = 4, 
            forceHeight = SCROLL_ITEM_HEIGHT,
            pos=(0, 0, -0.1),
            scale=(1, 1, 1)
        )

        # GOMBOK ELREJTÉSE (Kérésre)
        # Bár a gombok léteznek a memóriában (a görgetéshez kellenek),
        # vizuálisan eltüntetjük őket.
        if hasattr(self.scroll_list, 'incButton'):
            self.scroll_list.incButton.hide()
        if hasattr(self.scroll_list, 'decButton'):
            self.scroll_list.decButton.hide()
        
        self._update_frame2_content(initial_width, initial_height)

    # --- GÖRGETŐS FUNKCIÓK JAVÍTVA ---

    def _setup_scroll_events(self):
        self.accept('wheel_up', self._on_scroll_up)
        self.accept('wheel_down', self._on_scroll_down)


    def _is_cursor_strictly_inside(self, frame):
        if not base.mouseWatcherNode.hasMouse():
            return False

        mw = base.mouseWatcherNode
        mouse_render2d = Point3(mw.getMouseX(), 0, mw.getMouseY())

        # render2d → frame lokális tér
        local = frame.getRelativePoint(render2d, mouse_render2d)

        min_x, max_x, min_z, max_z = frame['frameSize']
        return min_x <= local.x <= max_x and min_z <= local.z <= max_z


    def _on_scroll_up(self):
        if self.active_frame is not None:  # <<< IDE
            return

        if base.mouseWatcherNode.hasMouse():
            m = base.mouseWatcherNode.getMouse()
            if self._is_cursor_strictly_inside(self.frame2):
                self.scroll_list.scrollBy(-1)  # felfelé
            else:
                current_y = base.camera.getY()
                new_y = min(CAMERA_ZOOM_MAX_DIST, current_y + CAMERA_ZOOM_STEP)
                base.camera.setY(new_y)


    def _on_scroll_down(self):
        if self.active_frame is not None:  # <<< IDE
            return

        if base.mouseWatcherNode.hasMouse():
            m = base.mouseWatcherNode.getMouse()
            if self._is_cursor_strictly_inside(self.frame2):
                self.scroll_list.scrollBy(1)  # lefelé
            else:
                current_y = base.camera.getY()
                new_y = max(CAMERA_ZOOM_MIN_DIST, current_y - CAMERA_ZOOM_STEP)
                base.camera.setY(new_y)


    # ------------------------------------------------------------------

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

        for frame in reversed(self.frame_list):
            action, corner = self._check_interaction_area(mouse_x, mouse_y, frame)
            
            if action:
                self.active_frame = frame
                
                self.frame_list.remove(frame)
                self.frame_list.append(frame)
                frame.reparentTo(base.aspect2d)
                
                if action == 'resize':
                    self.is_resizing = True
                    self.resizing_corner = corner
                    self.active_frame['frameColor'] = (0.8, 0.1, 0.8, 0.9) 
                        
                elif action == 'drag':
                    self.is_dragging = True
                    frame_pos = frame.getPos()
                    self.drag_offset = LVector2(frame_pos.getX() - mouse_x, frame_pos.getZ() - mouse_y)
                    self.active_frame['frameColor'] = (0.0, 0.8, 0.0, 0.9) 
                
                self.status_text.setText(f"{'MÉRETEZÉS' if self.is_resizing else 'HÚZÁS'}")
                
                current_size = frame['frameSize']
                w = current_size[1] - current_size[0]
                h = current_size[3] - current_size[2]
                
                if frame == self.frame1:
                    self._update_button_scale(w, h)
                elif frame == self.frame2:
                    self._update_frame2_content(w, h)

                return 

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
            
            min_x_abs = max(-SCREEN_LIMIT, potential_min_x_abs)
            max_x_abs = min( SCREEN_LIMIT, potential_max_x_abs)
            min_y_abs = max(-SCREEN_LIMIT, potential_min_y_abs)
            max_y_abs = min( SCREEN_LIMIT, potential_max_y_abs)

            width = max(MIN_FRAME_SIZE, max_x_abs - min_x_abs)
            height = max(MIN_FRAME_SIZE, max_y_abs - min_y_abs)

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

            frame['frameSize'] = (-width / 2, width / 2, -height / 2, height / 2)
            new_center_x = min_x_abs + width / 2
            new_center_y = min_y_abs + height / 2
            frame.setPos(new_center_x, 0, new_center_y)
            
            if frame == self.frame1:
                self._update_button_scale(width, height)
            elif frame == self.frame2:
                self._update_frame2_content(width, height)
            
            self.status_text.setText(f"MÉRETEZÉS: W:{width:.2f}, H:{height:.2f}")

        return Task.cont

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

    def _update_frame2_content(self, width, height):
        if not self.scroll_list:
            return
            
        target_width = width * SCROLL_LIST_FRACTION
        target_height = height * SCROLL_LIST_FRACTION

        base_scroll_width = 0.8
        base_scroll_height = 0.8 
        
        scale_x = target_width / base_scroll_width
        scale_y = target_height / base_scroll_height
        
        self.scroll_list.setScale(scale_x, 1, scale_y)
        
        frame_half_height = height / 2
        list_half_height_in_frame_coords = (base_scroll_height / 2) * scale_y
        
        Z_target = -0.1 
        Z_required_to_stay_in_bounds = -frame_half_height + list_half_height_in_frame_coords
        Z_new_pos = max(Z_target, Z_required_to_stay_in_bounds)
        
        self.scroll_list.setZ(Z_new_pos)
        

    def stop_interaction(self):
        if self.active_frame:
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