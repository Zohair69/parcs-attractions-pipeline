-- Analyse 3 : attente moyenne selon le type de temps (jointure temps d'attente x météo), parcs Disney
SELECT
  m.libelle_meteo,
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
GROUP BY m.libelle_meteo
ORDER BY attente_moyenne_min DESC;

-- Analyse 3 bis : même calcul, parc par parc (pour séparer l'effet du parc de celui de la météo)
SELECT
  t.nom_parc,
  m.libelle_meteo,
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
ORDER BY t.nom_parc, attente_moyenne_min DESC;