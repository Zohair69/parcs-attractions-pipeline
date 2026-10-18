SELECT
  nom_parc,
  FORMAT_DATE('%A', DATE(date_maj_api, "Europe/Paris")) AS jour_semaine,
  ROUND(100 * AVG(IF(est_ouverte, 1, 0)), 1) AS taux_ouverture_pct,
  COUNT(*) AS nb_mesures
FROM ayline_parcs.temps_attente
WHERE id_parc NOT IN (4, 28)
GROUP BY nom_parc, jour_semaine
ORDER BY nom_parc, jour_semaine;