from shapely.geometry import Polygon


def line_to_points(line):
    def convert_number(string):
        if "/" in string:
            n, d = string.split("/")
            return float(n) / float(d)  # This is a format that CGAL uses for its exports.
        else:
            return float(string)

    points = list()
    content = line.split()
    n = int(content[0])
    for i in range(n):
        x = content[2 * i + 1]
        y = content[2 * i + 2]
        points.append((convert_number(x), convert_number(y)))

    return points


def read_cgal_polygon(file_name) -> Polygon:
    with open(file_name) as f:
        f.seek(0)
        lines = f.readlines()
        if not lines:
            raise ValueError("File seems to be empty")

        polygons = [line_to_points(line) for line in lines]

    return Polygon(polygons[0], polygons[1:])


def point_array_to_list(array, close_circuit=False):
    polygon = list()
    for p in array:
        polygon.append([p["x"], p["y"]])

    if close_circuit:
        polygon.append(polygon[0])

    return polygon


def point_array_to_polygon(array):
    return Polygon(point_array_to_list(array))
