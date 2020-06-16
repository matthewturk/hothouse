import numpy as np
import traittypes
import traitlets
from itertools import tee
import quaternion
import pythreejs

from plyfile import PlyData, PlyElement

from .traits_support import check_shape, check_dtype

# From itertools cookbook
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def _ensure_triangulated(faces):
    for face in faces:
        if len(face[0]) == 3:
            yield face
            continue
        # We are going to make the assumption that the face is convex
        # We choose the first vertex as our fan source
        indices, *rest = face
        base = indices[0]
        for pair in pairwise(indices[1:]):
            yield [np.array((base,) + pair)] + rest


class Model(traitlets.HasTraits):
    origin = traittypes.Array(None, allow_none=True).valid(
        check_shape(3), check_dtype("f4")
    )
    vertices = traittypes.Array(None, allow_none=True).valid(
        check_shape(None, 3), check_dtype("f4")
    )
    indices = traittypes.Array(None, allow_none=True).valid(
        check_shape(None, 3), check_dtype("i4")
    )
    attributes = traittypes.Array(None, allow_none=True)
    triangles = traittypes.Array(None, allow_none=True).valid(
        check_shape(None, 3, 3), check_dtype("f4")
    )

    @classmethod
    def from_ply(cls, filename):
        # This is probably not the absolute best way to do this.
        plydata = PlyData.read(filename)
        vertices = plydata["vertex"][:]
        faces = plydata["face"][:]
        triangles = []
        xyz_faces = []
        for face in _ensure_triangulated(faces):
            indices = face[0]
            vert = vertices[indices]
            triangles.append(np.array([vert["x"], vert["y"], vert["z"]]))
            xyz_faces.append(indices)

        xyz_vert = np.stack([vertices[ax] for ax in "xyz"], axis=-1)
        xyz_faces = np.stack(xyz_faces)
        colors = np.stack(
            [vertices["diffuse_{}".format(c)] for c in ("red", "green", "blue")],
            axis=-1,
        )
        triangles = np.array(triangles).swapaxes(1, 2)
        obj = cls(
            vertices=xyz_vert,
            indices=xyz_faces,
            attributes=colors,
            triangles=triangles,
        )

        return obj

    @property
    def geometry(self):
        attributes = dict(
            position=pythreejs.BufferAttribute(self.vertices, normalized=False),
            index=pythreejs.BufferAttribute(
                self.indices.ravel(order="C").astype("u4"), normalized=False
            ),
        )
        if self.attributes is not None:
            attributes["attributes"] = pythreejs.BufferAttribute(self.attributes)
        geometry = pythreejs.BufferGeometry(attributes=attributes)
        geometry.exec_three_obj_method("computeFaceNormals")
        return geometry

    def translate(self, delta):
        self.vertices = self.vertices + delta

    def rotate(self, q, origin="barycentric"):
        """
        This expects a quaternion as input.
        """
        pass
