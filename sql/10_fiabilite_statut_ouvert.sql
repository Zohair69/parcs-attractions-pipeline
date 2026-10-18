
SELECT
nom_parc,
COUNT(DISTINCT nom_attraction) AS nb_attractions,
COUNT(DISTINCT TIMESTAMP_TRUNC(date_maj_api, HOUR)) AS nb_heures_collectees,
ROUND(100 * AVG(IF(EXTRACT(HOUR FROM DATETIME(date_maj_api, "Europe/Paris")) BETWEEN 1 AND 6,
IF(est_ouverte, 1, 0), NULL)), 1) AS taux_ouverture_nuit_pct
FROM ayline_parcs.temps_attente
GROUP BY nom_parc
ORDER BY nom_parc
