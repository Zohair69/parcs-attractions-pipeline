-- Analyse 2 : attente moyenne par heure de la journée (heure de Paris), parcs Disney
SELECT
  nom_parc,
  EXTRACT(HOUR FROM DATETIME(date_maj_api, "Europe/Paris")) AS heure_paris,
  COUNT(*) AS nb_mesures,
  ROUND(AVG(temps_attente_min), 1) AS attente_moyenne_min
FROM ayline_parcs.temps_attente
WHERE est_ouverte
  AND NOT est_single_rider
  AND id_parc IN (4, 28)   -- Disneyland Park Paris et Disney Adventure World Paris
GROUP BY nom_parc, heure_paris
ORDER BY nom_parc, heure_paris