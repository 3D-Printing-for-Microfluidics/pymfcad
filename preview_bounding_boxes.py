import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def draw_3d_bounding_boxes(boxes, boxes2, color='cyan', edge_color='k', alpha=0.2):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for box in boxes:
        x_min, y_min, z_min, x_max, y_max, z_max = box

        # Define the 8 vertices of the bounding box
        vertices = [
            [x_min, y_min, z_min],
            [x_max, y_min, z_min],
            [x_max, y_max, z_min],
            [x_min, y_max, z_min],
            [x_min, y_min, z_max],
            [x_max, y_min, z_max],
            [x_max, y_max, z_max],
            [x_min, y_max, z_max],
        ]

        # Define the 6 faces of the box (each face is a list of 4 vertex indices)
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
            [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
            [vertices[0], vertices[1], vertices[5], vertices[4]],  # front
            [vertices[2], vertices[3], vertices[7], vertices[6]],  # back
            [vertices[1], vertices[2], vertices[6], vertices[5]],  # right
            [vertices[0], vertices[3], vertices[7], vertices[4]],  # left
        ]

        box_poly = Poly3DCollection(faces, alpha=alpha, facecolors=color, edgecolors=edge_color)
        ax.add_collection3d(box_poly)

    for box in boxes2:
        x_min, y_min, z_min, x_max, y_max, z_max = box

        # Define the 8 vertices of the bounding box
        vertices = [
            [x_min, y_min, z_min],
            [x_max, y_min, z_min],
            [x_max, y_max, z_min],
            [x_min, y_max, z_min],
            [x_min, y_min, z_max],
            [x_max, y_min, z_max],
            [x_max, y_max, z_max],
            [x_min, y_max, z_max],
        ]

        # Define the 6 faces of the box (each face is a list of 4 vertex indices)
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
            [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
            [vertices[0], vertices[1], vertices[5], vertices[4]],  # front
            [vertices[2], vertices[3], vertices[7], vertices[6]],  # back
            [vertices[1], vertices[2], vertices[6], vertices[5]],  # right
            [vertices[0], vertices[3], vertices[7], vertices[4]],  # left
        ]

        box_poly = Poly3DCollection(faces, alpha=alpha, facecolors="red", edgecolors=edge_color)
        ax.add_collection3d(box_poly)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.tight_layout()
    plt.show()

# Example usage:
bounding_boxes = [(18, 35, 40, 54, 71, 64), (52, 35, 40, 88, 71, 64), (25, 42, 30, 47, 64, 46), (24, 63, 34, 48, 87, 52), (24, 63, 46, 48, 87, 64), (59, 42, 30, 81, 64, 46), (58, 63, 34, 82, 87, 52), (58, 19, 
46, 82, 43, 64)]


boxes_of_intrest = [(67, 71, 52, 75, 79, 58),
(65, 71, 52, 73, 79, 58),
(66, 72, 52, 74, 80, 58),
(66, 70, 52, 74, 78, 58),
(66, 71, 53, 74, 79, 59),
(66, 71, 51, 74, 79, 57)]

draw_3d_bounding_boxes(bounding_boxes,boxes_of_intrest)
