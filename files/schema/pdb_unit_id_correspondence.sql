CREATE TABLE pdb_unit_id_correspondence (
   id      INTEGER PRIMARY KEY,
   old_id  VARCHAR,
   unit_id VARCHAR,
   pdb     VARCHAR,
   model   INTEGER,
   chain   VARCHAR,
   seq_id  INTEGER,
   comp_id VARCHAR,
   atom    VARCHAR,
   alt_id  VARCHAR,
   ins_code VARCHAR,
   sym_op  VARCHAR,
   pdb_file VARCHAR
);
