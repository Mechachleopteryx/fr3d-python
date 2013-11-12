CREATE TABLE pdb_coordinates (
   id         VARCHAR PRIMARY KEY,
   pdb        VARCHAR,
   pdb_type   VARCHAR,
   model      INTEGER,
   chain      VARCHAR,
   number     INTEGER,
   unit       VARCHAR,
   `ins_code` VARCHAR,
   `index`    INTEGER
);
