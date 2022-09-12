"""gustaf/gustaf/edges.py

Edges. Also known as 
"""

import numpy as np

from gustaf import settings
from gustaf import utils
from gustaf import helpers
from gustaf.vertices import Vertices


class Edges(Vertices):

    kind = "edge"

    __slots__ = [
        "_edges",
        "_edges_sorted",
    ]

    def __init__(
            self,
            vertices=None,
            edges=None,
            elements=None,
    ):
        """
        Edges. It has vertices and edges. Also known as lines.

        Parameters
        -----------
        vertices: (n, d) np.ndarray
        edges: (n, 2) np.ndarray
        """
        super().__init__(vertices=vertices)

        if edges is not None:
            self.edges = edges

        elif elements is not None:
            self.edges = elements

    @property
    def edges(self):
        """
        Returns edges. If edges is not its original property

        Parameters
        -----------
        None

        Returns
        --------
        edges: (n, 2) np.ndarray
        """
        self._logd("returning edges")
        return self._edges

    @edges.setter
    def edges(self, es):
        """
        Edges setter. Similar to vertices, this is a tracked array.

        Parameters
        -----------
        es: (n, 2) np.ndarray

        Returns
        --------
        None
        """
        self._logd("setting edges")
        self._edges = helpers.data.make_tracked_array(
            es,
            settings.INT_DTYPE
        )
        # same, but non-writeable view of tracked array
        self._const_edges = self._edges.view()
        self._const_edges.flags.writeable = False

    @property
    def elements(self):
        """
        Returns current connectivity. A short cut in FEM friendly term.
        Elements mean different things for different classes:
          Vertices -> vertices
          Edges -> edges
          Faces -> faces
          Volumes -> volumes

        Parameters
        -----------
        None

        Returns
        --------
        elements: (n, d) np.ndarray
          int. iff elements=None
        """
        elem_name = type(self).__qualname__.lower()
        self._logd(f"returning {elem_name}")

        return getattr(self, elem_name)

    @elements.setter
    def elements(self, elems):
        """
        Calls corresponding connectivity setter.
        A short cut in FEM friendly term.
          Vertices -> vertices
          Edges -> edges
          Faces -> faces
          Volumes -> volumes

        Parameters
        -----------
        elems: (n, d) np.ndarray

        Returns
        --------
        None
        """
        # naming rule in gustaf
        elem_name = type(self).__qualname__.lower()
        self._logd(f"seting {elem_name}'s connectivity.")

        return setattr(self, elem_name, elems)

    @property
    def const_elements(self):
        """
        Returns non-mutable version of elements

        Parameters
        -----------
        None

        Returns
        --------
        non_mutable_elements: (n, d) TrackedArray
        """
        self._logd("returning const_elements")
        return getattr(self, "const_" + type(self).__qualname__.lower())

    @helpers.data.ComputedMeshData.depends_on(["vertices", "elements"])
    def centers(self):
        """
        Center of elements.

        Parameters
        -----------
        None

        Returns
        --------
        centers: (n_elements, d) np.ndarray
        """
        self._logd("computing centers")

        return self.const_vertices[self.const_elements].mean(axis=1)

    @helpers.data.ComputedMeshData.depends_on(["vertices", "elements"])
    def referenced_vertices(self,):
        """
        Returns mask of referenced vertices.

        Parameters
        -----------
        None

        Returns
        --------
        referenced: (n,) np.ndarray
        """
        referenced = np.zeros(len(self.const_vertices), dtype=bool)
        referenced[self.const_elements] = True

        return referenced

    def remove_unreferenced_vertices(self):
        """
        Remove unreferenced vertices.
        Adapted from `github.com/mikedh/trimesh`

        Parameters
        -----------
        None

        Returns
        --------
        new_self: type(self)
        """
        referenced = self.referenced_vertices()

        inverse = np.zeros(len(self.vertices), dtype=settings.INT_DTYPE)
        inverse[referenced] = np.arange(referenced.sum())

        return self.update_vertices(
            mask=referenced,
            inverse=inverse,
        )


    @helpers.data.ComputedMeshData.depends_on(["elements"])
    def sorted_edges(self):
        """
        Sort edges along axis=1.

        Parameters
        -----------
        None

        Returns
        --------
        edges_sorted: (n_edges, 2) np.ndarray
        """
        self.edges_sorted = self.get_edges().copy()
        self.edges_sorted.sort(axis=1)

        return self.edges_sorted

    def get_edges_unique(self):
        """
        Returns unique edges.

        Parameters
        -----------
        None

        Returns
        --------
        edges_unique: (n, 2) np.ndarray
        """
        unique_stuff = utils.arr.unique_rows(
            self.get_edges_sorted(),
            return_index=True,
            return_inverse=True,
            return_counts=True,
            dtype_name=settings.INT_DTYPE,
        )

        # unpack
        #   set edges_unique with `edges`.
        #   otherwise it'd be based on edges_sorted and it changes orientation
        self.edges_unique_id = unique_stuff[1].astype(settings.INT_DTYPE)
        self.edges_unique = self.edges[self.edges_unique_id]
        self.edges_unique_inverse = unique_stuff[2].astype(settings.INT_DTYPE)
        self.edges_unique_count = unique_stuff[3].astype(settings.INT_DTYPE)
        self.outlines = self.edges_unique_id[self.edges_unique_count == 1]

        return self.edges_unique

    def get_edges_unique_id(self):
        """
        Returns ids of unique edges.

        Parameters
        -----------
        None

        Returns
        --------
        edges_unique_id: (n,) np.ndarray
        """
        _ = self.get_edges_unique()

        return self.edges_unique_id

    def get_edges_unique_inverse(self):
        """
        Returns ids that can be used to reconstruct edges with unique
        edges.

        Good to know:
          mesh.edges == mesh.unique_edges[mesh.edges_unique_inverse]

        Parameters
        -----------
        None

        Returns
        --------
        edges_unique_inverse: (len(self.edges),) np.ndarray
        """
        _ = self.get_edges_unique()

        return self.edges_unique_inverse

    def get_outlines(self):
        """
        Returns indices of very unique edges: edges that appear only once.
        For well constructed edges, this can be considered as outlines.

        Parameters
        -----------
        None

        Returns
        --------
        outlines: (m,) np.ndarray
        """
        _ = self.get_edges_unique()

        return self.outlines

    def update_elements(self, mask, inplace=True):
        """
        Similar to update_vertices, but for elements.

        Parameters
        -----------
        inplace: bool

        Returns
        --------
        new_self: type(self)
          iff inplace=False
        """
        new_elements = self.elements()[mask]
        if inplace:
            self.elements(new_elements).remove_unreferenced_vertices(
                inplace=True
            )
            return None

        else:
            return type(self)(
                vertices=self.vertices,
                elements=new_elements
            ).remove_unreferenced_vertices(inplace=False)

    def update_edges(self, *args, **kwargs):
        """
        Alias to update_elements.
        """
        return self.update_elements(*args, **kwargs)

    def subdivide(self):
        """
        Subdivides elements.
        Edges into 2, faces into 4.
        Not an inplace operation.

        Parameters
        -----------
        None

        Returns
        --------
        subdivided: Edges or Faces
        """
        if self.kind != "face":
            raise NotImplementedError

        else:
            whatami = self.get_whatami()
            if whatami.startswith("tri"):
                return type(self)(
                    **(utils.connec.subdivide_tri(self, return_dict=True))
                )

            elif whatami.startswith("quad"):
                return type(self)(
                    **(utils.connec.subdivide_quad(self, return_dict=True))
                )

            else:
                return None

    def dashed(self, spacing=None):
        """
        Turn edges into dashed edges(=lines).
        Given spacing, it will try to chop edges as close to it as possible.
        Pattern should look:
           o--------o    o--------o    o--------o
           |<------>|             |<-->|
              (chop length)         (chop length / 2)

        Parameters
        -----------
        spacing: float
          Default is None and it will use self.get_bounds_diagonal_norm() / 50

        Returns
        --------
        dashing_edges: Edges
        """
        if self.kind != "edge":
            raise NotImplementedError

        if spacing is None:
            # apply "automatic" spacing
            spacing = self.get_bounds_diagonal_norm() / 50

        v0s = self.vertices[self.edges[:,0]]
        v1s = self.vertices[self.edges[:,1]]

        distances = np.linalg.norm(v0s - v1s, axis=1)
        linspaces = (((distances // (spacing * 1.5)) + 1) * 3).astype(np.int32)

        # chop vertices!
        new_vs = []
        for v0, v1, lins in zip(v0s, v1s, linspaces):
            new_vs.append(np.linspace(v0, v1, lins))

        # we need all choped vertices.
        # there might be duplicating vertices. you can use merge_vertices
        new_vs = np.vstack(new_vs)
        # all mid points are explicitly defined, but they aren't required
        # so, rm. 
        mask = np.ones(len(new_vs), dtype=bool)
        mask[1::3] = False
        new_vs = new_vs[mask]

        # prepare edges
        tmp_es = utils.connec.range_to_edges((0, len(new_vs)), closed=False)
        new_es = tmp_es[::2]

        return Edges(vertices=new_vs, edges=new_es)

    def shrink(self, ratio=.8, map_vertexdata=True):
        """
        Returns shrunk elements.

        Parameters
        -----------
        ratio: float
          Default is 0.8
        map_vertexdata: bool
          Default is True. Maps all vertexdata.

        Returns
        --------
        s_elements: Elements
          shrunk elements
        """
        elements = self.elements()
        vs = np.vstack(self.vertices[elements])
        es = np.arange(len(vs))

        nodes_per_element = elements.shape[1]
        es = es.reshape(-1, nodes_per_element)

        mids = np.repeat(self.get_centers(), nodes_per_element, axis=0)

        vs -= mids
        vs *= ratio
        vs += mids

        s_elements = type(self)(vertices=vs, elements=es)

        if map_vertexdata:
            elements_flat = elements.ravel()
            for key, value in self.vertexdata.items():
                s_elements.vertexdata[key] = value[elements_flat]

            # probably wanna take visulation options too
            s_elements.vis_dict = self.vis_dict

        return s_elements

    def tovertices(self):
        """
        Returns Vertices obj.

        Parameters
        -----------
        None

        Returns
        --------
        vertices: Vertices
        """
        return Vertices(self.vertices)
