"""
Defines mutation operations via the ``Mutation`` class.

Extending MMEA: Adding mutation functions
-----------------------------------------
If a new mutation operation is to be added to MMEA it should be added
as a method in the ``Mutation`` class defined in this module. The only
requirement is that the first argument is ``macro_mol`` (excluding any
``self`` or ``cls`` arguments).

The naming requirement of ``macro_mol`` exists to help users identify
which arguments are handled automatically by MMEA and which they need
to define in the input file. The convention is that if the mutation
function takes an argument called  ``macro_mol`` it does not have to be
specified in the input file.

If the mutation function does not fit neatly into a single function
make sure that any helper functions are private, ie that their names
start with a leading underscore.

"""

import os
import logging
import numpy as np
from collections import Counter

from .population import Population
from .plotting import plot_counter
from ..molecular import StructUnit3, Cage

logger = logging.getLogger(__name__)


class MutationError(Exception):
    ...


class Mutation:
    """
    Carries out mutations operations on a population.

    Instances of the ``Population`` class delegate mutation operations
    to instances of this class. They do this by calling:

        >>> mutant_pop = pop.gen_mutants()

    which returns a new population consisting of molecules generated by
    performing mutation operations on members of ``pop``. This class
    invokes an instance of the ``Selection`` class to select molecules
    for mutations. Both an instance of this class and the ``Selection``
    class are held in the `ga_tools` attribute of a ``Population``
    instance.

    This class is initialized with a list of  ``FunctionData``
    instances. Each ``FunctionData`` object holds the name of the
    mutation function to be used by the population as well as any
    additional parameters the function may require. Mutation functions
    should be defined as methods within this class.

    A mutation function from the list will be selected at random, with
    likelihoods modified if the user supplies a `weights` list during
    initialization.

    Members of this class are also initialized with an integer which
    holds the number of mutation operations to be performed each
    generation.

    Attributes
    ----------
    funcs : list of FunctionData instances
        This lists holds all the mutation functions which are to be
        applied by the GA. One will be chosen at random when a mutation
        is desired. The likelihood that each is selected is given by
        `weights`.

    num_mutations : int
        The number of mutations that needs to be performed each
        generation.

    n_calls : int
        The total number of times an instance of ``Mutation`` has been
        called during its lifetime.

    weights : None or list of floats (default = None)
        When ``None`` each mutation function has equal likelihood of
        being picked. If `weights` is a list each float corresponds to
        the probability of selecting the mutation function at the
        corresponding index.

    """

    def __init__(self, funcs, num_mutations, weights=None):
        self.funcs = funcs
        self.weights = weights
        self.num_mutations = num_mutations
        self.n_calls = 0

    def __call__(self, population, counter_path=''):
        """
        Carries out mutation operations on the supplied population.

        This function selects members of the population to be mutated
        and mutates them. This goes on until either all possible
        molecules have been mutated or the required number of
        successful mutation operations have been performed.

        The mutants generated are returned together in a ``Population``
        instance. Any molecules that are created as a result of
        mutation that match a molecule present in the original
        population are removed.

        Parameters
        ----------
        population : Population
            The population who's members are to be mutated.

        counter_path : str (default = '')
            The path to the .png file showing which members were
            selected for mutation. If '' then no file is made.

        Returns
        -------
        Population
            A population with all the mutants generated held in the
            `members` attribute. This does not include mutants which
            correspond to molecules already present in `population`.

        """

        mutant_pop = Population(population.ga_tools)
        counter = Counter()

        # Keep a count of the number of successful mutations.
        num_mutations = 0
        for parent in population.select('mutation'):
            counter.update([parent])
            func_data = np.random.choice(self.funcs, p=self.weights)
            func = getattr(self, func_data.name)

            try:
                self.n_calls += 1
                mutant = func(parent, **func_data.params)

                # If the mutant was retrieved from the cache, log the
                # name.
                if mutant.name:
                    logger.debug(('Mutant "{}" retrieved from '
                                  'cache.').format(mutant.name))

                mutant_pop.members.append(mutant)
                num_mutations += 1
                logger.info(
                    'Mutation number {}. Finish when {}.'.format(
                                    num_mutations, self.num_mutations))

                if num_mutations == self.num_mutations:
                    break

            except Exception as ex:
                errormsg = ('Mutation function "{}()" '
                            'failed on molecule "{}".').format(
                             func_data.name, parent.name)
                logger.error(errormsg, exc_info=True)

        mutant_pop -= population

        if counter_path:
            # Update counter with unselected members.
            for member in population:
                if member not in counter.keys():
                    counter.update({member: 0})
            plot_counter(counter, counter_path)

        return mutant_pop

    def cage_random_bb(self, macro_mol, database, fg=None):
        """
        Substitutes a building block with a random one from a database.

        Parameters
        ----------
        macro_mol : Cage
            The cage who's building block will be exchanged. Note that
            the cage is not destroyed. It is used a template for a new
            cage.

        database : str
            The full path of the database from which a new
            building block is to be found.

        fg : str (default = None)
            The name of a functional group. All molecules in
            `database` must have this functional group. This is the
            functional group which is used to assemble the
            macromolecules. If ``None`` it is assumed that the
            path `database` holds the name of the functional group.

        Returns
        -------
        Cage
            A cage instance generated by taking all attributes of
            `macro_mol` except its building-block* which is replaced by
            a random building-block* from `database`.

        """

        _, lk = max(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))

        _, og_bb = min(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))

        while True:
            try:
                bb_file = np.random.choice(os.listdir(database))
                bb_file = os.path.join(database, bb_file)
                bb = StructUnit3(bb_file, fg)
                break

            except TypeError:
                continue

        if len(og_bb.bonder_ids) != len(bb.bonder_ids):
            raise MutationError(
                ('\n\nMUTATION ERROR: Replacement building block does'
                   ' not have the same number of functional groups as '
                   'the original building block.\n\nOriginal building '
                  'block:\n\n{}\n\nReplacement building block:\n\n'
                  '{}\n\n').format(og_bb, bb))

        return Cage([bb, lk], macro_mol.topology)

    def cage_random_lk(self, macro_mol, database, fg=None):
        """
        Substitutes a linker with a random one from a database.

        Parameters
        ----------
        macro_mol : Cage
            The cage who's linker will be exchanged. Note that
            the cage is not destroyed. It is used a template for a new
            cage.

        database : str
            The full path of the database from which a new linker is to
            be found.

        fg : str (default = None)
            The name of a functional group. All molecules in
            `database` must have this functional group. This is the
            functional group which is used to assemble the
            macromolecules. If ``None`` it is assumed that the
            path `database` holds the name of the functional group.

        Returns
        -------
        Cage
            A cage instance generated by taking all attributes of
            `macro_mol` except its linker which is replaced by a random
            linker from `database`.

        """

        _, og_lk = max(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))
        lk_type = type(og_lk)

        _, bb = min(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))

        while True:
            try:
                lk_file = np.random.choice(os.listdir(database))
                lk_file = os.path.join(database, lk_file)
                lk = lk_type(lk_file, fg)
                break

            except TypeError:
                continue

        if len(og_lk.bonder_ids) != len(lk.bonder_ids):
            raise MutationError(
                 ('\n\nMUTATION ERROR: Replacement linker does not'
                  ' have the same number of functional groups as the'
                  ' original linker.\n\nOriginal linker:\n\n{}\n\n'
                  'Replacement linker:\n\n{}\n\n').format(og_lk, lk))

        return Cage([bb, lk], macro_mol.topology)

    def cage_similar_bb(self, macro_mol, database, fg=None):
        """
        Substitute the building block with similar one from `database`.

        All of the molecules in `database` are checked for similarity
        to the building block of `macro_mol`. The first time this
        mutation function is run on a cage, the most similar molecule
        in `database` is used to substitute the building block. The
        next time this mutation function is run on the same cage, the
        second most similar molecule from `database` is used and so on.

        Parameters
        ----------
        macro_mol : Cage
            The cage which is to have its building-block* substituted.

        database : str
            The full path of the database from which molecules are used
            to substitute the building-block* of `macro_mol`.

        fg : str (default = None)
            The name of a functional group. All molecules in
            `database` must have this functional group. This is the
            functional group which is used to assemble the
            macromolecules. If ``None`` it is assumed that the
            path `database` holds the name of the functional group.

        Modifies
        --------
        macro_mol._similar_bb_mols : generator
            Creates this attribute on the `macro_mol` instance. This
            allows the function to keep track of which molecule from
            `database` should be used in the substitution.

        Returns
        -------
        Cage
            A new cage with the same linker as `macro_mol` but a
            different building-block*. The building-block* is selected
            according to the description in this docstring.

        """

        if not hasattr(self, '_similar_bb_mols'):
            self._similar_bb_mols = {}

        # The idea here is to create a list of molecules from
        # `database` ordered by similarity to the building block of
        # `macro_mol`. Each time this function is called on `macro_mol`
        # the next molecule from this list is used to substitute the
        # building block of the cage and create a new mutant.

        _, lk = max(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))

        _, og_bb = min(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))

        if macro_mol not in self._similar_bb_mols:
            self._similar_bb_mols[macro_mol] = iter(
                                    og_bb.similar_molecules(database))

        sim_mol = next(self._similar_bb_mols[macro_mol])[-1]
        new_bb = StructUnit3(sim_mol, fg)

        if len(og_bb.bonder_ids) != len(new_bb.bonder_ids):
            raise MutationError(
              ('\n\nMUTATION ERROR: Replacement building block does'
               ' not have the same number of functional groups as '
               'the original building block.\n\nOriginal building '
              'block:\n\n{}\n\nReplacement building block:\n\n'
              '{}\n\n').format(og_bb, new_bb))

        return Cage([new_bb, lk], macro_mol.topology)

    def cage_similar_lk(self, macro_mol, database, fg=None):
        """
        Substitute the linker with a similar one from `database`.

        All of the molecules in `database` are checked for similarity
        to the linker of `macro_mol`. The first time this mutation
        function is run on a cage, the most similar molecule in
        `database` is used to substitute the linker. The next time this
        mutation function is run on the same cage, the second most
        similar molecule from `database` is used and so on.

        Parameters
        ----------
        macro_mol : Cage
            The cage which is to have its linker substituted.

        database : str
            The full path of the database from which molecules are used
            to substitute the linker of `macro_mol`.

        fg : str (default = None)
            The name of a functional group. All molecules in
            `database` must have this functional group. This is the
            functional group which is used to assemble the
            macromolecules. If ``None`` it is assumed that the
            path `database` holds the name of the functional group.

        Modifies
        --------
        macro_mol._similar_lk_mols : generator
            Creates this attribute on the `macro_mol` instance. This
            allows the function to keep track of which molecule from
            `database` should be used in the substitution.

        Returns
        -------
        Cage
            A new cage with the same building-block* as `macro_mol` but
            a different linker. The linker is selected according to the
            description in this docstring.

        """

        if not hasattr(self, '_similar_lk_mols'):
            self._similar_lk_mols = {}

        # The idea here is to create a list of molecules from
        # `database` ordered by similarity to the linker of
        # `macro_mol`. Each time this function is called on `macro_mol`
        # the next molecule from this list is used to substitute the
        # linker of the cage and create a new mutant.

        _, og_lk = max(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))
        lk_type = type(og_lk)

        _, bb = min(zip(macro_mol.bb_counter.values(),
                        macro_mol.bb_counter.keys()))

        if macro_mol not in self._similar_lk_mols:
            self._similar_lk_mols[macro_mol] = iter(
                                    og_lk.similar_molecules(database))

        sim_mol = next(self._similar_lk_mols[macro_mol])[-1]
        new_lk = lk_type(sim_mol, fg)

        if len(og_lk.bonder_ids) != len(new_lk.bonder_ids):
            raise MutationError(
             ('\n\nMUTATION ERROR: Replacement linker does not'
              ' have the same number of functional groups as the'
              ' original linker.\n\nOriginal linker:\n\n{}\n\n'
              'Replacement linker:\n\n{}\n\n').format(og_lk, new_lk))

        return Cage([new_lk, bb], macro_mol.topology)

    def random_topology(self, macro_mol, topologies):
        """
        Changes `macro_mol` topology to a random one from `topologies`.

        A new instance of the same type as `macro_mol` is created. Ie
        if `macro_mol` was a Polymer instance then a Polymer instance
        will be returned.

        Parameters
        ----------
        macro_mol : MacroMolecule
            The macromolecule which is to be mutated.

        topologies : list of Topology instances
            This lists holds the topology instances from which one is
            selected at random to form a new molecule.

        Returns
        -------
        MacroMolecule
            A molecule generated by initializing a new instance
            with all the same parameters as `macro_mol` except for the
            topology.

        """

        tops = [x for x in topologies if
                                repr(x) != repr(macro_mol.topology)]
        topology = np.random.choice(tops)
        return macro_mol.__class__(macro_mol.building_blocks, topology)
