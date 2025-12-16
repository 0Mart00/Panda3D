from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, VBase4, loadPrcFileData, NodePath, LVector3, 
    TransparencyAttrib, DirectionalLight, 
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode
)
from direct.task import Task
from direct.interval.IntervalGlobal import Sequence, Parallel, LerpFunc, Func
import random

# Configuration to disable the default splash window for cleaner execution
loadPrcFileData("", "notify-level-audio error")
loadPrcFileData("", "window-title Panda3D Retro Kocka Részecske Emitter")
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

class RetroCubeParticles(ShowBase):
    """
    Panda3D application that generates small cube particles with a retro/pixelated aesthetic.
    """
    def __init__(self):
        ShowBase.__init__(self)

        # --- 1. Basic Scene Setup (Alapvető helyszín beállítása) ---
        # Mély, sötét háttér a retro hatásért
        self.setBackgroundColor(0.1, 0.05, 0.05, 1) 
        self.cam.setPos(12, -18, 12) # Slightly elevated camera angle
        self.cam.lookAt(0, 0, 0)
        
        self.active_particles = []
        self.max_particles = 300
        self.center_pos = LVector3(0, 0, 0)
        
        # Set up Lighting (Fénybeállítások)
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.5, 0.4, 0.3, 1)) # Meleg ambient fény
        self.render.setLight(self.render.attachNewNode(alight))

        dlight = DirectionalLight('dlight')
        dlight.setColor(VBase4(1.0, 0.9, 0.7, 1)) # Sárgás/fehér fő fény
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(60, -60, 0)
        self.render.setLight(dlnp)

        # --- CENTER CUBE (Központi kocka) ---
        self.center_cube = create_cube_mesh()
        self.center_cube.reparentTo(self.render)
        self.center_cube.setScale(3.0) # Larger size for the emitter
        self.center_cube.setPos(self.center_pos)
        # Retro Barna/Narancs szín a központi kockához
        self.center_cube.setColor(0.6, 0.3, 0.1, 1.0) 

        # --- 2. Particle Task Setup (Részecske indítási feladat) ---
        # Task to continuously spawn new particles
        self.taskMgr.doMethodLater(0.03, self.spawn_particle, "SpawnParticleTask")
        
        # Task to gently rotate the center cube
        self.taskMgr.add(self.rotate_cube, "RotateCubeTask")

    def rotate_cube(self, task):
        """Rotates the center cube with a slightly sharper motion."""
        self.center_cube.setH(self.center_cube.getH() + 0.2)
        self.center_cube.setP(self.center_cube.getP() + 0.1)
        return Task.cont

    def spawn_particle(self, task):
        """Spawns a new particle (small cube) and starts its life cycle."""
        
        if len(self.active_particles) >= self.max_particles:
            return Task.cont

        # 1. Create the particle (small cube mesh)
        particle = create_cube_mesh()
        particle.reparentTo(self.render)
        
        # --- Initial Properties ---
        life_duration = 1.0 + random.uniform(0.5, 1.0) # 1.5 to 2.0 seconds
        
        # Start position: slightly outside the center cube
        rand_offset = LVector3(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        start_pos = self.center_pos + rand_offset.normalized() * 1.6
        
        particle.setPos(start_pos)
        initial_scale = 0.2 + random.uniform(-0.05, 0.05)
        particle.setScale(initial_scale)
        
        # Define velocity and end position (move outwards)
        outward_direction = start_pos - self.center_pos
        outward_direction.normalize()
        
        # End position: further away from the center
        outward_speed = 5.0 + random.uniform(3.0, 6.0)
        end_pos = start_pos + outward_direction * outward_speed

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
        
        # Rotation: Add fast particle rotation for pixelated chaos effect
        particle_rotation = particle.hprInterval(life_duration, LVector3(random.randint(180, 720), random.randint(180, 720), random.randint(180, 720)))
        
        # Color: Retro sárga/narancsról sötét, átlátszóra halványodás
        color_start = VBase4(1.0, 0.7, 0.2, 1.0) # Bright Retro Orange/Yellow
        color_end = VBase4(0.5, 0.3, 0.1, 0.0) # Dark, Transparent (ash)
        
        color_interval = LerpFunc(
            self.update_color_and_alpha,
            duration=life_duration,
            fromData=0.0,
            toData=1.0,
            extraArgs=[particle, color_start, color_end]
        )

        # 3. Combine animations and deletion (Life Cycle)
        life_cycle = Sequence(
            Parallel(move_interval, scale_down, color_interval, particle_rotation),
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
    app = RetroCubeParticles()
    app.run()