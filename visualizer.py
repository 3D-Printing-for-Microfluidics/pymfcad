import numpy as np
import trimesh
from trimesh.scene import Scene
from trimesh.visual import ColorVisuals

from microfluidic_designer import NetType, Backend, Manifold3D, get_backend, Component, Port, Device

class Visualizer:
    def __init__(self):
        self.backend = get_backend()

    def nettype_to_rgba(self, nt:NetType) -> tuple[float, float, float, float]:
        r, g, b, a = nt.color
        return (r/255, g/255, b/255, a/255)

    def porttype_to_color(self, port_type:Port.PortType):
        if port_type == Port.PortType.IN:
            return (0, 255, 0, 255)  # Green
        elif port_type == Port.PortType.OUT:
            return (255, 0, 0, 255)  # Red
        elif port_type == Port.PortType.INOUT:
            return (0, 0, 255, 255)  # Blue
        else:
            return (255, 255, 255, 255)  # White


    def draw_bounding_box(self, scene, size, origin:tuple[int, int, int], color:tuple[int, int, int], px_size:float, layer_size:float, name:str="bbox"):
        # draw lines for component bounding box
        bbox_size = (size[0]*px_size, size[1]*px_size, size[2]*layer_size)
        bbox_origin = (origin[0]*px_size, origin[1]*px_size, origin[2]*layer_size)
        translation = trimesh.transformations.translation_matrix(bbox_origin)
        translation[:3, 3] = [o + s / 2 for o, s in zip(bbox_origin, bbox_size)]
        bbox = trimesh.path.creation.box_outline(
            extents=np.array(bbox_size),
            transform=translation
        )
        bbox.colors = [color]
        scene.add_geometry(bbox)#, node_name=name)

    def draw_port(self, scene:Scene, port: Port, component: Component):
        vector = np.array(port.pointing_vector_to_vector())
        adjusted_pos = np.array(port.get_adjusted_position())

        # Scale to real-world units
        scale = np.array([
            component.px_size,
            component.px_size,
            component.layer_size
        ])
        size_scaled = np.array(port.size) * scale
        pos_scaled = adjusted_pos * scale

        # Center the bounding box
        bbox_center = pos_scaled + size_scaled / 2

        # Draw port bounding box
        self.draw_bounding_box(
            scene,
            size=port.size,
            origin=adjusted_pos,
            color=self.porttype_to_color(port.type),
            px_size=component.px_size,
            layer_size=component.layer_size,
            name=f"port-{port.name}"
        )

        # Arrow positioning
        arrow_length = np.dot(size_scaled, np.abs(vector))  # length in the pointing direction
        arrow_radius = arrow_length * 0.25

        arrow_position = np.array(bbox_center)
        arrow_direction = vector / np.linalg.norm(vector)

        def make_arrow(length:float, reflect:bool=False, half_size:bool=False):
            # Align Z axis with arrow direction
            axis = np.array([0, 0, 1])
            if not np.allclose(axis, arrow_direction):
                rot = trimesh.geometry.align_vectors(axis, arrow_direction)
            else:
                rot = np.eye(4)
            reflect_matrix = trimesh.transformations.reflection_matrix(
                point=[0, 0, length / 2], normal=[0, 0, 1]
            ) if reflect else np.eye(4)
            transform = rot @ reflect_matrix

            arrow = trimesh.creation.cone(
                radius=arrow_radius,
                height=length,
                sections=8,
                transform=transform
            )

            center_offset = np.array([0,0,0])
            if half_size:
                if not reflect:
                    center_offset = vector * (arrow_length)
            else:
                center_offset = vector * (arrow_length / 2)

            arrow.apply_translation(arrow_position - center_offset)
            arrow.visual.vertex_colors = self.porttype_to_color(port.type)
            return arrow

        if port.type == Port.PortType.INOUT:
            arrow_length = arrow_length/2
            scene.add_geometry(make_arrow(arrow_length, reflect=True, half_size=True))
            scene.add_geometry(make_arrow(arrow_length, reflect=False, half_size=True))

        # IN arrow
        if port.type == Port.PortType.IN:
            scene.add_geometry(make_arrow(arrow_length, reflect=True))

        # OUT arrow
        if port.type == Port.PortType.OUT:
            scene.add_geometry(make_arrow(arrow_length, reflect=False))

    def manifold3d_shape_to_trimesh(self, shape:Backend.Shape) -> trimesh.Trimesh:
        # mesh = shape.object.to_trimesh()  # You must implement or provide this
        m = shape.object.to_mesh()
        tm = trimesh.Trimesh(vertices=m.vert_properties, faces=m.tri_verts)
        rgba = self.nettype_to_rgba(shape.nettype)
        tm.visual = ColorVisuals(tm, vertex_colors=[rgba] * len(tm.vertices))
        return tm

    def mesh_component_recursive(self, component: Component, wireframe_bulk:bool=False):
        scene = Scene()

        def recurse(comp:Component, parent_name:str="", wireframe_bulk:bool=False):
            name = f"{parent_name}/{comp.name}" if parent_name else comp.name

            # draw subcomponents (if not inverted device)
            if not(type(comp) == Device and comp.inverted):
                for sub in comp.subcomponents:
                    recurse(sub, name)

            # draw bulk shapes (if device and not inverted)
            if type(comp) == Device and not comp.inverted:
                for bulk in comp.bulk_shape:
                    if type(self.backend) == Manifold3D:
                        mesh = self.manifold3d_shape_to_trimesh(bulk)
                        if wireframe_bulk:
                            edges = mesh.edges_unique
                            vertices = mesh.vertices
                            entities = [trimesh.path.entities.Line([e[0], e[1]]) for e in edges]
                            mesh = trimesh.path.Path3D(entities=entities, vertices=vertices)
                    else:
                        mesh = None
                        print("Visualizer only supports Manifold3D backend.")
                    scene.add_geometry(mesh)#, node_name=f"{name}-{id(shape)}")

            # draw shapes (will also draw an inverted device)
            for shape in comp.model:
                if type(self.backend) == Manifold3D:
                    mesh = self.manifold3d_shape_to_trimesh(shape)
                else:
                    mesh = None
                    print("Visualizer only supports Manifold3D backend.")
                scene.add_geometry(mesh)#, node_name=f"{name}-{id(shape)}")

            # draw ports
            for port in comp.ports:
                self.draw_port(scene, port, comp)
                
        recurse(component, wireframe_bulk=wireframe_bulk)

        # draw component bounding box
        self.draw_bounding_box(
            scene,
            size=component.size,
            origin=component.position,
            color=(0, 0, 0, 255),
            px_size=component.px_size,
            layer_size=component.layer_size
        )
        
        return scene
        # return scene.to_mesh() # for flattening
        # return scene.to_geometry() # for flattening