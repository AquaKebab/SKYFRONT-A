import math

from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, NodePath, Vec3,
)

_FACES = (
    (Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(0, 1, 0)),
    (Vec3(0, 0, -1), Vec3(0, 1, 0), Vec3(1, 0, 0)),
    (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)),
    (Vec3(-1, 0, 0), Vec3(0, 0, 1), Vec3(0, 1, 0)),
    (Vec3(0, 1, 0), Vec3(0, 0, 1), Vec3(1, 0, 0)),
    (Vec3(0, -1, 0), Vec3(1, 0, 0), Vec3(0, 0, 1)),
)


def _format():
    return GeomVertexFormat.getV3n3c4t2()


def make_box(name, size_x, size_y, size_z, color):
    """Параллелепипед с UV-развёрткой; начало координат — центр основания."""
    vdata = GeomVertexData(name, _format(), Geom.UHStatic)
    vdata.setNumRows(24)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    colour = GeomVertexWriter(vdata, "color")
    texcoord = GeomVertexWriter(vdata, "texcoord")

    hx, hy, hz = size_x / 2.0, size_y / 2.0, size_z / 2.0
    triangles = GeomTriangles(Geom.UHStatic)
    index = 0
    uvs = ((0, 0), (1, 0), (1, 1), (0, 1))

    for n, u, v in _FACES:
        for corner, (su, sv) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            p = n + u * su + v * sv
            vertex.addData3f(p.x * hx, p.y * hy, p.z * hz + hz)
            normal.addData3f(n.x, n.y, n.z)
            colour.addData4f(color[0], color[1], color[2], color[3])
            texcoord.addData2f(uvs[corner][0], uvs[corner][1])

        triangles.addVertices(index, index + 1, index + 2)
        triangles.addVertices(index, index + 2, index + 3)
        index += 4

    geom = Geom(vdata)
    geom.addPrimitive(triangles)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def make_cylinder(name, radius, height, color, segments=12, top_radius=None):
    """Цилиндр или конус вдоль Z, с UV-развёрткой."""
    if top_radius is None:
        top_radius = radius

    vdata = GeomVertexData(name, _format(), Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    colour = GeomVertexWriter(vdata, "color")
    texcoord = GeomVertexWriter(vdata, "texcoord")
    triangles = GeomTriangles(Geom.UHStatic)

    def add_vertex(x, y, z, nx, ny, nz, u, v):
        vertex.addData3f(x, y, z)
        normal.addData3f(nx, ny, nz)
        colour.addData4f(color[0], color[1], color[2], color[3])
        texcoord.addData2f(u, v)

    slope = radius - top_radius
    length = math.sqrt(height * height + slope * slope)
    if length < 1e-6:
        length = 1.0

    for i in range(segments + 1):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        nx, ny, nz = ca * height / length, sa * height / length, slope / length
        add_vertex(ca * radius, sa * radius, 0.0, nx, ny, nz,
                   float(i) / segments, 0.0)
        add_vertex(ca * top_radius, sa * top_radius, height, nx, ny, nz,
                   float(i) / segments, 1.0)

    for i in range(segments):
        b0, t0 = 2 * i, 2 * i + 1
        b1, t1 = 2 * (i + 1), 2 * (i + 1) + 1
        triangles.addVertices(b0, b1, t1)
        triangles.addVertices(b0, t1, t0)

    if top_radius > 0.0:
        center = vdata.getNumRows()
        add_vertex(0, 0, height, 0, 0, 1, 0.5, 0.5)
        ring = vdata.getNumRows()
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            ca, sa = math.cos(a), math.sin(a)
            add_vertex(ca * top_radius, sa * top_radius, height,
                       0, 0, 1, 0.5 + ca * 0.5, 0.5 + sa * 0.5)
        for i in range(segments):
            triangles.addVertices(center, ring + i, ring + (i + 1) % segments)

    center = vdata.getNumRows()
    add_vertex(0, 0, 0, 0, 0, -1, 0.5, 0.5)
    ring = vdata.getNumRows()
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        add_vertex(ca * radius, sa * radius, 0, 0, 0, -1,
                   0.5 + ca * 0.5, 0.5 + sa * 0.5)
    for i in range(segments):
        triangles.addVertices(center, ring + (i + 1) % segments, ring + i)

    geom = Geom(vdata)
    geom.addPrimitive(triangles)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)
