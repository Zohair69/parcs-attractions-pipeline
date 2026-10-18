SELECT *
FROM ayline_parcs.parcs
WHERE id_parc NOT IN (SELECT DISTINCT id_parc FROM ayline_parcs.temps_attente)