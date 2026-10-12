-- Contrôle qualité : y a-t-il des doublons dans la table ?

SELECT id_parc, id_attraction, date_maj_api, COUNT(*) AS nb_occurrences
FROM ayline-parcs.ayline_parcs.temps_attente
GROUP BY id_parc, id_attraction, date_maj_api
HAVING COUNT(*) > 1