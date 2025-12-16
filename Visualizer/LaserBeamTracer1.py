from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomLines, Geom, GeomNode,
    TransparencyAttrib
)
from direct.task import Task
import random
import math

# Configuration for the window settings
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Lézersugár Rajzoló")
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
    Panda3D application that draws a laser beam by continually updating
    the line geometry between two points.
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
        self.end_point = LVector3(5, 5, 5)   # Target point that will move
        self.laser_color = VBase4(0.0, 1.0, 0.5, 1.0) # Bright green/cyan laser
        
        # Create initial laser beam geometry
        self.laser_beam = create_laser_geometry(self.start_point, self.end_point, self.laser_color)
        self.laser_beam.reparentTo(self.render)
        self.laser_beam.setTwoSided(True) # Ensure visibility from all angles
        self.laser_beam.setRenderModeThickness(3.0) # Make the line thicker (might not work depending on renderer)
        self.laser_beam.setTransparency(TransparencyAttrib.MAlpha)

        # --- 3. Animation Task (Animációs Feladat) ---
        self.time = 0.0
        self.taskMgr.add(self.update_laser, "UpdateLaserTask")
        
    def update_laser(self, task):
        """
        Updates the target point of the laser based on time to create a drawing effect.
        Frissíti a lézer végpontját az idő függvényében, rajzoló hatást keltve.
        """
        self.time += globalClock.getDt() # Get time elapsed since last frame

        # Use trigonometric functions (sine and cosine) to make the target point
        # move in a complex, 3D pattern (like drawing on an imaginary sphere or surface)
        
        # X: movement based on sine wave
        x = math.sin(self.time * 1.5) * 8
        
        # Y: movement based on a faster cosine wave (back and forth)
        y = math.cos(self.time * 2.0) * 8
        
        # Z: height movement based on a different sine wave (up and down)
        z = 5 + math.sin(self.time * 0.7) * 4 
        
        new_end_point = LVector3(x, y, z)
        
        # 1. Update the end point
        self.end_point = new_end_point
        
        # 2. Recreate/Update the geometry based on the new points
        # NOTE: Recreating the geometry every frame is slow, but necessary for dynamic line updates 
        # when not using specialized particle/trail systems.
        
        # Remove the old laser node
        self.laser_beam.removeNode()
        
        # Create a new laser node with the updated points
        self.laser_beam = create_laser_geometry(self.start_point, self.end_point, self.laser_color)
        self.laser_beam.reparentTo(self.render)
        self.laser_beam.setTwoSided(True)
        self.laser_beam.setRenderModeThickness(3.0)
        self.laser_beam.setTransparency(TransparencyAttrib.MAlpha)

        return Task.cont

# Run the application
if __name__ == "__main__":
    app = LaserBeamTracer()
    app.run()