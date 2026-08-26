# PyMFCAD Cheat Sheet (One‑Page Reference)

Quick reference to build, render, and slice a device.

## Core classes

- `Component(size, px_size, layer_size, quiet=False)`
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
- `TPMS(size, function, period, threshold, quiet=False) available functions include gyroid, diamond, schwarz_p, fischer_koch_s, double_diamond and double_gyroid`

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

Copying:

- copy()
- Must be done before adding as subcomponent

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

## Print File Generation

Settings objects (key parameters):

- `Printer(name, light_engines, xy_stage_available=False, vacuum_available=False, default_position_settings=PositionSettings())`
- `LightEngine(px_size, px_count, wavelengths, default_exposure_settings=[ExposureSettings()], grayscale_available=[False], settle_time_ms, stitched_px_overlap, x_offset_limits, y_offset_limits)`
- `ResinType(bulk_exposure, exposure_offset=0.0, monomer=[...], uv_absorbers=[...], initiators=[...], additives=[...])`
- `PositionSettings(distance_up, initial_wait, up_speed, up_acceleration, up_wait, down_speed, down_acceleration, final_wait, special_layer_techniques=[...])`
- `ExposureSettings(grayscale_correction, bulk_exposure_multiplier, power_setting, wavelength, relative_focus_position, wait_before_exposure, wait_after_exposure, special_image_techniques=[...])`

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

Top‑level defaults:

- `device.add_default_position_settings(PositionSettings(...), label)`
- `device.add_default_exposure_settings(ExposureSettings(...), label)`
- `device.set_burn_in_exposure([t1, t2, ...], label)`

PrintFileGenerator:

- `PrintFileGenerator(filename, author, purpose, description, component, workspaces, printer, resin, special_print_techniques, minimize_file=True, zip_output=False)`
- `print_file_gen.run()`

Workspaces:

- Workspace(printer, pixel_size, exposure_abs_pos_um, light_engine_stitching=(1,1))
- workspace.add_component(name, component, centered=True)
- workspace.adjust_subcomponent_light_engine_position(subcomponent_fqn, exposure_rel_pos_um)

Stitching notes:

- light_engine_stitching > (1,1) requires printer `xy_stage_available=True`
- Component is centered by default, can be adjusted if custom workspace(s) is/are used; per‑tile offsets are written in JSON
- Use light_engine `stitched_px_overlap` to overlap tiles

## Regional settings

- `component.add_regional_settings(name, shape, settings, label)`
- `ExposureSettings(bulk_exposure_multiplier, power_setting, wavelength, relative_focus_position, wait_before_exposure, wait_after_exposure, special_image_techniques=[...])`
- `PositionSettings(distance_up, initial_wait, up_speed, up_acceleration, up_wait, down_speed, down_acceleration, final_wait, special_layer_techniques=[...])`
- `MembraneSettings(exposure_settings, max_membrane_thickness_um, dilation_px)`
- `SecondaryDoseSettings(edge_bulk_exposure_multiplier, edge_erosion_px, edge_dilation_px, roof_bulk_exposure_multiplier, roof_erosion_px, roof_layers_above)`

## Global tessellation (optional)

- `set_fn(value)`

