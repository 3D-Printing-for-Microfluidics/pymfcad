# OpenMFD Cheat Sheet (One‑Page Reference)

Quick reference to build, render, and slice a device.

## Core classes

- `Component(size, position, px_size, layer_size, quiet=False)`
- `Device(name, position, layers, layer_size, px_count, px_size, quiet=False)`
- `StitchedDevice(name, position, layers, layer_size, tiles_x, tiles_y, base_px_count=(2560,1600), overlap_px=0, px_size=0.0076, quiet=False)`
- `Visitech_LRS10_Device`, `Visitech_LRS20_Device`, `Wintech_Device`
- `VariableLayerThicknessComponent(size, position, px_size, layer_sizes, quiet=False)`

## Labels and colors

- `component.add_label(name, Color)`
- `Color.from_rgba((r,g,b,a))`
- `Color.from_rgba_percent((r,g,b,a))`
- `Color.from_hex("RRGGBB", a)`
- `Color.from_name("aqua", a)`

## Shapes (geometry)

Primitives and key parameters:

- `Cube(size, center=False, quiet=False)`
- `Cylinder(height, radius, center_z=False, quiet=False)`
- `Sphere(size, quiet=False)`
- `RoundedCube(size, radius, quiet=False)`
- `TextExtrusion(text, height, font_size, quiet=False)`
- `ImportModel(path, scale, rotation, quiet=False)`
- `TPMS(size, function, period, threshold, quiet=False)`

Transforms (shapes):

- `translate((x,y,z))`, `rotate((rx,ry,rz))`, `resize((x,y,z))`, `mirror((x,y,z))`

Boolean ops:

- Union: `a + b`
- Difference: `a - b`
- Hull: `a.hull(b)`
- Copy: `a.copy()`

Add to component:

- `component.add_void(name, shape, label)`
- `component.add_bulk(name, shape, label)`

## Ports

- `Port(PortType, position, size, surface_normal)`
- `Port.PortType.IN | OUT | INOUT`
- `Port.SurfaceNormal.POS_X | NEG_X | POS_Y | NEG_Y | POS_Z | NEG_Z`
- `component.add_port(name, port)`
- `component.connect_port(port)`

## Subcomponents

Transforms (components):

- `translate((x,y,z))`, `rotate((rx,ry,rz))`, `mirror((x,y))`
- 90 degree rotations only

Add to component:

- `component.add_subcomponent(name, subcomponent, subtract_bounding_box, hide_in_render)`

Relabeling:

- `component.relabel({shape_or_name_or_fqn: label}, recursive=False)`

Helpers:

- `component.get_labels()`
- `component.get_shapes()`
- `component.get_subcomponents()`

## Polychannels

- `Polychannel([PolychannelShape, ...], quiet=False)`
- `PolychannelShape(shape_type, position, size, absolute_position=False, rotation=(0,0,0), corner_radius=0, corner_segments=10, rounded_cube_radius=(...))`
- `BezierCurveShape(control_points, bezier_segments, position, size, absolute_position=False, shape_type=..., rounded_cube_radius=(...))`

Rules:

- First shape cannot be `BezierCurveShape`
- First shape must define `shape_type`, `position`, `size`
- Last shape cannot have non‑zero `corner_radius`
- `rounded_cube` requires `rounded_cube_radius`

## Routing

- `Router(component, channel_size, channel_margin, quiet=False)`
- `router.autoroute_channel(port_a, port_b, label)`
- `router.route_with_fractional_path(port_a, port_b, steps, label)`
- `router.route_with_polychannel(port_a, port_b, shapes, label)`
- `router.finalize_routes()`

Helpers:

- `component.get_ports()`

## Preview and render

- `component.preview()`
- `component.render("file.glb")`

## Slicing

Settings objects (key parameters):

- `Settings(printer, resin, default_position_settings, default_exposure_settings, special_print_techniques=[...], user="", purpose="", description="")`
- `Printer(name, light_engines, xy_stage_available=False, vacuum_available=False)`
- `LightEngine(px_size, px_count, wavelengths, grayscale_available=[False])`
- `ResinType(monomer=[...], uv_absorbers=[...], initiators=[...], additives=[...])`
- `PositionSettings(distance_up, initial_wait, up_speed, up_acceleration, up_wait, down_speed, down_acceleration, final_wait, special_layer_techniques=[...])`
- `ExposureSettings(grayscale_correction, exposure_time, power_setting, wavelength, relative_focus_position, wait_before_exposure, wait_after_exposure, special_image_techniques=[...])`

Settings JSON I/O:

- `Settings.save(path)` / `Settings.from_file(path)`
- `Printer.save(path)` / `Printer.from_file(path)`
- `ResinType.save(path)` / `ResinType.from_file(path)`

Special techniques:

- Print:

	- `PrintUnderVacuum(enabled=False, target_vacuum_level_torr=10.0, vacuum_wait_time=0.0)`
- Position/Layer:

	- `SqueezeOutResin(enabled=False, count=0, squeeze_force=0.0, squeeze_time=0.0)`
- Image/Exposure:

	- `ZeroMicronLayer(enabled=False, count=0)`
	- `PrintOnFilm(enabled=False, distance_up_mm=0.3)`

Device‑level defaults:

- `device.add_default_position_settings(PositionSettings(...))`
- `device.add_default_exposure_settings(ExposureSettings(...))`
- `device.set_burn_in_exposure([t1, t2, ...])`

Slicer:

- `Slicer(device, settings, filename, minimize_file=True, zip_output=False)`
- `slicer.make_print_file()`

Stitching notes:

- `StitchedDevice` requires printer `xy_stage_available=True`
- Device is centered; per‑tile offsets are written in JSON
- Use `overlap_px` to overlap tiles (step = base size − overlap)

## Regional settings

- `component.add_regional_settings(name, shape, settings, label)`
- `ExposureSettings`, `PositionSettings`, `MembraneSettings`, `SecondaryDoseSettings`

## Global tessellation (optional)

- `set_fn(value)`

