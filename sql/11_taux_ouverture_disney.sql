
SELECT
ROUND(100 * AVG(IF(est_ouverte, 1, 0)), 1) AS taux_ouverture_disney_pct,
COUNT(*) AS nb_mesures_disney
FROM ayline_parcs.temps_attente
WHERE id_parc IN (4, 28)