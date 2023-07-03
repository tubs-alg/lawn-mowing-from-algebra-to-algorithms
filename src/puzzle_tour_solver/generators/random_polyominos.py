from shapely.geometry import Polygon, Point
import random as rd


def aspect_ratio(rectangle):
    # get coordinates of polygon vertices
    x, y = rectangle.boundary.coords.xy

    # get length of bounding box edges
    edge_length = (
        Point(x[0], y[0]).distance(Point(x[1], y[1])),
        Point(x[1], y[1]).distance(Point(x[2], y[2])),
    )

    # get length of polygon as the longest edge of the bounding box
    length = max(edge_length)

    # get width of polygon as the shortest edge of the bounding box
    width = min(edge_length)

    return width / length


def random_rectangle(min_x, min_y, max_x, max_y, tile_size, min_aspect=0.6):
    area = 0

    while area <= 0:
        x1 = rd.randint(min_x, max_x)
        y1 = rd.randint(min_y, max_y)

        x2 = rd.randint(min_x, max_x)
        y2 = rd.randint(min_y, max_y)
        poly = Polygon(
            [
                (min(x1, x2), min(y1, y2)),
                (max(x1, x2), min(y1, y2)),
                (max(x1, x2), max(y1, y2)),
                (min(x1, x2), max(y1, y2)),
            ]
        )
        if poly.area > 0 and aspect_ratio(poly) < min_aspect:
            continue

        area = poly.area

    return Polygon(
        [
            (min(x1, x2) * tile_size, tile_size * min(y1, y2)),
            (max(x1, x2) * tile_size, tile_size * min(y1, y2)),
            (max(x1, x2) * tile_size, tile_size * max(y1, y2)),
            (min(x1, x2) * tile_size, tile_size * max(y1, y2)),
        ]
    )


def random_polyomino(
    desired_size=40,
    canvas_width=10,
    canvas_height=10,
    tile_size=2,
    max_factor=2,
    min_aspect=0.0,
):
    polygon = None

    if (canvas_height * canvas_width) / (tile_size**2) < desired_size:
        raise ValueError()

    while polygon is None or abs(polygon.area) / (tile_size**2) < desired_size:

        rectangle = random_rectangle(
            0, 0, canvas_width, canvas_height, tile_size, min_aspect
        )
        assert rectangle.is_simple
        assert not rectangle.is_empty
        assert rectangle.is_valid
        assert rectangle.area > 0

        if abs(rectangle.area) / (tile_size**2) >= (desired_size / max_factor) or (
            polygon is not None and not rectangle.intersection(polygon).area > 0
        ):
            continue

        if polygon is None:
            polygon = rectangle
        else:
            polygon_test = polygon.union(rectangle)

            try:
                _ = polygon_test.boundary.coords
            except NotImplementedError:
                continue

            polygon = polygon_test

    return polygon
