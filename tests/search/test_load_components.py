import os
import csv
import sqlite3

from unittest import TestCase

from fr3d.search.load_components import lookup


class LoadingTest(TestCase):
    def setUp(self):
        self.motifs = [[0, 1, 2, 3], [3, 2, 1, 0], [2, 1, 0, 5]]
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.build_tables()
        self.load_data()

    def tearDown(self):
        self.db.close()

    def build_tables(self):
        for filename in os.listdir("files/schema"):
            path = os.path.join("files/schema", filename)
            with open(path, 'rb') as raw:
                command = raw.read()
            self.cursor.execute(command)

    def load_data(self):
        for filename in os.listdir("files/data"):
            tablename, ext = os.path.splitext(filename)
            path = os.path.join("files/data", filename)
            with open(path, 'rb') as raw:
                if ext == ".csv":
                    reader = csv.DictReader(raw)
                    data = [row for row in reader]
            fields = ','.join(['`%s`' % n for n in data[0].keys()])
            params = ','.join([':%s' % n for n in data[0].keys()])
            insert = "insert into %s (%s) values (%s);" % \
                (tablename, fields, params)
            self.cursor.executemany(insert, data)


class LookupTest(LoadingTest):
    def test_finds_enough_components(self):
        val = len(list(lookup(self.cursor, '2AVY', 'pdb', self.motifs)))
        ans = 5
        self.assertEqual(val, ans)

    def test_finds_all_atoms(self):
        self.fail()

    def test_generates_components(self):
        self.fail()

    def test_generates_atoms(self):
        self.fail()


class LoadComponentsTest(LoadingTest):
    pass
