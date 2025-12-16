from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    TransparencyAttrib, DirectionalLight, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode
)
from direct.task import Task
from direct.interval.IntervalGlobal import Sequence, Parallel, LerpFunc, Func

# Configuration to disable the default splash window for cleaner execution
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Kocka Részecske Emitter")
loadPrcFileData("", "show-frame-rate-meter true")

# Kocka geometria generálása a fájlbetöltési hibák elkerülése érdekében
def create_cube_mesh():
    """Generates a cube mesh programmatically."""
    format = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData('cube_data', format, Geom.UHStatic)
    
    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    texcoord = GeomVertexWriter(vdata, 'texcoord')

    # Fél méret (a középpontból)
    s = 0.5 

    # Kocka csúcsai (8 csúcs)
    points = [
        (-s, -s, -s), ( s, -s, -s), ( s,  s, -s), (-s,  s, -s),  # Alsó lap
        (-s, -s,  s), ( s, -s,  s), ( s,  s,  s), (-s,  s,  s)   # Felső lap
    ]

    # Felületek (6 felület, 4 csúcs/felület, 2 háromszög/felület = 36 index)
    faces = [
        # Elülső
        0, 1, 2, 3, 
        # Hátsó
        4, 7, 6, 5, 
        # Jobb
        1, 5, 6, 2, 
        # Bal
        0, 3, 7, 4, 
        # Felső
        3, 2, 6, 7, 
        # Alsó
        0, 4, 5, 1
    ]

    # Normálok
    normals = [
        ( 0, -1,  0), # Elülső
        ( 0,  1,  0), # Hátsó
        ( 1,  0,  0), # Jobb
        (-1,  0,  0), # Bal
        ( 0,  0,  1), # Felső
        ( 0,  0, -1)  # Alsó
    ]

    # A kocka létrehozása a felületek és háromszögek hozzáadásával
    prim = GeomTriangles(Geom.UHStatic)
    for i in range(6): # 6 felület
        # 4 csúcsot használunk minden felülethez (a textúra koordináták miatt ismételjük a pontokat)
        
        # Első háromszög
        p1 = points[faces[i*4 + 0]]
        p2 = points[faces[i*4 + 1]]
        p3 = points[faces[i*4 + 2]]
        
        # Második háromszög
        p4 = points[faces[i*4 + 0]]
        p5 = points[faces[i*4 + 2]]
        p6 = points[faces[i*4 + 3]]
        
        tris = [p1, p2, p3, p4, p5, p6]
        
        for k in range(6):
            vertex.addData3f(tris[k][0], tris[k][1], tris[k][2])
            normal.addData3f(normals[i][0], normals[i][1], normals[i][2])
            
            # Textúra koordináták, egyszerűen a felület sarkait használva
            if k == 0 or k == 3: texcoord.addData2f(0.0, 0.0)
            elif k == 1: texcoord.addData2f(1.0, 0.0)
            elif k == 2 or k == 4: texcoord.addData2f(1.0, 1.0)
            elif k == 5: texcoord.addData2f(0.0, 1.0)

        # Minden felülethez két háromszöget adunk hozzá (összesen 12)
        v_offset = i * 6
        prim.addVertices(v_offset + 0, v_offset + 1, v_offset + 2)
        prim.addVertices(v_offset + 3, v_offset + 4, v_offset + 5)
        
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    
    node = GeomNode('cube_geom')
    node.addGeom(geom)
    
    return NodePath(node)

class CubeParticleEmitter(ShowBase):
    """
    Panda3D application that generates small cube particles around a central cube.
    Uses the Task and Interval system for animation and avoids loading external models.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        self.setBackgroundColor(0.1, 0.1, 0.15, 1) # Dark background
        self.cam.setPos(15, -15, 10)
        self.cam.lookAt(0, 0, 0)
        
        self.active_particles = []
        self.max_particles = 300
        self.center_pos = LVector3(0, 0, 0)
        
        # Set up Lighting
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.4, 0.4, 0.4, 1))
        self.render.setLight(self.render.attachNewNode(alight))

        dlight = DirectionalLight('dlight')
        dlight.setColor(VBase4(0.9, 0.9, 0.9, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(45, -45, 0)
        self.render.setLight(dlnp)

        # --- CENTER CUBE (Központi kocka) ---
        self.center_cube = create_cube_mesh()
        self.center_cube.reparentTo(self.render)
        self.center_cube.setScale(3.0) # Larger size for the emitter
        self.center_cube.setPos(self.center_pos)
        self.center_cube.setColor(0.3, 0.3, 0.5, 1.0) # Solid blue/purple color

        # --- 2. Particle Task Setup (Részecske indítási feladat) ---
        # Task to continuously spawn new particles
        self.taskMgr.doMethodLater(0.02, self.spawn_particle, "SpawnParticleTask")
        
        # Task to gently rotate the center cube
        self.taskMgr.add(self.rotate_cube, "RotateCubeTask")

    def rotate_cube(self, task):
        """Rotates the center cube gently."""
        self.center_cube.setH(self.center_cube.getH() + 0.1)
        self.center_cube.setP(self.center_cube.getP() + 0.05)
        return Task.cont

    def spawn_particle(self, task):
        """Spawns a new particle (small cube) and starts its life cycle."""
        
        if len(self.active_particles) >= self.max_particles:
            return Task.cont

        # 1. Create the particle (small cube mesh)
        particle = create_cube_mesh()
        particle.reparentTo(self.render)
        
        # --- Initial Properties ---
        life_duration = 1.5 + (0.5 * (globalClock.getFrameTime() * 1.5) % 1) # 1.5 to 2.0 seconds
        
        # Start position: slightly outside the center cube
        rand_x = (0.5 - (globalClock.getFrameTime() * 1.1) % 1) * 3
        rand_y = (0.5 - (globalClock.getFrameTime() * 1.3) % 1) * 3
        rand_z = (0.5 - (globalClock.getFrameTime() * 1.7) % 1) * 3
        start_pos = self.center_pos + LVector3(rand_x, rand_y, rand_z) * 0.5
        
        particle.setPos(start_pos)
        initial_scale = 0.2
        particle.setScale(initial_scale)
        
        # Define velocity and end position (move outwards)
        outward_direction = start_pos - self.center_pos
        outward_direction.normalize()
        
        # End position: further away from the center
        end_pos = start_pos + outward_direction * 8 * (1.0 + (globalClock.getFrameTime() % 1) * 0.5)

        # --- 2. Particle Animation (Intervals) ---
        
        # A. Movement: Linear movement outwards
        move_interval = particle.posInterval(
            life_duration,
            pos=end_pos,
            startPos=start_pos
        )
        
        # B. Scaling and Fading (Visuals)
        # Scale: Starts small, shrinks to 0
        scale_down = particle.scaleInterval(life_duration, 0.0, startScale=initial_scale)
        
        # Color: Light green to dark transparent (fading)
        color_start = VBase4(0.2, 1.0, 0.2, 1.0) # Bright Green
        color_end = VBase4(0.0, 0.2, 0.0, 0.0) # Dark, Transparent
        
        color_interval = LerpFunc(
            self.update_color_and_alpha,
            duration=life_duration,
            fromData=0.0,
            toData=1.0,
            extraArgs=[particle, color_start, color_end]
        )

        # 3. Combine animations and deletion (Life Cycle)
        life_cycle = Sequence(
            Parallel(move_interval, scale_down, color_interval),
            Func(self.destroy_particle, particle) # Cleanup function
        )
        
        life_cycle.start()
        self.active_particles.append(particle)
        
        return Task.cont

    def update_color_and_alpha(self, t, particle, start_color, end_color):
        """Custom LerpFunc to handle color and alpha interpolation."""
        
        # Linear interpolation
        r = start_color[0] * (1-t) + end_color[0] * t
        g = start_color[1] * (1-t) + end_color[1] * t
        b = start_color[2] * (1-t) + end_color[2] * t
        a = start_color[3] * (1-t) + end_color[3] * t

        particle.setColor(VBase4(r, g, b, a), 1) 
        
        # Enable transparency
        particle.setTransparency(TransparencyAttrib.MAlpha)

    def destroy_particle(self, particle):
        """Removes the particle from the scene and the active list."""
        if particle in self.active_particles:
            self.active_particles.remove(particle)
        particle.removeNode()

# Run the application
if __name__ == "__main__":
    app = CubeParticleEmitter()
    app.run()