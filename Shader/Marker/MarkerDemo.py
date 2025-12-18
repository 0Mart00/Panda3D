from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Shader, Geom, GeomNode, GeomVertexData, GeomVertexFormat, 
    GeomVertexWriter, GeomTriangles, NodePath, Vec4
)

class MarkerDemo(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # 1. Generate the Cube from Vertices
        self.cube_np = self.create_procedural_cube()
        self.cube_np.reparent_to(self.render)
        self.cube_np.set_pos(0, 10, 0)
        
        # Make it spin
        self.cube_np.hprInterval(10, (360, 360, 0)).loop()

        # 2. Load Shaders
        my_shader = Shader.load(Shader.SL_GLSL, "marker.vert", "marker.frag")
        self.cube_np.set_shader(my_shader)

        # 3. Set Uniforms for the Marker Look
        self.cube_np.set_shader_input("u_colorSteps", 3.0)      # 3 distinct color levels
        self.cube_np.set_shader_input("u_noiseStrength", 0.08)  # Subtle ink texture
        self.cube_np.set_shader_input("u_outlineWidth", 0.45)   # Threshold for edge ink
        self.cube_np.set_shader_input("u_baseColor", Vec4(0.2, 0.6, 0.9, 1.0)) # Cyan marker

    def create_procedural_cube(self):
        # Format: Vertex + Normal + UV
        vformat = GeomVertexFormat.get_v3n3t2()
        vdata = GeomVertexData('cube', vformat, Geom.UH_static)

        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        texcoord = GeomVertexWriter(vdata, 'texcoord')

        # Helper to add a face
        def make_face(v1, v2, v3, v4, n):
            # Triangle 1
            vertex.add_data3(v1); normal.add_data3(n); texcoord.add_data2(0, 0)
            vertex.add_data3(v2); normal.add_data3(n); texcoord.add_data2(1, 0)
            vertex.add_data3(v3); normal.add_data3(n); texcoord.add_data2(1, 1)
            # Triangle 2
            vertex.add_data3(v1); normal.add_data3(n); texcoord.add_data2(0, 0)
            vertex.add_data3(v3); normal.add_data3(n); texcoord.add_data2(1, 1)
            vertex.add_data3(v4); normal.add_data3(n); texcoord.add_data2(0, 1)

        # Define corners
        p1, p2 = (-1, -1, 1), (1, -1, 1)
        p3, p4 = (1, 1, 1), (-1, 1, 1)
        p5, p6 = (-1, -1, -1), (1, -1, -1)
        p7, p8 = (1, 1, -1), (-1, 1, -1)

        # Build Faces
        make_face(p1, p2, p3, p4, (0, 0, 1))  # Top
        make_face(p5, p8, p7, p6, (0, 0, -1)) # Bottom
        make_face(p1, p4, p8, p5, (-1, 0, 0)) # Left
        make_face(p2, p6, p7, p3, (1, 0, 0))  # Right
        make_face(p1, p5, p6, p2, (0, -1, 0)) # Front
        make_face(p4, p3, p7, p8, (0, 1, 0))  # Back

        geom = Geom(vdata)
        tris = GeomTriangles(Geom.UH_static)
        tris.add_next_vertices(36) # 6 faces * 2 tris * 3 verts
        geom.add_primitive(tris)

        node = GeomNode('gnode')
        node.add_geom(geom)
        return NodePath(node)

app = MarkerDemo()
app.run()