SELECT
nom_parc,
ROUND(100 * AVG(IF(est_ouverte, 1, 0)), 1) AS taux_ouverture_pct,
ROUND(100 * AVG(IF(EXTRACT(HOUR FROM DATETIME(date_maj_api, "Europe/Paris")) != 0,
IF(est_ouverte, 1, 0), NULL)), 1) AS taux_hors_minuit_pct
FROM ayline_parcs.temps_attente
WHERE id_parc IN (4, 28)
GROUP BY nom_parc