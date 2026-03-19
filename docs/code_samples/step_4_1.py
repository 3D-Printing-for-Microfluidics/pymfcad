
import pymfcad

component = pymfcad.Component(
    size=(120, 40, 10), # X pixel count, Y pixel count, Z layer count
    position=(0, 0, 0),
    px_size=0.0076,
    layer_size=0.01,
)

component.add_label("default", pymfcad.Color.from_rgba((0, 255, 0, 255)))
component.add_label("bulk", pymfcad.Color.from_name("aqua", 127))

hello = pymfcad.TextExtrusion("Hello World!", height=1, font_size=15)
hello.translate((5, 5, 9))
component.add_void("hello", hello, label="default")

bulk_cube = pymfcad.Cube((120, 40, 10))
component.add_bulk("bulk_shape", bulk_cube, label="bulk")

component.preview()