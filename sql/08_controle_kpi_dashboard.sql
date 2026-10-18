-- 08_controle_kpi_dashboard : vérifier les chiffres affichés dans Looker Studio
WITH source AS (
  SELECT
    t.nom_parc,
    t.nom_attraction,
    t.est_ouverte,
    IF(t.est_ouverte, 1, 0) AS ouverte_num,
    t.temps_attente_min,
    IF(t.est_ouverte AND NOT t.est_single_rider AND t.id_parc IN (4, 28),
       t.temps_attente_min, NULL) AS attente_analysable_min,
    DATETIME(t.date_maj_api, "Europe/Paris") AS date_heure_paris,
    DATE(t.date_maj_api, "Europe/Paris") AS jour,
    EXTRACT(HOUR FROM DATETIME(t.date_maj_api, "Europe/Paris")) AS heure_paris,
    m.libelle_meteo,
    m.temperature_c,
    m.precipitation_mm
  FROM ayline_parcs.temps_attente AS t
  LEFT JOIN ayline_parcs.meteo_horaire AS m
    ON t.id_parc = m.id_parc
    AND TIMESTAMP_TRUNC(t.date_maj_api, HOUR) = m.heure_utc
)
SELECT
  MIN(date_heure_paris) AS premiere_mesure,
  MAX(date_heure_paris) AS derniere_mesure,
  COUNT(DISTINCT nom_parc) AS nb_parcs,
  STRING_AGG(DISTINCT nom_parc, ' | ') AS liste_parcs,
  ROUND(AVG(attente_analysable_min), 1) AS attente_moy_disney,
  ROUND(100 * AVG(ouverte_num), 1) AS taux_ouverture_pct,
  COUNT(*) AS nb_mesures,
  (SELECT COUNT(*) FROM ayline_parcs.temps_attente) AS nb_lignes_table_brute
FROM source;