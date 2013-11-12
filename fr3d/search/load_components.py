"""
This is a module to load the components from the database. It uses the index of
component from its cif file to load it from the database.
"""

import itertools as it

import collections as coll

from fr3d.data import Atom
from fr3d.data import Component


COMPONENT_QUERY = """
SELECT
    U.pdb AS 'pdb',
    U.model AS 'model',
    U.chain AS 'chain',
    U.seq_id AS 'number',
    U.comp_id AS 'sequence',
    O.`index` AS 'index',
    U.sym_op AS 'symmetry',
    U.ins_code AS 'ins_code'

FROM pdb_unit_ordering AS O

JOIN pdb_unit_id_correspondence AS U
ON
    O.nt_id = U.old_id

WHERE
    O.pdb = ?
    AND U.pdb_file = ?
    AND O.`index` in (%s)
;
"""

ATOM_QUERY = """
SELECT
    A.x as 'x',
    A.y as 'y',
    A.z as 'z',
    A.name as 'name',
    O.`index` as 'component_index'

from pdb_unit_ordering as O

join atom_data as A
ON
    O.nt_id = A.nt_id

JOIN pdb_unit_id_correspondence AS U
ON
    O.nt_id = U.old_id

where
    O.pdb = ?
    AND U.pdb_file = ?
    AND O.`index` in (%s)
;
"""


def lookup(cursor, pdb, filetype, motifs, component_query=COMPONENT_QUERY,
           atom_query=ATOM_QUERY):
    """Do the lookup for components. This will use the COMPONENT_QUERY constant
    to create a query which returns all matching components from the database.
    The query is designed with our current database in mind, however this could
    be changed later. The result of doing cursor.execute should be a iterable
    of dictionaries.

    :cursor: A cursor object to execute the query.
    :pdb: PDB name to use
    :motifs: A list of lists of indexes to lookup.
    :component_query: The query string to use.
    :atom_query: The query string to use to load atoms.
    :returns: A generator for each unique component requested.
    """

    numbers = set(it.chain.from_iterable(motifs))

    params = [pdb, filetype]
    params.extend(numbers)
    params = tuple(params)

    atoms = coll.defaultdict(list)
    query = atom_query % ','.join(['?'] * len(numbers))
    for ans in cursor.execute(query, params):
        atom = Atom(**ans)
        atoms[atom.component_index].append(atom)

    query = component_query % ','.join(['?'] * len(numbers))
    for ans in cursor.execute(query, params):
        component = Component(**ans)
        yield component


def load_components(cursor, pdb, motifs, lookup=lookup):
    """Load components from the database.

    :cursor: Cursor object to query with
    :pdb: PDB file to query for components.
    :motifs: List of lists of numbers representing the components.
    :lookup: A callable which take the pdb and list of numbers to produce a
    iterable of tuples of number, Component.
    :returns: A generator of list of lists of Components that match the given
    motifs.
    """

    mapping = {obj.index: obj for obj in lookup(pdb, motifs)}
    for motif in motifs:
        yield [mapping[number] for number in motif]
