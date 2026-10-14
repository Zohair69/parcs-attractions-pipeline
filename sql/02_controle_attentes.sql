-- Contrôle : les parcs transmettent-ils des temps d'attente ?
SELECT
  nom_parc,
  COUNTIF(est_ouverte) AS nb_mesures_ouvertes,
  COUNTIF(est_ouverte AND temps_attente_min > 0) AS nb_mesures_attente_positive
FROM ayline_parcs.temps_attente
GROUP BY nom_parc
ORDER BY nb_mesures_attente_positive DESC