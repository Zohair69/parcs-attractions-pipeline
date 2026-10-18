SELECT
t.nom_parc,
COUNT(DISTINCT m.heure_utc) AS nb_heures_ouvertes,
COUNT(DISTINCT IF(m.precipitation_mm > 0, m.heure_utc, NULL)) AS nb_heures_avec_pluie,
MAX(m.precipitation_mm) AS pluie_max_mm
FROM ayline_parcs.temps_attente AS t
JOIN ayline_parcs.meteo_horaire AS m
ON t.id_parc = m.id_parc
AND TIMESTAMP_TRUNC(t.date_maj_api, HOUR) = m.heure_utc
WHERE t.est_ouverte
AND t.id_parc IN (4, 28)
GROUP BY t.nom_parc