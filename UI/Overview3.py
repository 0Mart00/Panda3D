from direct.showbase.ShowBase import ShowBase
from panda3d.core import LVector2, loadPrcFileData, TextNode, Point3, LColor
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectScrolledFrame import DirectScrolledFrame 
from direct.gui import DirectGuiGlobals as DGG
from direct.task import Task
import random

# --- BOOTSTRAP 5 SZÍNPALETTA (Normalizálva 0.0 - 1.0) ---
BT_PRIMARY = (13/255, 110/255, 253/255, 1)     # #0d6efd
BT_SECONDARY = (108/255, 117/255, 125/255, 1)   # #6c757d
BT_SUCCESS = (25/255, 135/255, 84/255, 1)       # #198754
BT_INFO = (13/255, 202/255, 240/255, 1)          # #0dcaf0
BT_WARNING = (255/255, 193/255, 7/255, 1)       # #ffc107
BT_DANGER = (220/255, 53/255, 69/255, 1)        # #dc3545
BT_LIGHT = (248/255, 249/255, 250/255, 1)       # #f8f9fa
BT_DARK = (33/255, 37/255, 41/255, 1)           # #212529
BT_WHITE = (1, 1, 1, 1)
BT_BORDER = (222/255, 226/255, 230/255, 1)     # #dee2e6
BT_TEXT_DARK = (33/255, 37/255, 41/255, 1)

# --- KONFIGURÁCIÓ ---
WINDOW_SIZE = 1024
RESIZE_TOLERANCE = 0.08  # Érzékenység az éleknél
SCREEN_LIMIT = 1.3 
MIN_FRAME_SIZE = 0.3 
TARGET_FRAME_TEXT_SCALE = 0.05 
BUTTON_BASE_HALF_SIZE = 0.1 
INTERNAL_BUTTON_FRACTION = 0.8 
SCROLL_LIST_NUM_ITEMS = 30
SCROLL_ITEM_HEIGHT = 0.08
CAMERA_DEFAULT_Y = -12.0

prc_data = f"""
window-title Bootstrap Dashboard Simulation
win-size {WINDOW_SIZE} {WINDOW_SIZE}
background-color 0.95 0.96 0.97
"""
loadPrcFileData("", prc_data)

class BootstrapUIApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self) 
        self.is_dragging = False
        self.is_resizing = False 
        self.drag_offset = LVector2(0, 0) 
        self.active_frame = None 
        self.resizing_sides = "" 
        
        self.internal_button = None
        self.scroll_frame2 = None 
        self.scroll_frame3 = None 
        self.filter_buttons = []
        
        self.frame1 = None 
        self.frame2 = None 
        self.frame3 = None
        self.frame_list = []
        
        self.frame3_data = [] 
        self.current_filter = "All"

        base.camera.setY(CAMERA_DEFAULT_Y)
        
        self._generate_data()
        self._setup_panels()
        self._setup_drag_events() 
        self._setup_scroll_events()

    def _generate_data(self):
        """Mock adatok Bootstrap stílusú jelzőszínekkel."""
        for i in range(30):
            is_danger = random.random() > 0.5
            type_tag = "Critical" if is_danger else "Stable"
            color = BT_DANGER if is_danger else BT_SUCCESS
            self.frame3_data.append({
                "id": i,
                "text": f"System Node {i+1}",
                "type": type_tag,
                "color": color
            })

    def _internal_button_click(self):
        self.status_text.setText("Action: Primary Button Clicked!")

    def _stop_event_propagation(self, event):
        """Megállítja az esemény továbbterjedését a gombokról."""
        return event.stop()
        
    def _setup_panels(self):
        # Felső státusz szöveg
        self.status_text = OnscreenText(
            text="Bootstrap UI Dashboard - Drag & Resize Active",
            pos=(0, 0.92), 
            scale=0.07, 
            fg=BT_TEXT_DARK, 
            mayChange=True
        )
        
        panel_half_scale = 0.3
        initial_w = panel_half_scale * 2
        initial_h = panel_half_scale * 2
        
        # --- FRAME 1 (Vezérlő kártya) ---
        self.frame1 = DirectFrame(
            frameColor=BT_WHITE,
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(-0.6, 0, 0.3), 
            text="Control Panel", 
            text_scale=0.045, 
            text_pos=(0, 0.22),
            text_fg=BT_TEXT_DARK,
            borderWidth=(0.01, 0.01)
        )
        self.frame_list.append(self.frame1)

        self.internal_button = DirectButton(
            parent=self.frame1, 
            frameColor=BT_PRIMARY,
            text="Run Diagnostics",
            text_fg=BT_WHITE,
            text_scale=0.04,
            command=self._internal_button_click,
            pad=(0.1, 0.1),
            relief=DGG.FLAT
        )
        self.internal_button.bind('press', self._stop_event_propagation)
        self._update_button_scale(width=initial_w, height=initial_h)
        
        # --- FRAME 2 (Hírfolyam kártya) ---
        self.frame2 = DirectFrame(
            frameColor=BT_WHITE, 
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(0.0, 0, -0.4), 
            text="Activity Feed", 
            text_scale=0.045,
            text_pos=(0, 0.22),
            text_fg=BT_TEXT_DARK
        )
        self.frame_list.append(self.frame2)

        canvas_h = SCROLL_LIST_NUM_ITEMS * (SCROLL_ITEM_HEIGHT + 0.01)
        self.scroll_frame2 = DirectScrolledFrame(
            parent=self.frame2,
            frameSize=(-0.25, 0.25, -0.2, 0.2), 
            canvasSize=(-0.2, 0.2, -canvas_h, 0),
            scrollBarWidth=0.03,
            frameColor=BT_LIGHT,
            verticalScroll_frameColor=BT_BORDER,
            verticalScroll_thumb_frameColor=BT_SECONDARY,
            relief=DGG.FLAT
        )
        
        for i in range(SCROLL_LIST_NUM_ITEMS):
            y_pos = -0.05 - (i * (SCROLL_ITEM_HEIGHT + 0.005))
            btn = DirectButton(
                text=f"Log Entry #{i + 1} - System OK",
                text_scale=0.035,
                text_align=TextNode.ALeft,
                text_pos=(-0.18, -0.01),
                frameColor=BT_WHITE,
                frameSize=(-0.22, 0.22, -0.035, 0.035),
                pos=(0, 0, y_pos),
                parent=self.scroll_frame2.getCanvas(),
                relief=DGG.RAISED,
                borderWidth=(0.005, 0.005),
                command=lambda i=i: self.status_text.setText(f"Feed Item: {i+1}")
            )
            btn.bind('press', self._stop_event_propagation)

        self._update_frame2_content(initial_w, initial_h)

        # --- FRAME 3 (Hálózati csomópontok kártya) ---
        self.frame3 = DirectFrame(
            frameColor=BT_WHITE,
            frameSize=(-panel_half_scale, panel_half_scale, -panel_half_scale, panel_half_scale),
            pos=(0.6, 0, 0.3),
            text="Network Nodes",
            text_scale=0.045,
            text_fg=BT_TEXT_DARK,
            text_pos=(0, 0.22)
        )
        self.frame_list.append(self.frame3)
        
        # Szűrő gombok
        filter_opts = ["All", "Critical", "Stable"]
        btn_colors = [BT_SECONDARY, BT_DANGER, BT_SUCCESS]
        
        for idx, lbl in enumerate(filter_opts):
            btn = DirectButton(
                parent=self.frame3,
                text=lbl,
                text_scale=0.035,
                text_fg=BT_WHITE,
                frameColor=btn_colors[idx],
                frameSize=(-0.09, 0.09, -0.03, 0.03),
                relief=DGG.FLAT,
                command=self._apply_filter,
                extraArgs=[lbl]
            )
            btn.bind('press', self._stop_event_propagation)
            self.filter_buttons.append(btn)
            
        self.scroll_frame3 = DirectScrolledFrame(
            parent=self.frame3,
            frameSize=(-0.25, 0.25, -0.15, 0.15),
            canvasSize=(-0.2, 0.2, -1, 0),
            scrollBarWidth=0.03,
            frameColor=BT_LIGHT,
            relief=DGG.FLAT,
            verticalScroll_thumb_frameColor=BT_SECONDARY
        )
        
        self._apply_filter("All")
        self._update_frame3_content(initial_w, initial_h)

    def _apply_filter(self, filter_type):
        self.current_filter = filter_type
        for child in self.scroll_frame3.getCanvas().getChildren():
            child.removeNode()
            
        filtered_data = [item for item in self.frame3_data if filter_type == "All" or item["type"] == filter_type]
        item_h, spacing, current_y = 0.07, 0.01, -0.05
        
        for item in filtered_data:
            f = DirectFrame(
                parent=self.scroll_frame3.getCanvas(),
                frameColor=BT_WHITE,
                frameSize=(-0.22, 0.22, -item_h/2, item_h/2),
                pos=(0, 0, current_y),
                borderWidth=(0.002, 0.002),
                relief=DGG.GROOVE
            )
            DirectFrame(parent=f, frameColor=item["color"], frameSize=(-0.21, -0.18, -0.02, 0.02))
            OnscreenText(parent=f, text=item["text"], scale=0.035, pos=(-0.16, -0.01), align=TextNode.ALeft, fg=BT_TEXT_DARK)
            f.bind(DGG.B1PRESS, self._stop_event_propagation)
            current_y -= (item_h + spacing)
            
        canvas_h = abs(current_y)
        self.scroll_frame3['canvasSize'] = (-0.23, 0.23, -canvas_h, 0)

    # --- LAYOUT LOGIKA ---

    def _update_button_scale(self, width, height):
        if not self.internal_button: return
        target_w, target_h = width * 0.7, 0.08
        self.internal_button['frameSize'] = (-target_w/2, target_w/2, -target_h/2, target_h/2)
        self.internal_button.setPos(0, 0, -0.05)

    def _update_frame2_content(self, width, height):
        if not self.scroll_frame2: return
        margin = 0.06
        list_w, list_h = width - (margin * 2), height - (margin * 3)
        self.scroll_frame2['frameSize'] = (-list_w/2, list_w/2, -list_h/2, list_h/2)
        self.scroll_frame2.setPos(0, 0, -margin)

    def _update_frame3_content(self, width, height):
        if not self.scroll_frame3: return
        half_w, half_h = width / 2, height / 2
        filter_y = half_h - 0.12
        btn_spacing = width / 5.0
        start_x = -btn_spacing
        
        for i, btn in enumerate(self.filter_buttons):
            btn.setPos(start_x + (i * btn_spacing), 0, filter_y)
            btn.setScale(min(1.0, width * 1.6))

        list_top, list_bottom = filter_y - 0.08, -half_h + 0.05
        list_h, list_w = list_top - list_bottom, width - 0.1
        sf_hw, sf_hh = list_w / 2, list_h / 2
        self.scroll_frame3['frameSize'] = (-sf_hw, sf_hw, -sf_hh, sf_hh)
        self.scroll_frame3.setPos(0, 0, list_bottom + sf_hh)

    # --- INTERAKCIÓS LOGIKA (DRAG & RESIZE) ---

    def _setup_scroll_events(self):
        self.accept('wheel_up', self._on_scroll, [-1]) 
        self.accept('wheel_down', self._on_scroll, [1])

    def _setup_drag_events(self):
        self.accept('mouse1', self.start_interaction_check) 
        self.accept('mouse1-up', self.stop_interaction)
        self.taskMgr.add(self.interaction_task, 'interaction_task')

    def _get_hovered_scroll_frame(self):
        if not base.mouseWatcherNode.hasMouse(): return None
        mw, m_pos = base.mouseWatcherNode, Point3(base.mouseWatcherNode.getMouseX(), 0, base.mouseWatcherNode.getMouseY())
        for sf in [self.scroll_frame2, self.scroll_frame3]:
            if sf:
                local, f_size = sf.getRelativePoint(render2d, m_pos), sf['frameSize']
                if f_size[0] <= local.x <= f_size[1] and f_size[2] <= local.z <= f_size[3]: return sf
        return None

    def _on_scroll(self, direction):
        if self.active_frame: return
        target_sf = self._get_hovered_scroll_frame()
        if target_sf:
            sb = target_sf.verticalScroll
            if sb and not sb.isHidden():
                r = sb['range']
                sb['value'] = max(r[0], min(r[1], sb['value'] + 0.08 * direction))
        else:
            curr_y = base.camera.getY()
            base.camera.setY(max(-40, min(-2, curr_y + (2.0 * -direction))))

    def _check_interaction_area(self, mx, my, frame):
        pos = frame.getPos()
        fs = frame['frameSize']
        ax1, ax2, az1, az2 = pos.getX() + fs[0], pos.getX() + fs[1], pos.getZ() + fs[2], pos.getZ() + fs[3]
        
        # Külső határ ellenőrzése toleranciával
        if not (ax1 - RESIZE_TOLERANCE <= mx <= ax2 + RESIZE_TOLERANCE and 
                az1 - RESIZE_TOLERANCE <= my <= az2 + RESIZE_TOLERANCE):
            return None, ""
            
        # Átméretezési élek detektálása
        sides = ""
        if abs(mx - ax2) < RESIZE_TOLERANCE: sides += "r"
        elif abs(mx - ax1) < RESIZE_TOLERANCE: sides += "l"
        if abs(my - az2) < RESIZE_TOLERANCE: sides += "t"
        elif abs(my - az1) < RESIZE_TOLERANCE: sides += "b"
        
        if sides: return 'resize', sides
        
        # Ha benne vagyunk a belső területen -> HÚZÁS
        if ax1 <= mx <= ax2 and az1 <= my <= az2:
            return 'drag', ""
            
        return None, ""

    def start_interaction_check(self):
        if not base.mouseWatcherNode.hasMouse(): return
        m = base.mouseWatcherNode.getMouse()
        mx, my = m.getX(), m.getY()
        
        for frame in reversed(self.frame_list):
            action, sides = self._check_interaction_area(mx, my, frame)
            if action:
                self.active_frame = frame
                self.frame_list.remove(frame)
                self.frame_list.append(frame)
                frame.reparentTo(base.aspect2d)
                
                if action == 'resize':
                    self.is_resizing = True
                    self.resizing_sides = sides
                    self.active_frame['frameColor'] = (0.9, 0.95, 1, 1) # Átméretezés visszajelzés
                elif action == 'drag':
                    self.is_dragging = True
                    # Eltolás kiszámítása a stabil húzáshoz
                    self.drag_offset = LVector2(frame.getX() - mx, frame.getZ() - my)
                    self.active_frame['frameColor'] = (0.95, 0.95, 0.95, 1) # Húzás visszajelzés
                
                self._refresh_active_frame_content()
                return

    def _refresh_active_frame_content(self):
        if not self.active_frame: return
        fs = self.active_frame['frameSize']
        w, h = fs[1] - fs[0], fs[3] - fs[2]
        if self.active_frame == self.frame1: self._update_button_scale(w, h)
        elif self.active_frame == self.frame2: self._update_frame2_content(w, h)
        elif self.active_frame == self.frame3: self._update_frame3_content(w, h)

    def interaction_task(self, task):
        if not self.active_frame or not base.mouseWatcherNode.hasMouse(): return Task.cont
        m = base.mouseWatcherNode.getMouse()
        mx, my = m.getX(), m.getY()
        frame, fs = self.active_frame, self.active_frame['frameSize']
        
        if self.is_dragging:
            # Új pozíció a drag_offset használatával
            nx = max(-SCREEN_LIMIT, min(SCREEN_LIMIT, mx + self.drag_offset.getX()))
            ny = max(-SCREEN_LIMIT, min(SCREEN_LIMIT, my + self.drag_offset.getY()))
            frame.setPos(nx, 0, ny)
            
        elif self.is_resizing:
            cx, cz = frame.getX(), frame.getZ()
            ax1, ax2, az1, az2 = cx + fs[0], cx + fs[1], cz + fs[2], cz + fs[3]
            
            if 'r' in self.resizing_sides: ax2 = mx
            if 'l' in self.resizing_sides: ax1 = mx
            if 't' in self.resizing_sides: az2 = my
            if 'b' in self.resizing_sides: az1 = my
            
            w, h = max(MIN_FRAME_SIZE, ax2 - ax1), max(MIN_FRAME_SIZE, az2 - az1)
            frame['frameSize'] = (-w/2, w/2, -h/2, h/2)
            frame.setPos(ax1 + w/2, 0, az1 + h/2)
            self._refresh_active_frame_content()

        return Task.cont

    def stop_interaction(self):
        if self.active_frame:
            self.active_frame['frameColor'] = BT_WHITE
            self.is_dragging, self.is_resizing = False, False
            self.active_frame, self.resizing_sides = None, ""

if __name__ == '__main__':
    app = BootstrapUIApp()
    app.run()