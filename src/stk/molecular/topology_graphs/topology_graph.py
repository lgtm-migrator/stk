"""
Adding Topology Graphs
======================

To add a new topology graph a new subclass of :class:`.TopologyGraph`
must be added, which implements its virtual methods. Similarly,
a new subclass of :class:`.Vertex` must also be made and its virtual
methods implemented. When the new subclass of :class:`.TopologyGraph`
is initialized, it must create instances of the :class:`.Vertex`
subclass, together with :class:`.Edge` instances. Once your
topology graph has the vertices and edges it wants, simply run
:meth:`.TopologyGraph.__init__` and you're done.

The subclass can also create `construction_stages` if parallel
construction needs to be broken down into separate stages. However,
if this is not the case, then an empty :class:`tuple` can simply be
passed.


"""

import numpy as np
import pathos
from collections import namedtuple

from ..reactor import Reactor
from ...utilities import vector_angle


class Vertex:
    """
    Represents a vertex in a :class:`.TopologyGraph`.

    Attributes
    ----------
    id : :class:`int`
        The id of the vertex. This should be its index in
        :attr:`TopologyGraph.vertices`.

    """

    def __init__(self, x, y, z):
        """
        Initialize a :class:`.Vertex`.

        Parameters
        ----------
        x : :class:`float`
            The x coordinate.

        y : :class:`float`
            The y coordinate.

        z : :class:`float`
            The z coordinate.

        """

        # This is set by TopologyGraph.__init__().
        self.id = None
        self._position = np.array([x, y, z], dtype=np.dtype('float64'))
        # Holds the ids of edges the Vertex is connected to.
        self._edge_ids = []
        self._cell = np.array([0, 0, 0])
        # This holds the ConstructedMolecule that the vertex is used
        # to construct.
        self._mol = None

    @classmethod
    def init_at_center(cls, *vertices):
        """
        Initialize at the center of `vertices`.

        Parameters
        ----------
        vertices : :class:`.Vertex`
            Vertices at whose center this vertex should be initialized.

        Returns
        -------
        :class:`.Vertex`
            The vertex.

        """

        center = sum(vertex.get_position() for vertex in vertices)
        center /= len(vertices)
        return cls(*center)

    def apply_scale(self, scale):
        """
        Scale the position by `scale`.

        Parameters
        ----------
        scale : :class:`float` or :class:`list`of :class:`float`
            The value by which the position of the :class:`Vertex` is
            scaled. Can be a single number if all axes are scaled by
            the same amount or a :class:`list` of three numbers if
            each axis is scaled by a different value.

        Returns
        -------
        :class:`Vertex`
            The vertex is returned.

        """

        self._position *= scale
        return self

    def clone(self, clear_edges=False):
        """
        Return a clone.

        Parameters
        ----------
        clear_edges : :class:`bool`, optional
            ``True`` if the clone should not be connected to any edges.

        Returns
        -------
        :class:`Vertex`
            The clone.

        """

        clone = self.__class__.__new__(self.__class__)
        clone.id = self.id
        clone._position = np.array(self._position)
        clone._cell = np.array(self._cell)
        clone._edge_ids = tuple(self._edge_ids)
        clone._mol = self._mol
        return clone

    def get_position(self):
        """
        Return the position.

        Returns
        -------
        :class:`numpy.ndarray`
            The position of the :class:`Vertex`.

        """

        return np.array(self._position)

    def get_num_edges(self):
        """
        Return the number of connceted edge.

        Returns
        -------
        :class:`int`
            The number of connected edges.

        """

        return len(self._edge_ids)

    def get_edge_ids(self):
        """
        Yield the ids of connected edges.

        Yields
        ------
        :class:`int`
            The :class:`~.Edge.id` of a connected edge.

        """

        yield from self._edge_ids

    def add_edge(self, edge):
        """
        Connect to an `edge`.

        Notes
        -----
        This method can only be called before :meth:`finalize`.

        Parameters
        ----------
        edge : :class:`.Edge`
            An edge to which the vertex should be connected.

        Returns
        -------
        :class:`.Vertex`
            The vertex.

        """

        # The edge will get converted to its id by finalize().
        self._edge_ids.append(edge)
        return self

    def finalize(self):
        """
        Finish construction.

        Needs to be called on every vertex as the last part of
        :class:`.TopologyGraph` construction.

        Returns
        -------
        :class:`.Vertex`
            The vertex.

        """

        self._edge_ids = tuple(edge.id for edge in self._edge_ids)
        return self

    def set_position(self, position):
        """
        Set the position of the vertex.

        Parameters
        ----------
        :class:`numpy.ndarray`
            The new position of the vertex.

        Returns
        -------
        :class:`.Vertex`
            The vertex.

        """

        self._position = np.array(position)
        return self

    def get_cell(self):
        """
        Get the cell of the lattice in which the vertex is found.

        Returns
        -------
        :class:`numpy.ndarray`
            The cell of the lattice in which the vertex is found.

        """

        return np.array(self._cell)

    def set_cell(self, x, y, z):
        """
        Set the cell of the lattice in which the vertex is found.

        Parameters
        ----------
        x : :class:`int`
            The x position of the cell in the lattice.

        y : :class:`int`
            The y position of the cell in the lattice.

        z : :class:`int`
            The z position of the cell in the lattice.

        Returns
        -------
        :class:`.Vertex`
            The vertex.

        """

        self._cell = np.array([x, y, z])
        return self

    def set_contructed_molecule(self, mol):
        """
        Set the :class:`.ConstructedMolecule` being constructed.

        Parameters
        ----------
        mol : :class:`.ConstructedMolecule`
            The molecule being constructed.

        Returns
        -------
        :class:`.Vertex`
            The vertex.

        """

        self._mol = mol
        return self

    def place_building_block(self, building_block, vertices, edges):
        """
        Place `building_block` on the :class:`.Vertex`.

        Parameters
        ----------
        building_block : :class:`.Molecule`
            The building block molecule which is to be placed on the
            vertex.

        vertices : :class:`tuple` of :class:`.Vertex`
            All vertices in the topology graph. The index of each
            vertex must match its :class:`~.Vertex.id`.

        edges : :class:`tuple` of :class:`.Edge`
            All edges in the topology graph. The index of each
            edge must match its :class:`~.Edge.id`.

        Returns
        -------
        :class:`numpy.nadarray`
            The position matrix of `building_block` after being
            placed.

        Raises
        ------
        :class:`NotImplementedError`
            This is a virtual method, it needs to be implemented in a
            subclass.

        """

        raise NotImplementedError()

    def assign_func_groups_to_edges(
        self,
        building_block,
        vertices,
        edges
    ):
        """
        Assign functional groups to edges.

        Each :class:`.FunctionalGroup` of the `building_block` needs
        to be associated with one of the :class:`.Edge` instances in
        :attr:`edges`.

        Parameters
        ----------
        building_block : :class:`.Molecule`
            The building block molecule which is needs to have
            functional groups assigned to edges.

        vertices : :class:`tuple` of :class:`.Vertex`
            All vertices in the topology graph. The index of each
            vertex must match its :class:`~.Vertex.id`.

        edges : :class:`tuple` of :class:`.Edge`
            All edges in the topology graph. The index of each
            edge must match its :class:`~.Edge.id`.

        Returns
        -------
        :class:`dict`
            A mapping from the id of a functional group in
            `building_block` to the id of the edge in :attr:`edges` it
            is assigned to.

        Raises
        ------
        :class:`NotImplementedError`
            This is a virtual method, it needs to be implemented in a
            subclass.

        """

        raise NotImplementedError()

    def after_assign_func_groups_to_edges(
        self,
        building_block,
        vertices,
        edges,
        func_groups
    ):
        """
        Perform operations after functional groups have been assigned.

        This method is always executed serially. It is often useful
        when data needs to be transferred between vertices, which
        have been processed independently, in parallel.

        It does nothing by default, but should be overridden when
        necessary.

        Parameters
        ----------
        building_block : :class:`.Molecule`
            The building block molecule which is needs to have
            functional groups assigned to edges.

        vertices : :class:`tuple` of :class:`.Vertex`
            All vertices in the topology graph. The index of each
            vertex must match its :class:`~.Vertex.id`.

        edges : :class:`tuple` of :class:`.Edge`
            All edges in the topology graph. The index of each
            edge must match its :class:`~.Edge.id`.

        func_groups : :class:`tuple` of :class:`.FunctionalGroup`
            The functional group clones added to the constructed
            molecule.

        Returns
        -------
        None : :class:`NoneType`

        """

        return

    def _get_edge_centroid(self, edges):
        """
        Return the centroid of `edges`.

        Parameters
        ----------
        edges : :class:`iterable` of :class:`.Edge`
            The edges which are used to calculate the centroid.

        Returns
        -------
        :class:`numpy.ndarray`
            The centroid of the edges.

        """

        edge_positions = []
        for i, edge in enumerate(edges, 1):
            edge_positions.append(edge.get_position(self))
        return np.sum(edge_positions, axis=0) / i

    def _get_edge_plane_normal(self, reference, edges):
        """
        Get the normal to the plane on which `edges` lie.

        Parameters
        ----------
        reference : :class:`numpy.ndarray`
            A reference direction vector. The direction of the returned
            normal is set such that its angle with with `reference`
            is always acute.

        edges : :class:`iterable` of :class:`.Edge`
            The edges which are used to calculate the plane.
            If there are more than three, a plane of best fit across
            `edges` is returned.

        Returns
        -------
        :class:`numpy.ndarray`
            A unit vector which describes the normal to the plane of
            the edges.

        """

        edge_positions = []
        for i, edge in enumerate(edges, 1):
            edge_positions.append(edge.get_position(self))
        edge_positions = np.array(edge_positions)

        centroid = np.sum(edge_positions, axis=0) / i
        normal = np.linalg.svd(edge_positions - centroid)[-1][2, :]

        if vector_angle(normal, reference) > np.pi/2:
            normal *= -1
        return normal

    def _get_molecule_centroid(self, atom_ids=None):
        """
        Get the centroid of the molecule being constructed.

        During construction :meth:`.Molecule.get_centroid` cannot be
        used, because the molecule is not fully constructed yet. This
        method acts as its replacement during construction.

        Parameters
        ----------
        atom_ids : :class:`iterable` of :class:`int`, optional
            The ids of atoms which are used to calculate the
            centroid. If ``None``, then all atoms will be used.

        Returns
        -------
        :class:`numpy.ndarray`
            The centroid of atoms specified by `atom_ids`.

        """

        if atom_ids is None:
            atom_ids = range(len(self.atoms))
        elif not isinstance(atom_ids, (list, tuple)):
            atom_ids = list(atom_ids)

        return np.divide(
            np.sum(
                np.array(self._mol._position_matrix)[atom_ids, :],
                axis=0
            ),
            len(atom_ids)
        )

    def __str__(self):
        x, y, z = self._position
        return f'Vertex(id={self.id}, position={[x, y, z]})'

    def __repr__(self):
        return str(self)


class Edge:
    """
    Represents an edge in a topology graph.

    Note that some methods of this class will behave differently
    before and after :meth:`finalize` is called. Methods will switch
    from returning :class:`.Vertex` objects to returning :class:`int`
    objects.

    Attributes
    ----------
    id : :class:`int`
        The id of the edge. Matches the index of the edge in
        :attr:`.TopologyGraph.edges`.

    """

    def __init__(
        self,
        *vertices,
        position=None,
        periodicity=None,
        lattice_constants=None
    ):
        """
        Initialize an :class:`Edge`.

        Parameters
        ----------
        *vertices : :class:`.Vertex`
            The vertices which the :class:`Edge` connects.

        position : :class:`numpy.ndarray`, optional
            The position of the edge. If ``None``, the centroid
            of `vertices` is used.

        periodicity : :class:`tuple` of :class:`int`, optional
            The periodicity of the edge. For example, if ``(0, 0, 0)``
            then the edge is not periodic. If, ``(1, 0, -1)`` then the
            edge is periodic across the x axis in the positive
            direction, is not periodic across the y axis and is
            periodic across the z axis in the negative direction. If
            ``None`` then the edge is not periodic.

        lattice_constants : :class:`iterable`, optional
            If the edge is periodic, the a, b and c lattice
            constants should be provided as vectors in Cartesian
            coordiantes.

        """

        if periodicity is None:
            periodicity = [0, 0, 0]
        if lattice_constants is None:
            lattice_constants = ([0, 0, 0] for i in range(3))

        self._vertex_ids = vertices
        # This will be set by TopologyGraph.__init__.
        self.id = None
        self._periodicity = np.array(periodicity)
        # The FunctionalGroup instances which the edge connects.
        # These will belong to the molecules placed on the vertices
        # connected by the edge.
        self._func_groups = []

        self._custom_position = position is not None
        self._position = position
        self._lattice_constants = tuple(
            np.array(constant) for constant in lattice_constants
        )

        _position = 0
        for i, vertex in enumerate(vertices, 1):
            vertex.add_edge(self)

            if not self._custom_position:
                _position += vertex.get_position()

        if not self._custom_position:
            self._position = _position / i

    def get_periodicity(self):
        """
        Get the periodicity of the edge.

        Returns
        -------
        :class:`numpy.ndarray`
            The periodicity of the edge. If ``[0, 0, 0]`` the edge is
            not periodic, if ``[1, 0, -1]`` the edge is periodic going
            in the postive direction along the x axis, is not periodic
            across the y axis and is periodic in the negative direction
            along the z axis.

        """

        return np.array(self._periodicity)

    def set_periodicity(self, x, y, z):
        """
        Set the periodicity  of the edge.

        Parameters
        ----------
        x : :class:`int`
            The periodicity of the edge along the x axis.

        y : :class:`int`
            The periodicity of the edge along the y axis.

        z : :class:`int`
            The periodicity of the edge along the z axis.

        Returns
        -------
        :class:`.Edge`
            The edge.

        """

        self._periodicity = np.array([x, y, z])
        return self

    def is_periodic(self):
        """
        Return ``True`` if periodic.

        Returns
        -------
        :class:`bool`
            ``True`` if periodic.

        """

        return any(i != 0 for i in self._periodicity)

    def apply_scale(self, scale):
        """
        Scale the position by `scale`.

        Parameters
        ----------
        scale : :class:`float` or :class:`list`of :class:`float`
            The value by which the position of
            the :class:`Edge` is scaled. Can be a single number if all
            axes are scaled by the same amount or a :class:`list` of
            three numbers if each axis is scaled by a different value.

        Returns
        -------
        :class:`Edge`
            The edge is returned.


        """

        self._position *= scale
        self._lattice_constants = tuple(
            scale*constant for constant in self._lattice_constants
        )
        return self

    def finalize(self):
        """
        Finish construction.

        Needs to be called on every edge as the last part of
        :class:`.TopologyGraph` construction.

        Returns
        -------
        :class:`.Edge`
            The edge.

        """

        self._vertex_ids = tuple(
            vertex.id for vertex in self._vertex_ids
        )
        return self

    def clone(self, vertex_map=None):
        """
        Return a clone.

        Parameters
        ----------
        vertex_map : :class:`dict`, optional
            Maps the current vertices in the edge to the ones which
            the clone should hold. If :meth:`clone` is getting called
            before :meth:`finalize` has been called, the keys and
            values should be :class:`.Vertex` objects. After
            :meth:`finalize` has been called they should be
            :class:`int` objects.

        Returns
        -------
        :class:`Edge`
            The clone.

        """

        if vertex_map is None:
            vertex_map = {}

        clone = self.__class__.__new__(self.__class__)
        clone.id = self.id
        clone._func_groups = list(self._func_groups)
        clone._custom_position = self._custom_position
        clone._periodicity = np.array(self._periodicity)
        clone._lattice_constants = tuple(
            np.array(constant) for constant in self._lattice_constants
        )
        clone._vertex_ids = tuple(
            vertex_map.get(v, v) for v in self._vertex_ids
        )
        clone._position = np.array(self._position)
        return clone

    def get_func_groups(self):
        """
        Get the functional groups connected by this edge.

        Returns
        -------
        :class:`tuple` of :class:`.FunctionalGroup`
            The functional groups connected by the edge.

        """

        return tuple(self._func_groups)

    def get_vertex_ids(self):
        """
        Get the connected vertices.

        If this method is called before :meth:`finalize`, the
        :class:`.Vertex` objects will be yielded instead.

        Yields
        ------
        :class:`int`
            The id of a connected vertex.

        """

        yield from self._vertex_ids

    def assign_func_group(self, func_group):
        """
        Assign `func_group` to be connected by this edge.

        Parameters
        ----------
        func_group : :class:`.FunctionalGroup`
            The functional group to be assigned to the edge.

        Returns
        -------
        :class:`Edge`
            The edge is returned.

        """

        self._func_groups.append(func_group)

    def get_position(self, vertices=None, reference=None):
        """
        Return the position.

        Parameters
        ----------
        vertices : :class:`tuple` of :class:`.Vertex`, optional
            All the vertices in the topology graph. Index of each
            vertex must be equal to :class:`~.Vertex.id`. Only needs
            to be supplied if `reference` is supplied

        reference : :class:`.Vertex`, optional
            If the edge is periodic, the position returned will
            depend on which vertex the edge position is calculated
            relative to.

        Returns
        -------
        :class:`numpy.ndarray`
            The position of the :class:`Edge`.

        """

        if reference is None or not self.is_periodic():
            return np.array(self._position)

        other = vertices[
            next(v for v in self._vertices if v != reference.id)
        ]
        direction = (
            1 if reference is vertices[self._vertex_ids[0]] else -1
        )
        end_cell = reference.get_cell() + direction*self._periodicity
        cell_shift = end_cell - other.get_cell()
        shift = 0
        for dim, constant in zip(cell_shift, self._lattice_constants):
            shift += dim*constant
        return (
            (other.get_position()+shift+reference.get_position()) / 2
        )

    def set_position(self, position):
        """
        Set the position.

        Parameters
        ----------
        position : :class:`numpy.ndarray`
            The new position of the edge.

        Returns
        -------
        :class:`Edge`
            The edge.

        """

        self._position = np.array(position)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        vertices = ', '.join(str(id_) for id_ in self._vertex_ids)
        if self._custom_position:
            position = f', position={self._position!r}'
        else:
            position = ''

        if any(i != 0 for i in self._periodicity):
            periodicity = f', periodicity={tuple(self._periodicity)!r}'
        else:
            periodicity = ''

        return f'Edge({vertices}{position}{periodicity})'


PlacementResult = namedtuple(
    'PlacementResult',
    ['building_block', 'vertex', 'assignments']
)


def _place_building_blocks(vertex, building_block):
    vertex.place_building_block(building_block)
    assignments = vertex.assign_func_groups_to_edges(building_block)
    return PlacementResult(building_block, vertex, assignments)


class TopologyGraph:
    """
    Represents topology graphs of :class:`.ConstructedMolecule`.

    The topology graph is an abstract representation of a constructed
    molecule. The vertices indicate where building blocks are placed
    and the edges indicate which building blocks have bonds formed
    between them by the construction process.

    Vertices are responsible for placing the building block molecules.
    By initializing the vertices with different settings, they can
    position the building block molecules differently and therefore
    allow the user to easily specify a different structural isomer.

    Once a building block is placed on a vertex, the functional groups
    on the building block must be assigned to the different edges
    connected to the vertex. The number of functional groups in the
    building block must match the number of edges connected to the
    vertex.

    Once the functional groups are assigned to edges, each edge
    represents a reaction between the functional groups assigned to it.
    Note that an edge can be assigned more than two functional groups,
    in case you are dealing with something really exotic. The
    functional groups are then matched to an appropriate reaction,
    which generally creates bonds between the atoms of the functional
    groups. After this you will end up with a
    :class:`.ConstructedMolecule`.

    Attributes
    ----------
    vertices : :class:`tuple` of :class:`.Vertex`
        The vertices which make up the topology graph.

    edges : :class:`tuple` of :class:`.Edge`
        The edges which make up the topology graph.

    """

    def __init__(
        self,
        vertices,
        edges,
        construction_stages,
        num_processes
    ):
        """
        Initialize an instance of :class:`.TopologyGraph`.

        Parameters
        ----------
        vertices : :class:`tuple` of :class:`.Vertex`
            The vertices which make up the graph.

        edges : :class:`tuple` of :class:`.Edge`
            The edges which make up the graph.

        construction_stages : :class:`tuple` of :class:`callable`
            A collection of callables, each of which takes a
            :class:`.Vertex` and returns ``True`` or ``False``.
            If the first :class:`callable` is applied to a  vertex in
            `vertices`, that vertex is is part of the first
            construction stage. The second :class:`callable` is then
            applied to all vertices not in the first stage and those
            which return ``True`` belong to the second stage and
            so on.

            Vertices which belong to the same construction stage
            all place building blocks together in parallel, before
            placement is done by any vertices which are part of a later
            stage. This breaks down parallel construction into
            serial stages if synchronization between stages is needed.

            If the topology graph is performing construction serially,
            then all vertices which belong to an earlier stage will
            place their building block before those at a later stage.

        num_processes : :class:`int`
            The number of parallel processes to create during
            :meth:`construct`.

        """

        self.vertices = vertices
        self.edges = edges
        self._construction_stages = construction_stages
        self._set_stages()
        self._num_processes = num_processes
        for i, edge in enumerate(self.edges):
            edge.id = i
        for i, vertex in enumerate(self.vertices):
            vertex.id = i
        for edge in self.edges:
            edge.finalize()
        for vertex in self.vertices:
            vertex.finalize()

    def _set_stages(self):
        self._stages = tuple(
            [] for i in range(len(self._construction_stages)+1)
        )
        for vertex in self.vertices:
            placed = False
            for i, stage in enumerate(self._construction_stages):
                if stage(vertex):
                    self._stages[i].append(vertex)
                    placed = True
                    break
            if not placed:
                self._stages[-1].append(vertex)

    def construct(self, mol):
        """
        Construct a :class:`.ConstructedMolecule`.

        Parameters
        ----------
        mol : :class:`.ConstructedMolecule`
            The :class:`.ConstructedMolecule` instance which needs to
            be constructed.

        Returns
        -------
        None : :class:`NoneType`

        """

        scale = self._get_scale(mol)
        vertices = tuple(self._get_vertex_clones(mol, scale))
        edges = tuple(self._get_edge_clones(scale))

        self._prepare(mol)
        self._place_building_blocks(mol, vertices, edges)

        vertices, edges = self._before_react(mol, vertices, edges)
        reactor = Reactor(mol)
        for edge in edges:
            reactor.add_reaction(
                func_groups=edge.get_func_groups(),
                periodicity=tuple(edge.get_periodicity())
            )
        reactor.finalize()

        self._clean_up(mol)

    def assign_building_blocks_to_vertices(self, building_blocks):
        """
        Assign `building_blocks` to :attr:`vertices`.

        Parameters
        ----------
        building_blocks : :class:`list` of :class:`.Molecule`
            The :class:`.BuildingBlock` and
            :class:`ConstructedMolecule` instances which
            represent the building block molecules used for
            construction. Only one instance is present per building
            block molecule, even if multiples of that building block
            join up to form the :class:`ConstructedMolecule`.

        Returns
        -------
        :class:`dict`
            Maps the `building_blocks`, to the
            :class:`~.topologies.base.Vertex` objects in
            :attr:`vertices` they are placed on during construction.
            The :class:`dict` has the form

            .. code-block:: python

                building_block_vertices = {
                    BuildingBlock(...): [Vertex(...), Vertex(...)],
                    BuildingBlock(...): [
                        Vertex(...),
                        Vertex(...),
                        Vertex(...),
                    ]
                    ConstructedMolecule(...): [Vertex(...)]
                }

        Raises
        ------
        :class:`NotImplementedError`
            This is a virtual method which needs to be implemented in
            a subclass.

        """

        raise NotImplementedError()

    def _get_scale(self, mol):
        """
        Get the scale used for vertex and edge positions.

        Parameters
        ----------
        mol : :class:`.ConstructedMolecule`
            The molecule being constructed.

        Returns
        -------
        :class:`float` or :class:`list` of :class:`float`
            The value by which the position of each :class:`Vertex` and
            is :class:`Edge` is scaled. Can be a single number if all
            axes are scaled by the same amount or a :class:`list` of
            three numbers if each axis is scaled by a different value.

        Raises
        ------
        :class:`NotImplementedError`
            This is a virtual method and needs to be implemented in a
            subclass.

        """

        raise NotImplementedError()

    def _get_vertex_clones(self, mol, scale):
        """
        Yield clones of :attr:`vertices`.

        The order of yielded clones corresponds to the order in
        :attr:`vertices`

        Notes
        -----
        Clones are necessary so that multiple :meth:`construct`
        calls can be done asynchronously and so that the state of the
        original :class:`.Vertex` objects is not
        changed by the construction process.

        Parameters
        ----------
        mol : :class:`.ConstructedMolecule`
            The molecule being constructed.

        scale : :class:`float` or :class:`list` of :class:`float`
            The value by which the position of each :class:`Vertex` is
            scaled. Can be a single number if all axes are scaled by
            the same amount or a :class:`list` of three numbers if
            each axis is scaled by a different value.

        Yields
        -------
        :class:`.Vertex`
            A vertex clone.

        """

        for vertex in self.vertices:
            yield (
                vertex
                .clone()
                .set_contructed_molecule(mol)
                .apply_scale(scale)
            )

    def _get_edge_clones(self, scale):
        """
        Yield clones of :attr:`edges`.

        The order of yielded edges corresponds to the order in
        :attr:`edges`.

        Parameters
        ----------
        scale : :class:`float` or :class:`list` of :class:`float`
            The value by which the position of each :class:`Edge` is
            scaled. Can be a single number if all axes are scaled by
            the same amount or a :class:`list` of three numbers if
            each axis is scaled by a different value.

        Yields
        -------
        :class:`.Edge`
            An edge clone.

        """

        for edge in self.edges:
            yield edge.clone().apply_scale(scale)

    def _before_react(self, mol, vertices, edges):
        return vertices, edges

    def _prepare(self, mol):
        """
        Do preprocessing on `mol` before construction.

        Parameters
        ----------
        mol : :class:`.ConstructedMolecule`
            The molecule being constructed.

        Returns
        -------
        None : :class:`NoneType`

        """

        return

    def _place_building_blocks(self, mol, vertices, edges):
        """
        Place building blocks in `mol` on :attr:`vertices`.

        Parameters
        ----------
        mol : :class:`.ConstructedMolecule`
            The molecule being constructed.

        vertices : :class:`tuple` of :class:`.Vertex`
            The vertex clones used for construction.

        edges : :class:`tuple` of :class:`.Edge`
            The edge clones used for construction.

        Returns
        -------
        None : :class:`NoneType`

        """

        if self._num_processes == 1:
            return self._place_building_blocks_serial(
                mol=mol,
                vertices=vertices,
                edges=edges
            )
        else:
            return self._place_building_blocks_parallel(
                mol=mol,
                vertices=vertices,
                edges=edges
            )

    def _get_atom_map(self, mol, bb, bb_id):
        atom_map = {}
        for atom in bb.atoms:
            atom_clone = atom.clone()
            atom_clone.id = len(mol.atoms)
            atom_clone.building_block = bb
            atom_clone.building_block_id = bb_id
            atom_map[atom] = atom_clone
            mol.atoms.append(atom_clone)
        return atom_map

    def _assign_func_groups_to_edges(
        self,
        mol,
        bb,
        bb_id,
        edges,
        assignments
    ):
        atom_map = self._get_atom_map(mol, bb, bb_id)
        mol.func_groups.extend(
            fg.clone(atom_map) for fg in bb.func_groups
        )
        num_fgs = len(bb.func_groups)
        for fg_id, edge_id in assignments.items():
            edges[edge_id].assign_func_group(
                func_group=mol.func_groups[-num_fgs+fg_id]
            )
        return atom_map

    def _place_building_blocks_serial(self, mol, vertices, edges):
        bb_id = 0

        vertex_building_blocks = {
            vertex: bb
            for bb, vertices in mol.building_block_vertices.items()
            for vertex in vertices
        }
        # Use a shorter alias.
        counter = mol.building_block_counter
        for stage in self._stages:
            for instance_vertex in stage:
                vertex = vertices[instance_vertex.id]
                bb = vertex_building_blocks[instance_vertex]
                original_coords = bb.get_position_matrix()

                mol._position_matrix.extend(
                    vertex.place_building_block(bb, vertices, edges)
                )
                assignments = vertex.assign_func_groups_to_edges(
                    building_block=bb,
                    vertices=vertices,
                    edges=edges
                )
                atom_map = self._assign_func_groups_to_edges(
                    mol=mol,
                    bb=bb,
                    bb_id=bb_id,
                    edges=edges,
                    assignments=assignments
                )
                # Perform additional, miscellaneous operations.
                vertex.after_assign_func_groups_to_edges(
                    building_block=bb,
                    vertices=vertices,
                    edges=edges,
                    func_groups=mol.func_groups[-len(bb.func_groups):]
                )

                bb.set_position_matrix(original_coords)
                mol.bonds.extend(b.clone(atom_map) for b in bb.bonds)
                counter.update([bb])
                bb_id += 1

    def _place_building_blocks_parallel(self, mol, vertices, edges):
        bb_id = 0

        vertex_building_blocks = {
            vertex: bb
            for bb, vertices in mol.building_block_vertices.items()
            for vertex in vertices
        }
        bb_map = {
            bb.get_identity_key(): bb
            for bb in mol.get_building_blocks()
        }
        # Use a shorter alias.
        counter = mol.building_block_counter
        with pathos.pools.ProcessPool(self._num_processes) as pool:
            for stage in self._stages:
                verts = []
                bbs = []
                for instance_vertex in stage:
                    verts.append(vertices[instance_vertex.id])
                    bbs.append(vertex_building_blocks[instance_vertex])
                results = pool.map(_place_building_blocks, verts, bbs)

                for result in results:
                    result_bb = result.building_block
                    bb = bb_map[result_bb.get_identity_key()]

                    mol._position_matrix.extend(
                        result_bb.get_position_matrix()
                    )
                    atom_map = self._assign_func_groups_to_edges(
                        mol=mol,
                        bb=bb,
                        bb_id=bb_id,
                        edges=edges,
                        assignments=result.assignments
                    )

                    # Perform additional, miscellaneous operations.
                    vertex = vertices[result.vertex.id]
                    num_fgs = len(bb.func_groups)
                    vertex.after_assign_func_groups_to_edges(
                        building_block=result_bb,
                        func_groups=mol.func_groups[-num_fgs:]
                    )
                    mol.bonds.extend(
                        b.clone(atom_map) for b in bb.bonds
                    )
                    counter.update([bb])
                    bb_id += 1

    def _clean_up(self, mol):
        mol._position_matrix = np.array(mol._position_matrix).T
        for i, atom in enumerate(mol.atoms):
            atom.id = i

    def __str__(self):
        return repr(self)

    def __repr__(self):
        raise NotImplementedError()
