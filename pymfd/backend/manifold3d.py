from __future__ import annotations

import os
import trimesh
import freetype
import functools
import numpy as np
from trimesh.scene import Scene
from typing import TYPE_CHECKING
from shapely.affinity import scale
from shapely.geometry import Polygon
from trimesh.visual import ColorVisuals
from manifold3d import set_circular_segments, Manifold, Mesh, CrossSection

from pymfd.backend import Color

if TYPE_CHECKING:
    from collections.abs import Callable
    from pymfd import Component, Port, Device

def _is_integer(val: float) -> bool:
    return abs(val - round(val)) < 1e-6

class Manifold3D():
    """
    Manifold3D backend.
    """
    def set_fn(self, fn):
        """
        Set the number of facets for the shapes.
        """
        set_circular_segments(fn)

    class Shape():
        """
        Manifold3D shape.
        """
        def __init__(self, px_size:float, layer_size:float):
            self.name = None
            self.parent = None
            self.color = None
            self.px_size = px_size
            self.layer_size = layer_size
            self.object = None
            self.keepouts = []

        def _translate_keepouts(self, translation: tuple[float, float, float]):
            """
            Translate the keepouts.

            Input:
            - translation (tuple[float, float, float]): The translation.
            """
            dx, dy, dz = translation
            self.keepouts = [
                [x0 + dx, y0 + dy, z0 + dz, x1 + dx, y1 + dy, z1 + dz]
                for x0, y0, z0, x1, y1, z1 in self.keepouts
            ]

        def _rotate_point(self, point:tuple[float, float, float], rotation:tuple[float, float, float]):
            """
            Rotate a point around origin (0,0,0) with Euler angles (in degrees) in XYZ order.
            
            Input:
            - point (tuple[float, float, float]): The point to rotate.
            - rotation (tuple[float, float, float]): The rotation.
            """
            # Convert degrees to radians
            rx, ry, rz = np.radians(rotation)
            x, y, z = point

            # Rotate around X
            cos_rx, sin_rx = np.cos(rx), np.sin(rx)
            y, z = y * cos_rx - z * sin_rx, y * sin_rx + z * cos_rx

            # Rotate around Y
            cos_ry, sin_ry = np.cos(ry), np.sin(ry)
            x, z = x * cos_ry + z * sin_ry, -x * sin_ry + z * cos_ry

            # Rotate around Z
            cos_rz, sin_rz = np.cos(rz), np.sin(rz)
            x, y = x * cos_rz - y * sin_rz, x * sin_rz + y * cos_rz

            return [x, y, z]

        def _rotate_keepouts(self, rotation: tuple[float, float, float]):
            """
            Rotate the keepouts.

            Input:
            - rotation (tuple[float, float, float]): The rotation.
            """
            rotated_keepouts = []
            for x0, y0, z0, x1, y1, z1 in self.keepouts:
                # Get all 8 corners
                corners = [
                    [x, y, z]
                    for x in (x0, x1)
                    for y in (y0, y1)
                    for z in (z0, z1)
                ]
                rotated_corners = [self._rotate_point(pt, rotation) for pt in corners]
                xs, ys, zs = zip(*rotated_corners)
                rotated_keepouts.append([min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)])
            self.keepouts = rotated_keepouts

        def _scale_keepouts(self, scale: tuple[float, float, float]) -> None:
            """
            Scale the keepouts.

            Input:
            - scale (tuple[float, float, float]): The scale.
            """
            sx, sy, sz = scale
            self.keepouts = [
                [
                    x0 * sx,
                    y0 * sy,
                    z0 * sz,
                    x1 * sx,
                    y1 * sy,
                    z1 * sz,
                ]
                for x0, y0, z0, x1, y1, z1 in self.keepouts
            ]

        def _mirror_keepouts(self, axis: tuple[bool, bool, bool]):
            """
            Mirror the keepouts.

            Input:
            - axis (tuple[bool, bool, bool]): The axis to mirror.
            """
            flip_x, flip_y, flip_z = axis
            new_keepouts = []
            for x0, y0, z0, x1, y1, z1 in self.keepouts:
                nx0, nx1 = sorted([-x0, -x1]) if flip_x else (x0, x1)
                ny0, ny1 = sorted([-y0, -y1]) if flip_y else (y0, y1)
                nz0, nz1 = sorted([-z0, -z1]) if flip_z else (z0, z1)
                new_keepouts.append([nx0, ny0, nz0, nx1, ny1, nz1])
            self.keepouts = new_keepouts
        
        def translate(self, translation:tuple[int, int, int]) -> 'Shape':
            self._translate_keepouts(translation)
            self.object = self.object.translate((translation[0] * self.px_size, translation[1] * self.px_size, translation[2] * self.layer_size))
            return self

        def rotate(self, rotation:tuple[float, float, float]) -> 'Shape':
            self._rotate_keepouts(rotation)
            self.object = self.object.rotate(rotation)
            return self

        def resize(self, size: tuple[int, int, int]) -> 'Shape':
            # if size if 0 set it near 0
            if size[0] == 0:
                size = (0.0001, size[1], size[2])
            if size[1] == 0:
                size = (size[0], 0.0001, size[2])
            if size[2] == 0:
                size = (size[0], size[1], 0.0001)
            bounds = self.object.bounding_box()
            # convert bounds to px/layer
            bounds = [
                bounds[0] / self.px_size,
                bounds[1] / self.px_size,
                bounds[2] / self.layer_size,
                bounds[3] / self.px_size,
                bounds[4] / self.px_size,
                bounds[5] / self.layer_size
            ]
            # calculate scale factors in px/layer space
            sx = size[0] / (bounds[3] - bounds[0])
            sy = size[1] / (bounds[4] - bounds[1])
            sz = size[2] / (bounds[5] - bounds[2])

            self._scale_keepouts((sx, sy, sz))
            self.object = self.object.scale((sx, sy, sz))
            return self

        def mirror(self, axis:tuple[bool, bool, bool]) -> 'Shape':
            self._mirror_keepouts(axis)
            self.object = self.object.mirror(axis)
            return self

        def __add__(self, other:'Shape') -> 'Shape': # union
            self.keepouts.extend(other.keepouts)
            self.object = self.object + other.object
            return self

        def __sub__(self, other:'Shape') -> 'Shape': # difference
            self.object = self.object - other.object
            return self

        def hull(self, other: 'Shape') -> 'Shape':
            # Combine keepouts
            self.keepouts.extend(other.keepouts)

            # Get both bounding boxes
            b1 = self.object.bounding_box()
            b1 = (b1[0]/self.px_size, b1[1]/self.px_size, b1[2]/self.layer_size, b1[3]/self.px_size, b1[4]/self.px_size, b1[5]/self.layer_size)
            b2 = other.object.bounding_box()
            b2 = (b2[0]/self.px_size, b2[1]/self.px_size, b2[2]/self.layer_size, b2[3]/self.px_size, b2[4]/self.px_size, b2[5]/self.layer_size)

            # Determine bridge keepout bounds
            x0 = min(b1[0], b2[0])
            y0 = min(b1[1], b2[1])
            z0 = min(b1[2], b2[2])
            x1 = max(b1[3], b2[3])
            y1 = max(b1[4], b2[4])
            z1 = max(b1[5], b2[5])

            # Determine the separation axis
            size1 = (b1[3] - b1[0], b1[4] - b1[1], b1[5] - b1[2])
            size2 = (b2[3] - b2[0], b2[4] - b2[1], b2[5] - b2[2])

            center1 = [(b1[0] + b1[3]) / 2, (b1[1] + b1[4]) / 2, (b1[2] + b1[5]) / 2]
            center2 = [(b2[0] + b2[3]) / 2, (b2[1] + b2[4]) / 2, (b2[2] + b2[5]) / 2]
            deltas = [abs(center1[i] - center2[i]) for i in range(3)]

            # The separation axis is the one with the largest center delta
            sep_axis = deltas.index(max(deltas))

            # Create a bridge box between bounding boxes along the separation axis
            bridge_min = [0, 0, 0]
            bridge_max = [0, 0, 0]

            for i in range(3):
                if i == sep_axis:
                    bridge_min[i] = min(b1[i], b2[i])
                    bridge_max[i] = max(b1[i + 3], b2[i + 3])
                else:
                    bridge_min[i] = min(b1[i], b2[i])
                    bridge_max[i] = max(b1[i + 3], b2[i + 3])

            self.keepouts.append([
                bridge_min[0], bridge_min[1], bridge_min[2],
                bridge_max[0], bridge_max[1], bridge_max[2]
            ])
            
            self.object = Manifold.batch_hull([self.object, other.object])
            return self
        
        def add_bbox_to_keepout(self, bbox:tuple[float]):
            # add keepout
            bbox = (bbox[0]/self.px_size, bbox[1]/self.px_size, bbox[2]/self.layer_size, bbox[3]/self.px_size, bbox[4]/self.px_size, bbox[5]/self.layer_size)
            self.keepouts.append(bbox)

    class Cube(Shape):
        """
        Manifold3D cube.
        """
        def __init__(self, size:tuple[int, int, int], px_size:float, layer_size:float, center:bool=False, _no_validation:bool=False):
            super().__init__(px_size, layer_size)

            # shift half a pixel if odd and centered
            x = 0
            y = 0
            z = 0                 
            if center and not _no_validation:
                if size[0] %2 != 0:
                    print(f"⚠️ Centered cube x dimension is odd. Shifting 0.5 px to align with px grid")
                    x = 0.5
                if size[1] %2 != 0:
                    print(f"⚠️ Centered cube y dimension is odd. Shifting 0.5 px to align with px grid")
                    y = 0.5
                if size[2] %2 != 0:
                    print(f"⚠️ Centered cube z dimension is odd. Shifting 0.5 px to align with px grid")
                    z = 0.5

            if size[0] == 0:
                size = (0.0001, size[1], size[2])
            if size[1] == 0:
                size = (size[0], 0.0001, size[2])
            if size[2] == 0:
                size = (size[0], size[1], 0.0001)

            self.object = Manifold.cube((size[0]*px_size, size[1]*px_size, size[2]*layer_size), center=center).translate((x*px_size,y*px_size,z*layer_size))
            self.add_bbox_to_keepout(self.object.bounding_box())

    class Cylinder(Shape):
        """
        Manifold3D cylinder.
        """
        def __init__(self, height:int, radius:float=None, bottom_r:float=None, top_r:float=None, px_size:float=None, layer_size:float=None, center_xy:bool=True, center_z:bool=False, fn:int=0):
            super().__init__(px_size, layer_size)

            # only allow radiuses to be multiples of 0.5
            if radius is not None:
                if not _is_integer(radius*2):
                    raise ValueError("Cylinder radius must be a multiple of 0.5")
            if bottom_r is not None:
                if not _is_integer(bottom_r*2):
                    raise ValueError("Cylinder radius (bottom) must be a multiple of 0.5")
            if top_r is not None:
                if not _is_integer(top_r*2):
                    raise ValueError("Cylinder radius (top) must be a multiple of 0.5")

            # validate shape is fully constrained
            bottom = bottom_r if bottom_r is not None else radius
            top = top_r if top_r is not None else radius
            if bottom is None or top is None:
                raise ValueError("Either radius or bottom_r and top_r must be provided.")

            if top % 2 != bottom % 2:
                raise ValueError("Cylinder top and bottom radius must both be either even or odd.")

            bottom = bottom_r if bottom_r is not None else radius
            top = top_r if top_r is not None else radius
            
            xy = 0
            z = 0
            if center_z and height %2 != 0:
                print(f"⚠️ Centered cylinder z dimension is odd. Shifting 0.5 px to align with px grid")
                z = 0.5
            if height == 0:
                height = 0.0001
            if center_xy:
                if top*2 %2 != 0: # can check either to or bottom
                    print(f"⚠️ Centered cylinder radius is odd. Shifting 0.5 px to align with px grid")
                    xy = 0.5
                self.object = Manifold.cylinder(height=height*layer_size, radius_low=bottom*px_size, radius_high=top*px_size, circular_segments=fn, center=center_z).translate((xy*px_size,xy*px_size,z*layer_size))
            else:
                radius = max(bottom, top)
                self.object = Manifold.cylinder(height=height*layer_size, radius_low=bottom*px_size, radius_high=top*px_size, circular_segments=fn, center=center_z).translate((radius*px_size,radius*px_size,z*layer_size))
            self.add_bbox_to_keepout(self.object.bounding_box())
                

    class Sphere(Shape):
        """
        Manifold3D ellipsoid.
        """
        def __init__(self, size:tuple[int, int, int], px_size:float=None, layer_size:float=None, center:bool=True, fn:int=0, _no_validation:bool=False):
            super().__init__(px_size, layer_size)
            if center:
                x = 0
                y = 0
                z = 0
                if not _no_validation:
                    if size[0] %2 != 0:
                        print(f"⚠️ Centered sphere x dimension is odd. Shifting 0.5 px to align with px grid")
                        x=0.5
                    if size[1] %2 != 0:
                        print(f"⚠️ Centered sphere y dimension is odd. Shifting 0.5 px to align with px grid")
                        y=0.5
                    if size[2] %2 != 0:
                        print(f"⚠️ Centered sphere z dimension is odd. Shifting 0.5 px to align with px grid")
                        z=0.5

            if size[0] == 0:
                size = (0.0001, size[1], size[2])
            if size[1] == 0:
                size = (size[0], 0.0001, size[2])
            if size[2] == 0:
                size = (size[0], size[1], 0.0001)

            self.object = Manifold.sphere(radius=1, circular_segments=fn)
            self.resize(size)

            if center:
                self.object = self.object.translate((x*px_size,y*px_size,z*layer_size))
            else:
                self.object = self.object.translate((size[0]/2*px_size,size[1]/2*px_size,size[2]/2*layer_size))
            self.add_bbox_to_keepout(self.object.bounding_box())

    class RoundedCube(Shape):
        """
        Manifold3D rounded cube.
        """
        def __init__(self, size:tuple[int, int, int], radius:tuple[float, float, float], px_size:float, layer_size:float, center:bool=False, fn:int=0, _no_validation:bool=False):
            super().__init__(px_size, layer_size)

            # shift half a pixel if odd and centered
            x = 0
            y = 0
            z = 0                 
            if center and not _no_validation:
                if size[0] %2 != 0:
                    print(f"⚠️ Centered rounded cube x dimension is odd. Shifting 0.5 px to align with px grid")
                    x = 0.5
                if size[1] %2 != 0:
                    print(f"⚠️ Centered rounded cube y dimension is odd. Shifting 0.5 px to align with px grid")
                    y = 0.5
                if size[2] %2 != 0:
                    print(f"⚠️ Centered rounded cube z dimension is odd. Shifting 0.5 px to align with px grid")
                    z = 0.5

            if size[0] == 0:
                size = (0.0001, size[1], size[2])
            if size[1] == 0:
                size = (size[0], 0.0001, size[2])
            if size[2] == 0:
                size = (size[0], size[1], 0.0001)

            radius = list(radius)
            if radius[0] <= 0:
                radius[0] = 0.0000001
            if radius[1] <= 0:
                radius[1] = 0.0000001
            if radius[2] <= 0:
                radius[2] = 0.0000001

            spheres = []
            for i in range(2):
                for j in range(2):
                    for k in range(2):
                        s = Manifold.sphere(radius=1, circular_segments=fn)
                        s = s.scale((radius[0]*px_size, radius[1]*px_size, radius[2]*layer_size)) 
                        _x = (size[0]/2 - radius[0]) if i else -(size[0]/2 - radius[0])
                        _y = (size[1]/2 - radius[1]) if j else -(size[1]/2 - radius[1])
                        _z = (size[2]/2 - radius[2]) if k else -(size[2]/2 - radius[2])
                        s = s.translate(((x+_x)*px_size, (y+_y)*px_size, (z+_z)*layer_size))
                        if not center:
                            s = s.translate((size[0]/2*px_size, size[1]/2*px_size, size[2]/2*layer_size))
                        spheres.append(s)

            self.object = Manifold.batch_hull(spheres)
            self.add_bbox_to_keepout(self.object.bounding_box())

    class TextExtrusion(Shape):
        """
        Abstract base class for all text extrusion shapes.
        """
        def __init__(self, text:str, height:int, font:str="arial", font_size:int=10, px_size:float=None, layer_size:float=None):
            super().__init__(px_size, layer_size)

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
            
            if height[0] == 0:
                height = 0.0001
            
            self.object = text_to_manifold(text, height=height, font_path=f"pymfd/backend/fonts/{font}.ttf")
            self.add_bbox_to_keepout(self.object.bounding_box())

    class ImportModel(Shape):
        """
        Abstract base class for all ImportModel imports.
        """
        def __init__(self, filename:str, auto_repair:bool=True, px_size:float=None, layer_size:float=None):
            super().__init__(px_size, layer_size)

            def load_3d_file_to_manifold(path, auto_repair=True):
                ext = os.path.splitext(filename)[1].lower()
                print(f"📦 Loading: {filename} (.{ext[1:]})")

                # try:
                mesh = trimesh.load(filename, force='mesh')

                if isinstance(mesh, trimesh.Scene):
                    print("🔁 Flattening scene...")
                    mesh = mesh.to_mesh()

                issues = []
                if not mesh.is_watertight:
                    issues.append("❌ Mesh is not watertight (required for Manifold3D).")
                if not mesh.is_winding_consistent:
                    issues.append("⚠️ Face winding is inconsistent (normals may be wrong).")
                if mesh.is_empty or len(mesh.faces) == 0:
                    issues.append("❌ Mesh is empty or has no faces.")
                if not mesh.is_volume:
                    issues.append("⚠️ Mesh may not define a solid volume.")

                if issues:
                    print("\n".join(issues))
                    if not auto_repair:
                        raise ValueError("Mesh has critical issues. Aborting due to `auto_repair=False`.")

                if auto_repair:
                    print("🛠 Attempting repair steps...")
                    mesh = mesh.copy()
                    trimesh.repair.fill_holes(mesh)
                    trimesh.repair.fix_normals(mesh)
                    mesh.remove_degenerate_faces()
                    mesh.remove_duplicate_faces()
                    mesh.remove_infinite_values()
                    mesh.remove_unreferenced_vertices()

                if not mesh.is_watertight:
                    raise ValueError("❌ Mesh is still not watertight after repair. Cannot proceed.")

                # Convert to MeshGL
                verts = np.asarray(mesh.vertices, dtype=np.float32)
                faces = np.asarray(mesh.faces, dtype=np.uint32)
                mesh_obj = Mesh(verts, faces)

                manifold = Manifold(mesh_obj)
                print("✅ Successfully converted mesh to Manifold.")
                return manifold

            self.object = load_3d_file_to_manifold(filename, auto_repair)
            self.add_bbox_to_keepout(self.object.bounding_box())

            # except Exception as e:
            #     raise ValueError(f"❌ Error loading mesh: {e}")
            #     print(f"🔥 Error loading mesh: {e}")
            #     return None

    class TPMS(Shape):
        @functools.cache
        def gyroid(x:float, y:float, z:float) -> bool:
            a = np.radians(360)
            return (
                np.cos(a * x) * np.sin(a * y) +
                np.cos(a * y) * np.sin(a * z) +
                np.cos(a * z) * np.sin(a * x)
            )

        @functools.cache
        def diamond(x:float, y:float, z:float) -> bool:
            a = np.radians(360)
            return (
                np.sin(a*(x)) * np.sin(a*(y)) * np.sin(a*(z)) + 
                np.sin(a*(x)) * np.cos(a*(y)) * np.cos(a*(z)) + 
                np.cos(a*(x)) * np.sin(a*(y)) * np.cos(a*(z)) + 
                np.cos(a*(x)) * np.cos(a*(y)) * np.sin(a*(z))
            )
             
        def __init__(self, size:tuple[int, int, int], func:Callable[[int, int, int], int]=diamond, px_size:float=None, layer_size:float=None):
            super().__init__(px_size, layer_size)

            bounds = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]  # bounding box
            edge_length = 0.1
            self.object = Manifold.level_set(
                func,
                bounds,
                edge_length,
                level=0.0  # isosurface at 0
            )
            if size[0] == 0:
                size = (0.0001, size[1], size[2])
            if size[1] == 0:
                size = (size[0], 0.0001, size[2])
            if size[2] == 0:
                size = (size[0], size[1], 0.0001)
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

    def _manifold3d_shape_to_trimesh(self, shape:Shape) -> trimesh.Trimesh:
        # mesh = shape.object.to_trimesh()  # You must implement or provide this
        m = shape.object.to_mesh()
        tm = trimesh.Trimesh(vertices=m.vert_properties, faces=m.tri_verts)
        rgba = shape.color.to_float()
        tm.visual = ColorVisuals(tm, vertex_colors=[rgba] * len(tm.vertices))
        return tm

    def _manifold3d_shape_to_wireframe(self, shape:Shape) -> trimesh.Trimesh:
        mesh = self._manifold3d_shape_to_trimesh(shape)
        edges = mesh.edges_unique
        vertices = mesh.vertices
        entities = [trimesh.path.entities.Line([e[0], e[1]]) for e in edges]
        return trimesh.path.Path3D(entities=entities, vertices=vertices)

    def _component_to_manifold(self, component:Component, render_bulk:bool=True, do_bulk_difference:bool=True):
        bulk_manifolds = {}
        manifolds = {}
        ports = []
        def recurse(comp:Component, parent_name:str=""):
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

            # get list of routes
            route_names = []
            if comp.parent is not None:
                for s in comp.parent.shapes:
                    if "__to__" in s.name:
                        route_names.append(s.name)
            # append ports not in a route
            for port in comp.ports:
                draw_port = True
                for n in route_names:
                    if port.get_name() in n:
                        draw_port = False
                if draw_port:
                    ports.append((port, comp))
            
        recurse(component)

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

        return manifolds, bulk_manifolds, ports
        
    def render(self, component:Component, render_bulk:bool=True, do_bulk_difference:bool=True, flatten_scene:bool=True, wireframe_bulk:bool=False, show_assists:bool=False):
        scene = Scene()
        
        manifolds, bulk_manifolds, ports = self._component_to_manifold(component, render_bulk=render_bulk, do_bulk_difference=do_bulk_difference)

        if show_assists:
            for port in ports:
                p, c = port
                self._draw_port(scene, p, c)
            
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
            return scene.to_mesh() # for flattening (trimesh only)
            # return scene.to_geometry() # for flattening (also allows Path3D and Path2D)
        else:
            return scene
        

    def slice_component(self, component:Component, render_bulk:bool=True, do_bulk_difference:bool=True):
        manifolds, bulk_manifolds, _ = self._component_to_manifold(component, render_bulk=render_bulk, do_bulk_difference=do_bulk_difference)

        manifold = None
        for m in manifolds.values():
            if manifold is None:
                manifold = m
            else:
                manifold += m

        if render_bulk:
            bulk_manifold = None
            for m in bulk_manifolds.values():
                if bulk_manifold is None:
                    bulk_manifold = m
                else:
                    bulk_manifold += m
            if do_bulk_difference:
                bulk_manifold -= manifold
                manifold = bulk_manifold
            else:
                manifold += manifold

        from PIL import Image, ImageDraw

        slice_num = 0
        z_height = 0
        while z_height < component.size[2]:
            polygons = manifold.object.slice(component.position[2]*component.layer_size + z_height*component.layer_size).to_polygons()

            # # Step 2: Find bounding box of all points
            # all_points = np.vstack(polygons)
            # min_x, min_y = np.min(all_points, axis=0)
            # max_x, max_y = np.max(all_points, axis=0)

            # # Compute scale to fit image size
            # width = max_x - min_x
            # height = max_y - min_y
            # scale = min((resolution - 2 * padding) / width,
            #             (resolution - 2 * padding) / height)

            # Create a new blank grayscale image
            img = Image.new("L", (2560, 1600), 0)
            draw = ImageDraw.Draw(img)

            # if slice_num == 54:
            #     print(polygons)

            # Step 3: Draw each polygon
            for poly in polygons:
                # snap to pixel grid
                transformed = np.round(poly / component.px_size).astype(int)
                transformed[:, 1] = img.height - transformed[:, 1]
                points = [tuple(p) for p in transformed]

                # Convert poly (Nx2 numpy array) to shapely polygon and offset inward by small amount in px sdpace
                p = Polygon(points)
                px_offset = 0.1
                shrunk = p.buffer(-px_offset)
                # Only process if still valid
                if not shrunk.is_empty and shrunk.geom_type == 'Polygon':
                    coords = np.array(shrunk.exterior.coords)
                    # do floor to fix issues with polygon inclusivity
                    transformed = np.floor(coords).astype(int)
                    points = [tuple(p) for p in transformed]

                # Draw polygon filled with white (255)
                draw.polygon(points, fill=255)

            # 5. Save or show the image
            img.save(f"slice{slice_num}.png")
            img.show()

            slice_num += 1
            z_height += 1