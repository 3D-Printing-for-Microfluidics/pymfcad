from __future__ import annotations


import trimesh
import freetype
import numpy as np
from trimesh.scene import Scene
from typing import TYPE_CHECKING
from trimesh.visual import ColorVisuals
from manifold3d import set_circular_segments, Manifold, CrossSection

from pymfd.backend import Color, Backend

if TYPE_CHECKING:
    from collections.abs import Callable
    from pymfd import Component, Port, Device

class Manifold3D(Backend):
    """
    Manifold3D backend.
    """
    def set_fn(self, fn):
        """
        Set the number of facets for the shapes.
        """
        set_circular_segments(fn)

    class Shape(Backend.Shape):
        """
        Manifold3D shape.
        """
        def __init__(self, px_size:float, layer_size:float, allow_half_integer_translations:bool = False):
            super().__init__(px_size, layer_size, allow_half_integer_translations)
        
        def translate(self, translation:tuple[float, float, float]) -> 'Shape':
            super().translate(translation)
            self.object = self.object.translate((translation[0] * self.px_size, translation[1] * self.px_size, translation[2] * self.layer_size))
            return self

        def rotate(self, rotation:tuple[float, float, float]) -> 'Shape':
            super().rotate(rotation)
            self.object = self.object.rotate(rotation)
            return self

        def resize(self, size: tuple[int, int, int]) -> 'Shape':
            super().resize(size)
            bounds = self.object.bounding_box()
            sx = size[0]*self.px_size / (bounds[3] - bounds[0])
            sy = size[1]*self.px_size / (bounds[4] - bounds[1])
            sz = size[2]*self.layer_size / (bounds[5] - bounds[2])

            self.object = self.object.scale((sx, sy, sz))
            return self

        def mirror(self, axis:tuple[bool, bool, bool]) -> 'Shape':
            super().mirror(axis)
            self.object = self.object.mirror(axis)
            return self

        def __add__(self, other:'Shape') -> 'Shape': # union
            super().__add__(other)
            self.object = self.object + other.object
            return self

        def __sub__(self, other:'Shape') -> 'Shape': # difference
            super().__sub__(other)
            self.object = self.object - other.object
            return self

        def hull(self, other: 'Shape') -> 'Shape':
            super().hull(other)
            self.object = Manifold.batch_hull([self.object, other.object])
            return self

    class Cube(Backend.Cube, Shape):
        """
        Manifold3D cube.
        """
        def __init__(self, size:tuple[int, int, int], px_size:float, layer_size:float, center:bool=False):
            super().__init__(size, px_size, layer_size, center)
            self.object = Manifold.cube((size[0]*px_size, size[1]*px_size, size[2]*layer_size), center=center)
            self.add_bbox_to_keepout(self.object.bounding_box())

    class Cylinder(Backend.Cylinder, Shape):
        """
        Manifold3D cylinder.
        """
        def __init__(self, height:int, radius:float=None, bottom_r:float=None, top_r:float=None, px_size:float=None, layer_size:float=None, center:bool=False, fn=0):
            super().__init__(height, radius, bottom_r, top_r, px_size, layer_size, center, fn)

            bottom = bottom_r if bottom_r is not None else radius
            top = top_r if top_r is not None else radius
            self.object = Manifold.cylinder(height=height*layer_size, radius_low=bottom*px_size, radius_high=top*px_size, circular_segments=fn, center=center)
            self.add_bbox_to_keepout(self.object.bounding_box())

    class Sphere(Backend.Sphere, Shape):
        """
        Manifold3D sphere.
        """
        def __init__(self, radius:float, px_size:float=None, layer_size:float=None, fn=0):
            super().__init__(radius, px_size, layer_size, fn)
            self.object = Manifold.sphere(radius=radius*px_size, circular_segments=fn)
            self.add_bbox_to_keepout(self.object.bounding_box())

    class TextExtrusion(Backend.TextExtrusion, Shape):
        """
        Abstract base class for all text extrusion shapes.
        """
        def __init__(self, text:str, height:int, font:str="arial", font_size:int=10, px_size:float=None, layer_size:float=None):
            super().__init__(text, height, font, font_size, px_size, layer_size)

            def glyph_to_polygons(face, char, scale=1.0):
                face.load_char(char, freetype.FT_LOAD_NO_BITMAP)
                outline = face.glyph.outline
                points = np.array(outline.points, dtype=np.float32) * scale
                tags = outline.tags
                contours = outline.contours

                polys = []
                start = 0
                for end in contours:
                    contour = points[start:end + 1]
                    if len(contour) >= 3:
                        polys.append(contour)
                    start = end + 1
                return polys

            def text_to_manifold(text, font_path="Arial.ttf", font_size=50, height=1.0, spacing=1.1):
                face = freetype.Face(font_path)
                face.set_char_size(font_size * 64)

                offset_x = 0
                result = Manifold()

                for char in text:
                    if char == ' ':
                        offset_x += font_size * spacing / 4
                        continue

                    polys = glyph_to_polygons(face, char, scale=1.0 / 64.0)
                    if not polys:
                        continue

                    def is_clockwise(loop):
                        area = 0.0
                        for i in range(len(loop)):
                            x1, y1 = loop[i]
                            x2, y2 = loop[(i + 1) % len(loop)]
                            area += (x2 - x1) * (y2 + y1)
                        return area > 0

                    all_loops = []
                    for poly in polys:
                        loop = list(reversed([[float(p[0] + offset_x)*px_size, float(p[1])*px_size] for p in poly]))
                        all_loops.append(loop)

                    # Create cross section with outer + holes
                    xsec = CrossSection(all_loops)
                    if xsec.is_empty():
                        print(f"Invalid CrossSection for character '{char}'")
                        continue

                    extruded = xsec.extrude(height * layer_size)
                    if extruded.num_vert() == 0:
                        print(f"Extrusion failed for character '{char}'")
                        continue
                    result += extruded
                    offset_x += (face.glyph.advance.x / 64.0) * spacing

                return result
            
            self.object = text_to_manifold(text, height=height, font_path=f"pymfd/backend/fonts/{font}.ttf")
            self.add_bbox_to_keepout(self.object.bounding_box())

    class STL(Backend.STL, Shape):
        """
        Abstract base class for all STL imports.
        """
        def __init__(self):
            pass

    class Evaluation(Backend.Evaluation, Shape):          
        def __init__(self, size:tuple[int, int, int], func:Callable[[int, int, int], int]=Backend.Evaluation.double_diamond, px_size:float=None, layer_size:float=None):
            super().__init__(size, func, px_size, layer_size)

            bounds = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]  # bounding box
            edge_length = 0.1
            self.object = Manifold.level_set(
                func,
                bounds,
                edge_length,
                level=0.0  # isosurface at 0
            )
            self.resize(size)
            self.add_bbox_to_keepout(self.object.bounding_box())

    def _draw_bounding_box(self, scene:Scene, size:tuple[int, int, int], origin:tuple[int, int, int], color:Color, px_size:float, layer_size:float, name:str="bbox"):
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
        scene.add_geometry(bbox)

    def _draw_arrow(self, scene:Scene, length:float, position:np.typing.NDArray[np.int_], direction:np.typing.NDArray[np.int_], port:Port, reflect:bool=False, half_size:bool=False):
        # Align Z axis with arrow direction
        axis = np.array([0, 0, 1])
        if not np.allclose(axis, direction):
            rot = trimesh.geometry.align_vectors(axis, direction)
        else:
            rot = np.eye(4)
        reflect_matrix = trimesh.transformations.reflection_matrix(
            point=[0, 0, length / 2], normal=[0, 0, 1]
        ) if reflect else np.eye(4)
        transform = rot @ reflect_matrix

        arrow = trimesh.creation.cone(
            radius=length * 0.25,
            height=length,
            sections=8,
            transform=transform
        )

        center_offset = np.array([0,0,0])
        if half_size:
            if not reflect:
                center_offset = direction * (length)
        else:
            center_offset = direction * (length / 2)

        arrow.apply_translation(position - center_offset)
        arrow.visual.vertex_colors = port.get_color().to_rgba()
        scene.add_geometry(arrow)

    def _draw_port(self, scene:Scene, port: Port, component: Component):
        arrow_direction = np.array(port.to_vector())
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
        self._draw_bounding_box(
            scene,
            size=port.size,
            origin=adjusted_pos,
            color=port.get_color(),
            px_size=component.px_size,
            layer_size=component.layer_size,
            name=f"port-{port.name}"
        )

        # Arrow positioning
        arrow_length = np.dot(size_scaled, np.abs(arrow_direction))  # length in the pointing direction
        arrow_position = np.array(bbox_center)

        from pymfd import Port
        if port.type == Port.PortType.INOUT:
            arrow_length = arrow_length/2
            self._draw_arrow(scene, arrow_length, arrow_position, arrow_direction, port, reflect=True, half_size=True)
            self._draw_arrow(scene, arrow_length, arrow_position, arrow_direction, port,  reflect=False, half_size=True)

        # IN arrow
        if port.type == Port.PortType.IN:
            self._draw_arrow(scene, arrow_length, arrow_position, arrow_direction, port,  reflect=True)

        # OUT arrow
        if port.type == Port.PortType.OUT:
            self._draw_arrow(scene, arrow_length, arrow_position, arrow_direction, port,  reflect=False)

    def _manifold3d_shape_to_trimesh(self, shape:Backend.Shape) -> trimesh.Trimesh:
        # mesh = shape.object.to_trimesh()  # You must implement or provide this
        m = shape.object.to_mesh()
        tm = trimesh.Trimesh(vertices=m.vert_properties, faces=m.tri_verts)
        rgba = shape.color.to_float()
        tm.visual = ColorVisuals(tm, vertex_colors=[rgba] * len(tm.vertices))
        return tm

    def _manifold3d_shape_to_wireframe(self, shape:Backend.Shape) -> trimesh.Trimesh:
        mesh = self._manifold3d_shape_to_trimesh(shape)
        edges = mesh.edges_unique
        vertices = mesh.vertices
        entities = [trimesh.path.entities.Line([e[0], e[1]]) for e in edges]
        return trimesh.path.Path3D(entities=entities, vertices=vertices)
        
    def render(self, filename:str, component:Component, render_bulk:bool=True, do_bulk_difference:bool=True, flatten_scene:bool=True, wireframe_bulk:bool=False, show_assists:bool=False):
        scene = Scene()
        bulk_manifolds = {}
        manifolds = {}
        def recurse(comp:Component, parent_name:str="", wireframe_bulk:bool=False):
            name = f"{parent_name}/{comp.name}" if parent_name else comp.name

            # itterate subcomponents
            for sub in comp.subcomponents:
                recurse(sub, name)

            # itterate bulk shapes (if device and not inverted)
            for bulk in comp.bulk_shape:
                key = str(bulk.color)
                if key in bulk_manifolds.keys():
                    bulk_manifolds[key] += bulk
                else:
                    bulk_manifolds[key] = bulk

            # itterate shapes (will also draw an inverted device)
            for shape in comp.shapes:
                key = str(shape.color)
                if key in manifolds.keys():
                    manifolds[key] += shape
                else:
                    manifolds[key] = shape

            if show_assists:
                # get list of routes
                route_names = []
                if comp.parent is not None:
                    for s in comp.parent.shapes:
                        if "__to__" in s.name:
                            route_names.append(s.name)
                # draw ports not in a route
                for port in comp.ports:
                    draw_port = True
                    for n in route_names:
                        if port.get_name() in n:
                            draw_port = False
                    if draw_port:
                        self._draw_port(scene, port, comp)
                
        recurse(component, wireframe_bulk=wireframe_bulk)

        # do_bulk_difference=True
        # render (union of shapes and bulk shapes)          render_bulk=True, do_bulk_difference=False, flatten_scene=True, wireframe_bulk=False, show_assists=False
        # render_negative (diff of shapes and bulk shapes)  render_bulk=True, do_bulk_difference=True, flatten_scene=True, wireframe_bulk=False, show_assists=False
        # preview (shapes only)                             render_bulk=False, do_bulk_difference=False, flatten_scene=True, wireframe_bulk=False, show_assists=True
        # preview (wireframe bulk)                          render_bulk=True, do_bulk_difference=False, flatten_scene=True, wireframe_bulk=True, show_assists=True
        # preview (normal bulk)                             render_bulk=True, do_bulk_difference=False, flatten_scene=True, wireframe_bulk=False, show_assists=True
        # preview (difference)                              render_bulk=True, do_bulk_difference=True, flatten_scene=True, wireframe_bulk=False, show_assists=True
        # preview (wireframe difference)                    render_bulk=True, do_bulk_difference=True, flatten_scene=True, wireframe_bulk=True, show_assists=True

        # render_bulk=True, do_bulk_difference=True, flatten_scene=False, wireframe_bulk=False

        if do_bulk_difference:
            if not render_bulk:
                raise ValueError("Cannot render do bulk difference without rendering bulk device")

            diff = None
            for m in bulk_manifolds.values():
                if diff is None:
                    diff = m
                else:
                    diff += m
            for m in manifolds.values():
                diff -= m
            manifolds = {}
            bulk_manifolds = {"device": diff}
            
        for m in manifolds.values():
            mesh = self._manifold3d_shape_to_trimesh(m)
            scene.add_geometry(mesh)

        if render_bulk:
            for m in bulk_manifolds.values():
                if wireframe_bulk:
                    mesh = self._manifold3d_shape_to_wireframe(m)
                else:
                    mesh = self._manifold3d_shape_to_trimesh(m)
                scene.add_geometry(mesh)

        # draw component bounding box
        self._draw_bounding_box(
            scene,
            size=component.size,
            origin=component.position,
            color=Color.from_name("black", 255),
            px_size=component.px_size,
            layer_size=component.layer_size
        )
        
        if flatten_scene:
            return scene.to_mesh() # for flattening
            # return scene.to_geometry() # for flattening
        else:
            return scene
        