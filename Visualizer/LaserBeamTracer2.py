from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomLines, Geom, GeomNode,
    TransparencyAttrib
)
from direct.task import Task
from direct.interval.IntervalGlobal import Sequence, Func, Wait, Parallel, LerpFunc
import random
import math

# Configuration for the window settings
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Lézersugár Rajzoló (Lövés)")
loadPrcFileData("", "show-frame-rate-meter true")

def create_laser_geometry(start_point, end_point, color):
    """
    Programmatically generates a line segment (the laser beam) using GeomLines.
    Létrehoz egy vonalszakaszt (lézersugarat) programozottan a GeomLines használatával.
    """
    # V3c4 format: 3D Vertex, 4D Color (RGBa)
    format = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData('laser_data', format, Geom.UHStatic)
    
    vertex = GeomVertexWriter(vdata, 'vertex')
    color_writer = GeomVertexWriter(vdata, 'color')

    # Add start and end points
    vertex.addData3f(start_point.x, start_point.y, start_point.z)
    vertex.addData3f(end_point.x, end_point.y, end_point.z)
    
    # Add color for both vertices
    color_writer.addData4f(color)
    color_writer.addData4f(color)

    # Create the line primitive
    lines = GeomLines(Geom.UHStatic)
    lines.addVertices(0, 1) # Define the line from vertex 0 to vertex 1
    
    geom = Geom(vdata)
    geom.addPrimitive(lines)
    
    node = GeomNode('laser_geom')
    node.addGeom(geom)
    
    return NodePath(node)

class LaserBeamTracer(ShowBase):
    """
    Panda3D application that simulates a laser firing every 1 second.
    The laser beam appears instantly and disappears after a short duration.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        self.setBackgroundColor(0.05, 0.05, 0.1, 1) # Dark blue background
        self.cam.setPos(0, -30, 10)
        self.cam.lookAt(0, 0, 0)
        
        # Set up Lighting (Fénybeállítások)
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.2, 0.2, 0.2, 1)) 
        self.render.setLight(self.render.attachNewNode(alight))

        # --- 2. Laser Setup (Lézersugár Beállítása) ---
        self.start_point = LVector3(0, 0, 0) # Fixed origin point
        self.laser_color = VBase4(0.0, 1.0, 0.5, 1.0) # Bright green/cyan laser
        
        # Placeholders for the current laser object (not used initially)
        self.current_laser = None
        
        # --- 3. Firing Task (Lövés Feladat) ---
        # Firing frequency is 1 second
        self.taskMgr.doMethodLater(0.0, self.fire_laser, "LaserFireTask")
        
        # Time variable for target position generation
        self.time = 0.0

    def get_new_target_point(self):
        """Calculates a new target point based on current time."""
        self.time += 1.0 # Increment time to get distinct positions for each shot
        
        # Complex, 3D trajectory calculation
        x = math.sin(self.time * 1.5) * 8
        y = math.cos(self.time * 2.0) * 8
        z = 5 + math.sin(self.time * 0.7) * 4 
        
        return LVector3(x, y, z)

    def fire_laser(self, task):
        """
        Creates and animates a single laser beam, making it disappear quickly.
        Létrehozza és animálja az egyedi lézersugarat, gyorsan eltüntetve azt.
        """
        # Get the new destination for the beam
        end_point = self.get_new_target_point()
        
        # 1. Create the laser geometry
        new_laser = create_laser_geometry(self.start_point, end_point, self.laser_color)
        new_laser.reparentTo(self.render)
        new_laser.setTwoSided(True)
        new_laser.setRenderModeThickness(3.0)
        new_laser.setTransparency(TransparencyAttrib.MAlpha)

        # Ensure the laser starts fully opaque
        new_laser.setColorScale(1.0, 1.0, 1.0, 1.0)
        
        # 2. Define the animation sequence
        
        # Duration the beam is visible (e.g., 0.1 seconds)
        visibility_duration = 0.1
        
        # Duration of the fade out (e.g., 0.4 seconds)
        fade_duration = 0.4
        
        # Define the fading effect
        fade_out = new_laser.colorScaleInterval(
            fade_duration,
            VBase4(1.0, 1.0, 1.0, 0.0), # Target alpha 0.0 (transparent)
            startColorScale=new_laser.getColorScale()
        )
        
        # Sequence: Visible -> Wait -> Fade Out -> Cleanup
        laser_sequence = Sequence(
            Wait(visibility_duration), # Keep the laser visible for a short moment
            fade_out, # Fade out the beam
            Func(new_laser.removeNode) # Remove the node after fading
        )
        
        laser_sequence.start()

        # --- FIX: Set delayTime explicitly and return Task.again ---
        task.delayTime = 1.0
        return Task.again

# Run the application
if __name__ == "__main__":
    app = LaserBeamTracer()
    app.run()