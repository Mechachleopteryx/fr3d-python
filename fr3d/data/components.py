from fr3d.data.base import EntitySelector
from fr3d.data.base import AtomProxy
from fr3d.data.atoms import Atom
from fr3d import definitions as defs
from fr3d.geometry.superpositions import besttransformation
from fr3d.geometry import angleofrotation as angrot
import numpy as np

from fr3d.unit_ids import encode

class Component(EntitySelector):
    """This represents things like nucleic acids, amino acids, small molecules
    and ligands.
    """

    def __init__(self, atoms, pdb=None, model=None, type=None, chain=None,
                 symmetry=None, sequence=None, number=None, index=None,
                 insertion_code=None, polymeric=None, alt_id=None):
        """Create a new Component.

        :atoms: The atoms this component is composed of.
        :pdb: The pdb this is a part of.
        :model: The model number.
        """

        self._atoms = atoms
        self.pdb = pdb
        self.model = model
        self.type = type
        self.chain = chain
        self.symmetry = symmetry
        self.sequence = sequence
        self.number = number
        self.index = index
        self.insertion_code = insertion_code
        self.polymeric = polymeric
        self.alt_id = alt_id
        self.centers = AtomProxy(self._atoms)

        if self.sequence in defs.RNAbaseheavyatoms:
            atoms = defs.RNAbaseheavyatoms[self.sequence]
            self.centers.define('base', atoms)

        if self.sequence in defs.nt_sugar:
            atoms = defs.nt_sugar[self.sequence]
            self.centers.define('nt_sugar', atoms)

        if self.sequence in defs.nt_phosphate:
            atoms = defs.nt_phosphate[self.sequence]
            self.centers.define('nt_phosphate', atoms)

        if self.sequence in defs.aa_fg:
            atoms = defs.aa_fg[self.sequence]
            self.centers.define('aa_fg', atoms)

        if self.sequence in defs.aa_backbone:
            atoms = defs.aa_backbone[self.sequence]
            self.centers.define('aa_backbone', atoms)

        if self.sequence in defs.modified_nucleotides:
            atoms = defs.modified_nucleotides[self.sequence]["atoms"].values()
            self.centers.define('base', atoms)

        self.calculate_rotation_matrix()


    def atoms(self, **kwargs):
        """Get, filter and sort the atoms in this component. Access is as
        described by EntitySelector.

        :kwargs: The keyword arguments to filter and sort by.
        :returns: A list of the requested atoms.
        """

        name = kwargs.get('name')
        if isinstance(name, basestring):
            definition = self.centers.definition(name)
            if definition:
                kwargs['name'] = definition

        return EntitySelector(self._atoms, **kwargs)

    def coordinates(self, **kwargs):
        """Get the coordaintes of all atoms in this component. This will
        filter to the requested atoms, sort and then provide a numpy array
        of all coordinates for the given atoms.

        :kwargs: Arguments to filter and sort by.
        :returns: A numpy array of the coordinates.
        """
        return np.array([atom.coordinates() for atom in self.atoms(**kwargs)])

    def select(self, **kwargs):
        """Select a group of atoms to create a new component out of.

        :kwargs: As for atoms.
        :returns: A new Component
        """
        return Component(list(self.atoms(**kwargs)),
                         pdb=self.pdb,
                         model=self.model,
                         type=self.type,
                         chain=self.chain,
                         symmetry=self.symmetry,
                         sequence=self.sequence,
                         number=self.number,
                         index=self.index,
                         insertion_code=self.insertion_code,
                         alt_id=self.alt_id,
                         polymeric=self.polymeric)

    def is_complete(self, names, key='name'):
        """This checks if we can find all atoms in this entity with the given
        names. This assumes that the names for each atom are unique. If you
        wish to use something other than name use the key argument. However, it
        must provide a unique value for each atom, if several atoms with the
        same value are found will cause the function to behave oddly.

        :names: The list of names to check for.
        :key: The key to use for getting atoms. Defaults to name.
        :returns: True if all atoms with the given name are present.
        """
        kwargs = {key: names}
        found = list(self.atoms(**kwargs))
        return len(found) == len(names)

    def calculate_rotation_matrix(self):
        """Calculate a rotation matrix that will rotate the atoms in an RNA
        base into a standard orientation in the xy plane with the Watson-
        Crick edge in the positive x and y quadrant.
        """

        if self.sequence not in defs.RNAbaseheavyatoms and \
                self.sequence not in defs.modified_nucleotides:
            return None

        R = []
        S = []

        if self.sequence in defs.modified_nucleotides:
            current = defs.modified_nucleotides[self.sequence]
            standard_coords = defs.RNAbasecoordinates[current["standard"]]
            for standard, modified in current["atoms"].items():
                coords = list(self.centers[modified])
                if coords:
                    R.append(coords)
                    S.append(standard_coords[standard])

        if self.sequence in defs.RNAbaseheavyatoms:
            baseheavy = defs.RNAbaseheavyatoms[self.sequence]
            for atom in self.atoms(name=baseheavy):
                coordinates = atom.coordinates()
                R.append(coordinates)
                S.append(defs.RNAbasecoordinates[self.sequence][atom.name])

        R = np.array(R)
        R = R.astype(np.float)
        S = np.array(S)
        try:
            rotation_matrix, fitted, base_center, rmsd, sse = \
                besttransformation(R, S)
            #print self.unit_id(), "Successful rotation matrix"

            #print "Check that two methods of computing the base center are the same"
            #print base_center
            #print self.centers["base"]
        except:
            print self.unit_id(), "Rotation matrix calculation failed"
            return None

        self.rotation_matrix = rotation_matrix

    def infer_hydrogens(self):
        """Infer the coordinates of the hydrogen atoms of this component.
        Currently, it only works for RNA with .sequence
        """

        if self.sequence in defs.RNAbasehydrogens:
            hydrogens = defs.RNAbasehydrogens[self.sequence]
            coordinates = defs.RNAbasecoordinates[self.sequence]

            for hydrogenatom in hydrogens:
                hydrogencoordinates = coordinates[hydrogenatom]
                newcoordinates = self.centers["base"] + \
                    np.dot(hydrogencoordinates, np.transpose(self.rotation_matrix))
                self._atoms.append(Atom(name=hydrogenatom,
                                        x=newcoordinates[0, 0],
                                        y=newcoordinates[0, 1],
                                        z=newcoordinates[0, 2]))

    def transform(self, transform_matrix):
        """Create a new component from "self" by applying the 4x4 transformation
        matrix. This does not keep the rotation matrix if any,
        but will keep any added hydrogens.

        :transform_matrix: The 4x4 transformation matrix to apply.
        :returns: A new Component with the same properties except with
        transformed coordinates.
        """

        atoms = [atom.transform(transform_matrix) for atom in self.atoms()]
        comp = Component(atoms, pdb=self.pdb,
                         model=self.model,
                         type=self.type,
                         chain=self.chain,
                         symmetry=self.symmetry,
                         sequence=self.sequence,
                         number=self.number,
                         index=self.index,
                         insertion_code=self.insertion_code,
                         alt_id=self.alt_id,
                         polymeric=self.polymeric)
        comp.infer_hydrogens()
        return comp

    def translate_rotate_component(self, component):
        """Translate and rotate the atoms in component according to
        the translation and rotation that will bring self to standard
        position at the origin.
        :param Component residue:  the residue to move
        :returns Component newcomp
        """

        atoms = [self.translate_rotate_atom(atom) for atom in component.atoms()]
        newcomp = Component(atoms, pdb=component.pdb,
                         model=component.model,
                         type=component.type,
                         chain=component.chain,
                         symmetry=component.symmetry,
                         sequence=component.sequence,
                         number=component.number,
                         index=component.index,
                         insertion_code=component.insertion_code,
                         alt_id=component.alt_id,
                         polymeric=component.polymeric)
        newcomp.infer_hydrogens()
        return newcomp

    def translate_rotate_atom(self, atom):
        """Translate and rotate atom according to
        the translation and rotation that will bring self to standard
        position at the origin.

        :param Atom atom: The Atom to move.
        :returns Atom: The moved atom.
        """

        atom_coord = atom.coordinates()
        translated_coord = np.subtract(atom_coord, self.centers["base"])
        translated_coord_matrix = np.matrix(translated_coord)
        rotated_coord = translated_coord_matrix * self.rotation_matrix
        coord_array = np.array(rotated_coord)
        a = coord_array.flatten()
        x, y, z = a.tolist()
        return Atom(x=x, y=y, z=z,
                    pdb=atom.pdb,
                    model=atom.model,
                    chain=atom.chain,
                    component_id=atom.component_id,
                    component_number=atom.component_number,
                    component_index=atom.component_index,
                    insertion_code=atom.insertion_code,
                    alt_id=atom.alt_id,
                    group=atom.group,
                    type=atom.type,
                    name=atom.name,
                    symmetry=atom.symmetry,
                    polymeric=atom.polymeric)

    def standard_transformation(self):
        """Returns a 4X4 transformation matrix which can be used to transform
        any component to the same relative location as the "self" argument in
        its standard location. If this is not an RNA component then this returns
        None.
        :returns: A numpy array suitable for input to self.transform to produce
        a transformed component.
        """

        if 'base' not in self.centers:
            return None
        base_center = self.centers["base"]
        if len(base_center) == 0:
            return None
        seq = self.sequence
        dist_translate = base_center

        rotation_matrix_transpose = self.rotation_matrix.transpose()

        matrix = np.zeros((4, 4))
        matrix[0:3, 0:3] = rotation_matrix_transpose
        matrix[0:3, 3] = -np.dot(rotation_matrix_transpose, dist_translate)
        matrix[3, 3] = 1.0

        return matrix

    def translate(self, aa_residue):
        if 'base' not in self.centers:
            return None
        rotation = self.rotation_matrix
        for atom in aa_residue:
            dist_translate = np.subtract(atom, self.centers["base"])
            rotated_atom = dist_translate*rotation
            coord_array = np.array(rotated_atom)
            a = coord_array.flatten()
            coord = a.tolist()
        return coord


    def unit_id(self):
        """Compute the unit id of this Component.

        :returns: The unit id.
        """

        return encode({
            'pdb': self.pdb,
            'model': self.model,
            'chain': self.chain,
            'component_id': self.sequence,
            'component_number': self.number,
            'alt_id': self.alt_id,
            'insertion_code': self.insertion_code,
            'symmetry': self.symmetry
        })

    def atoms_within(self, other, cutoff, using=None, to=None, min_number=1):
        """Determine if there are any atoms from another component within some
        distance.

        :other: Another component to compare agains.
        :using: The atoms from this component to compare with.
        :to: The atoms from the other component to compare against.
        :cutoff: The distances atoms must be within. Default 4.0
        """

        kw1 = {}
        if using:
            kw1['name'] = using

        kw2 = {}
        if to:
            kw2['name'] = to

        n = 0
        for atom1 in self.atoms(**kw1):
            for atom2 in other.atoms(**kw2):
                if atom1.distance(atom2) <= abs(cutoff):
                    n = n+1

        if n >= min_number:
            return True

    def distance(self, other, using='*', to='*'):
        """Compute a center center distance between this and another component.

        :other: The other component to get distance to.
        :using: A list of atom names to use for this component. Defaults to '*'
        meaning all atoms.
        :to: A list of atoms names for the second component. Defaults to '*'
        meaning all atoms.
        :returns: The distance between the two centers.
        """
        coordinates = self.centers[using]
        other_coord = other.centers[to]
        distance = np.subtract(coordinates, other_coord)
        return np.linalg.norm(distance)

    def __len__(self):
        """Compute the length of this Component. This is the number of atoms in
        this residue.

        :returns: The number of atoms.
        """
        return len(self._atoms)

    def __eq__(self, other):
        return isinstance(other, Component) and \
            self.pdb == other.pdb and \
            self.model == other.model and \
            self.chain == other.chain and \
            self.symmetry == other.symmetry and \
            self.sequence == other.sequence and \
            self.number == other.number and \
            self.insertion_code == other.insertion_code and \
            self.alt_id == other.alt_id

    def __repr__(self):
        return '<Component %s>' % self.unit_id()

    def angle_between_normals(self, aa_residue):
        vec1 = self.normal_calculation()
        vec2 = aa_residue.normal_calculation()
        return angrot.angle_between_planes(vec1, vec2)

    def normal_calculation(self):
        key = self.sequence
        P1 = self.centers[defs.planar_atoms[key][0]]
        P2 = self.centers[defs.planar_atoms[key][1]]
        P3 = self.centers[defs.planar_atoms[key][2]]
        vector = np.cross((P2 - P1), (P3-P1))
        return vector

    def enough_hydrogen_bonds(self, second, min_distance=4, min_bonds=2):
        """Calculates atom to atom distance of part "aa_part" of neighboring
        amino acids of type "aa" from each atom of base. Only returns a pair
        of aa/nt if two or more atoms are within the cutoff distance.
        """

        HB_atoms = set(['N', 'NH1','NH2','NE','NZ','ND1','NE2','O','OD1','OE1','OE2', 'OG', 'OH'])
        n = 0
        base_seq = self.sequence()
        for base_atom in self.atoms(name=defs.RNAbaseheavyatoms[base_seq]):
            for aa_atom in second.atoms(name=defs.aa_fg[second.sequence]):
                distance = np.subtract(base_atom.coordinates(), aa_atom.coordinates())
                distance = np.linalg.norm(distance)
                if distance <= min_distance and aa_atom.name in HB_atoms:
                    n = n + 1
                    if n > min_bonds:
                        return True
        return False

    def stacking_tilt(aa_residue, aa_coordinates):
        baa_dist_list = []

        for aa_atom in aa_residue.atoms(name=defs.aa_fg[aa_residue.sequence]):
            key = aa_atom.name
            aa_z = aa_coordinates[key][2]
            baa_dist_list.append(aa_z)
        max_baa = max(baa_dist_list)
        min_baa = min(baa_dist_list)
        diff = max_baa - min_baa
        #print aa_residue.unit_id(), diff
        if diff <= defs.tilt_cutoff[aa_residue.sequence]:
            return "stacked"
    
    def distance_metrics(self, aa_residue):
        squared_xy_dist_list = []
        aa_z_list = []
        base_coord = self.centers["base"]
        for aa_atom in aa_residue.atoms(name=defs.aa_fg[aa_residue.sequence]):
            try:
                aa_x = np.subtract(aa_atom.x, base_coord[0])
                aa_y= np.subtract(aa_atom.y, base_coord[1])
                aa_z = np.subtract(aa_atom.z, base_coord[2])
                squared_xy_dist = (aa_x**2) + (aa_y**2)
                squared_xy_dist_list.append(squared_xy_dist)
                aa_z_list.append(aa_z)
            except:
                print "Incomplete residue"