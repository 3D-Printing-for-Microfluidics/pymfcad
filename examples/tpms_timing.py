# ############### 1 Test all basic components ##################
component = Component(
    size=(2560, 1600, 10), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
)
chan_size = (8, 8, 6)
# Add label
component.add_label("default", Color.from_rgba((0, 255, 0, 127)))
# Add a shape
# TIME DIFFERENT TPMS LOADING METHODS
import time
from pymfd.backend import TPMS

start_time = time.time()
for i in range(0, 2):
    for j in range(0, 2):
        for k in range(25):
            component.add_shape(
                f"import_model_{i}{j}{k}",
                component.import_model("examples/Diamond_51.stl")
                .resize((10, 10, 8))
                .translate((10 * i, 10 * j, 8 * k)),
                label="default",
            )
end_time = time.time()
print(f"Import: {end_time - start_time:.2f} seconds")
start_time = time.time()
for i in range(0, 2):
    for j in range(3, 5):
        for k in range(25):
            component.add_shape(
                f"tpms_njit_{i}{j}{k}",
                component.make_tpms_cell(
                    func=TPMS.diamond, size=(10, 10, 8), fill=0.0, refinement=25
                ).translate((10 * i, 10 * j, 8 * k)),
                label="default",
            )
end_time = time.time()
print(f"NJIT Many TPMS: {end_time - start_time:.2f} seconds")
start_time = time.time()

component.add_shape(
    f"tpms_njit_large_eval",
    component.make_tpms_cell(
        func=TPMS.diamond,
        size=(10, 10, 8),
        cells=(2, 2, 25),
        fill=0.0,
        refinement=25,
    ).translate((30, 30, 0)),
    label="default",
)
end_time = time.time()
print(f"NJIT Large TPMS: {end_time - start_time:.2f} seconds")

# Mesh the component
component.preview()
