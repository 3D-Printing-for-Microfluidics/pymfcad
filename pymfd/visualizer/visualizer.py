import numpy as np
import trimesh
from trimesh.scene import Scene
from trimesh.visual import ColorVisuals

from ..microfluidic_designer import get_backend, Component, Port, Device
from ..backend import Backend, Manifold3D, Color

class Visualizer:
    def __init__(self):
        self.backend = get_backend()

    def draw_bounding_box(self, scene, size, origin:tuple[int, int, int], color:Color, px_size:float, layer_size:float, name:str="bbox"):
        # draw lines for component bounding box
        bbox_size = (size[0]*px_size, size[1]*px_size, size[2]*layer_size)
        bbox_origin = (origin[0]*px_size, origin[1]*px_size, origin[2]*layer_size)
        translation = trimesh.transformations.translation_matrix(bbox_origin)
        translation[:3, 3] = [o + s / 2 for o, s in zip(bbox_origin, bbox_size)]
        bbox = trimesh.path.creation.box_outline(
            extents=np.array(bbox_size),
            transform=translation
        )
        bbox.colors = [color.to_rgba()]
        scene.add_geometry(bbox)#, node_name=name)

    def draw_port(self, scene:Scene, port: Port, component: Component):
        vector = np.array(port.to_vector())
        adjusted_pos = np.array(port.get_origin())

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
            color=port.get_color(),
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
            arrow.visual.vertex_colors = port.get_color().to_rgba()
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
        rgba = shape.color.to_float()
        tm.visual = ColorVisuals(tm, vertex_colors=[rgba] * len(tm.vertices))
        return tm

    def mesh_component_recursive(self, component: Component, wireframe_bulk:bool=False):
        scene = Scene()

        bulk_manifolds = {}
        manifolds = {}

        def recurse(comp:Component, parent_name:str="", wireframe_bulk:bool=False):
            name = f"{parent_name}/{comp.name}" if parent_name else comp.name

            # draw subcomponents (if not inverted device)
            if not(type(comp) == Device and comp.inverted):
                for sub in comp.subcomponents:
                    recurse(sub, name)

            # draw bulk shapes (if device and not inverted)
            if type(comp) == Device and not comp.inverted:
                for bulk in comp.bulk_shape:
                    key = str(bulk.color)
                    if key in bulk_manifolds.keys():
                        bulk_manifolds[key] += bulk
                    else:
                        bulk_manifolds[key] = bulk

            # draw shapes (will also draw an inverted device)
            for shape in comp.shapes:
                key = str(shape.color)
                if key in manifolds.keys():
                    manifolds[key] += shape
                else:
                    manifolds[key] = shape

            # draw ports
            if type(self.backend) == Manifold3D:
                route_names = []
                if comp.parent is not None:
                    for s in comp.parent.shapes:
                        if "__to__" in s.name:
                            route_names.append(s.name)
                for port in comp.ports:
                    draw_port = True
                    for n in route_names:
                        if port.get_name() in n:
                            draw_port = False
                    if draw_port:
                        self.draw_port(scene, port, comp)
            else:
                print("Visualizer only supports Manifold3D backend.")
                
        recurse(component, wireframe_bulk=wireframe_bulk)

        for m in manifolds.values():
            mesh = self.manifold3d_shape_to_trimesh(m)
            scene.add_geometry(mesh)#, node_name=f"{name}-{id(shape)}")

        for m in bulk_manifolds.values():
            mesh = self.manifold3d_shape_to_trimesh(m)
            if wireframe_bulk:
                edges = mesh.edges_unique
                vertices = mesh.vertices
                entities = [trimesh.path.entities.Line([e[0], e[1]]) for e in edges]
                mesh = trimesh.path.Path3D(entities=entities, vertices=vertices)
            scene.add_geometry(mesh)#, node_name=f"{name}-{id(shape)}")

        # draw component bounding box
        self.draw_bounding_box(
            scene,
            size=component.size,
            origin=component.position,
            color=Color.from_name("black", 255),
            px_size=component.px_size,
            layer_size=component.layer_size
        )
        
        return scene
        # return scene.to_mesh() # for flattening
        # return scene.to_geometry() # for flattening