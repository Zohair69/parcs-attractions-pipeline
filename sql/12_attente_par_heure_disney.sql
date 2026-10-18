SELECT
nom_parc,
EXTRACT(HOUR FROM DATETIME(date_maj_api, "Europe/Paris")) AS heure_paris,
COUNT(DISTINCT DATE(date_maj_api, "Europe/Paris")) AS nb_jours_releves,
COUNT(*) AS nb_releves,
ROUND(100 * AVG(IF(est_ouverte, 1, 0)), 1) AS taux_ouverture_pct,
ROUND(AVG(IF(est_ouverte AND NOT est_single_rider, temps_attente_min, NULL)), 1) AS
attente_moyenne_min
FROM ayline_parcs.temps_attente
WHERE id_parc IN (4, 28)
GROUP BY nom_parc, heure_paris
ORDER BY nom_parc, heure_paris