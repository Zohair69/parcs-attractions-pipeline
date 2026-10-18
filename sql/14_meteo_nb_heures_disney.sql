SELECT
t.nom_parc,
m.libelle_meteo,
COUNT(DISTINCT TIMESTAMP_TRUNC(t.date_maj_api, HOUR)) AS nb_heures,
COUNT(DISTINCT DATE(t.date_maj_api, "Europe/Paris")) AS nb_jours,
COUNT(*) AS nb_mesures,
ROUND(AVG(t.temps_attente_min), 1) AS attente_moyenne_min,
ROUND(AVG(m.temperature_c), 1) AS temperature_moyenne_c
FROM ayline_parcs.temps_attente AS t
JOIN ayline_parcs.meteo_horaire AS m
ON t.id_parc = m.id_parc
AND TIMESTAMP_TRUNC(t.date_maj_api, HOUR) = m.heure_utc
WHERE t.est_ouverte
AND NOT t.est_single_rider
AND t.id_parc IN (4, 28)
GROUP BY t.nom_parc, m.libelle_meteo
ORDER BY t.nom_parc, nb_heures DESC