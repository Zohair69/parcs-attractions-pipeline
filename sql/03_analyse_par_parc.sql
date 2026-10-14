-- Analyse 1 : attente moyenne et taux d'ouverture par parc
-- Règles : attractions fermées et files Single Rider exclues du calcul de l'attente.
SELECT
  nom_parc,
  COUNT(*) AS nb_mesures,
  ROUND(100 * COUNTIF(est_ouverte) / COUNT(*), 1) AS taux_ouverture_pct,
  ROUND(AVG(IF(est_ouverte AND NOT est_single_rider, temps_attente_min, NULL)), 1) AS attente_moyenne_min,
  MAX(IF(est_ouverte AND NOT est_single_rider, temps_attente_min, NULL)) AS attente_max_min
FROM ayline_parcs.temps_attente
GROUP BY nom_parc
ORDER BY attente_moyenne_min DESC