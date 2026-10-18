SELECT
  DATE(date_execution, "Europe/Paris") AS jour,
  COUNT(*) AS nb_executions,
  COUNTIF(statut != 'ECHEC') AS nb_reussies
FROM ayline_parcs.logs_collecte
GROUP BY jour
ORDER BY jour;