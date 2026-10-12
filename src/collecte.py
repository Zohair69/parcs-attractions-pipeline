"""
Collecte automatique des temps d'attente des parcs d'attractions (API Queue-Times)
et chargement dans BigQuery.
Projet Ayline Parcs - auteur : Zohair
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from google.oauth2 import service_account

# ============ CONFIGURATION ============
PROJET = "ayline-parcs"
DATASET = "ayline_parcs"
TABLE_DONNEES = f"{PROJET}.{DATASET}.temps_attente"
TABLE_LOGS = f"{PROJET}.{DATASET}.logs_collecte"
LOCALISATION = "EU"

PARCS = {
    4: "Disneyland Park Paris",
    28: "Disney Adventure World Paris",
    9: "Parc Astérix",
    291: "Futuroscope",
    301: "Walibi Rhône-Alpes",
    303: "Le Pal",
    336: "Nigloland",
    304: "Vulcania",
    327: "Le Parc du Petit Prince",
    320: "PanoraMagique",
}

# Clé unique d'une mesure : un parc, une attraction, une mise à jour de l'API
CLE_UNIQUE = ["id_parc", "id_attraction", "date_maj_api"]

SCHEMA_DONNEES = [
    bigquery.SchemaField("id_parc", "INTEGER"),
    bigquery.SchemaField("nom_parc", "STRING"),
    bigquery.SchemaField("zone", "STRING"),
    bigquery.SchemaField("id_attraction", "INTEGER"),
    bigquery.SchemaField("nom_attraction", "STRING"),
    bigquery.SchemaField("est_ouverte", "BOOLEAN"),
    bigquery.SchemaField("temps_attente_min", "INTEGER"),
    bigquery.SchemaField("date_maj_api", "TIMESTAMP"),
    bigquery.SchemaField("date_collecte", "TIMESTAMP"),
    bigquery.SchemaField("est_single_rider", "BOOLEAN"),
]

SCHEMA_LOGS = [
    bigquery.SchemaField("date_execution", "TIMESTAMP"),
    bigquery.SchemaField("statut", "STRING"),
    bigquery.SchemaField("nb_lignes_collectees", "INTEGER"),
    bigquery.SchemaField("nb_doublons_ignores", "INTEGER"),
    bigquery.SchemaField("nb_lignes_inserees", "INTEGER"),
    bigquery.SchemaField("parcs_en_erreur", "STRING"),
    bigquery.SchemaField("message", "STRING"),
]

# ============ CONNEXION ============
def connexion_bigquery():
    """Sur GitHub Actions, la clé vient d'un secret ; en local, d'un fichier hors du projet."""
    cle_json = os.environ.get("GCP_CLE_JSON")
    if cle_json:
        identifiants = service_account.Credentials.from_service_account_info(json.loads(cle_json))
    else:
        chemin = Path.home() / "cles_gcp" / "cle_bigquery.json"
        identifiants = service_account.Credentials.from_service_account_file(chemin)
    return bigquery.Client(credentials=identifiants, project=PROJET)


# ============ COLLECTE ============
def collecter_parc(id_parc, nom_parc, date_collecte):
    """Appelle l'API pour un parc et renvoie une ligne par attraction."""
    url = f"https://queue-times.com/parks/{id_parc}/queue_times.json"
    reponse = requests.get(url, timeout=10)
    reponse.raise_for_status()   # erreur si le code HTTP n'est pas 200
    data = reponse.json()

    lignes = []

    def ajouter(attraction, zone):
        lignes.append({
            "id_parc": id_parc,
            "nom_parc": nom_parc,
            "zone": zone,
            "id_attraction": attraction["id"],
            "nom_attraction": attraction["name"],
            "est_ouverte": attraction["is_open"],
            "temps_attente_min": attraction["wait_time"],
            "date_maj_api": attraction["last_updated"],
            "date_collecte": date_collecte,
        })

    for zone in data.get("lands", []):          # attractions rangées dans des zones
        for attraction in zone.get("rides", []):
            ajouter(attraction, zone.get("name"))
    for attraction in data.get("rides", []):    # attractions hors zone
        ajouter(attraction, None)

    return lignes


# ============ NETTOYAGE ============
def nettoyer(df):
    """Mêmes règles que dans le notebook d'exploration."""
    df["date_maj_api"] = pd.to_datetime(df["date_maj_api"], utc=True)
    df["zone"] = df["zone"].fillna("Non renseignée")
    df["est_single_rider"] = df["nom_attraction"].str.contains("Single Rider", case=False)
    return df.drop_duplicates(subset=CLE_UNIQUE)


# ============ ANTI-DOUBLONS ============
def format_cle(id_parc, id_attraction, date):
    return f"{id_parc}|{id_attraction}|{date.strftime('%Y-%m-%dT%H:%M:%S')}"


def retirer_doublons_existants(client, df):
    """Retire les mesures déjà présentes dans BigQuery (même parc, attraction et date API)."""
    requete = f"SELECT DISTINCT id_parc, id_attraction, date_maj_api FROM `{TABLE_DONNEES}`"
    try:
        resultat = client.query(requete, location=LOCALISATION).result()
    except NotFound:
        return df   # première exécution : la table n'existe pas encore
    deja_presentes = {format_cle(r.id_parc, r.id_attraction, r.date_maj_api) for r in resultat}
    cles_df = df.apply(lambda l: format_cle(l["id_parc"], l["id_attraction"], l["date_maj_api"]), axis=1)
    return df[~cles_df.isin(deja_presentes)]


# ============ CHARGEMENT ============
def charger(client, lignes, table, schema):
    config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND")
    job = client.load_table_from_json(lignes, table, job_config=config, location=LOCALISATION)
    job.result()


def ecrire_log(client, date_execution, statut, nb_collectees=0, nb_doublons=0,
               nb_inserees=0, parcs_en_erreur=None, message=""):
    log = {
        "date_execution": date_execution.isoformat(),
        "statut": statut,
        "nb_lignes_collectees": nb_collectees,
        "nb_doublons_ignores": nb_doublons,
        "nb_lignes_inserees": nb_inserees,
        "parcs_en_erreur": ", ".join(parcs_en_erreur or []),
        "message": message,
    }
    charger(client, [log], TABLE_LOGS, SCHEMA_LOGS)
    print("Log enregistré :", log)


# ============ PROGRAMME PRINCIPAL ============
def main():
    date_execution = datetime.now(timezone.utc)
    print(f"=== Début de la collecte : {date_execution.isoformat()} ===")
    client = connexion_bigquery()

    try:
        toutes_les_lignes, parcs_en_erreur = [], []
        for id_parc, nom_parc in PARCS.items():
            try:
                lignes = collecter_parc(id_parc, nom_parc, date_execution.isoformat())
                toutes_les_lignes.extend(lignes)
                print(f"{nom_parc} : {len(lignes)} attractions récupérées")
            except requests.exceptions.RequestException as erreur:
                parcs_en_erreur.append(nom_parc)
                print(f"ERREUR {nom_parc} : {erreur}")

        if not toutes_les_lignes:
            ecrire_log(client, date_execution, "ECHEC", parcs_en_erreur=parcs_en_erreur,
                       message="Aucune donnée récupérée")
            return

        df = nettoyer(pd.DataFrame(toutes_les_lignes))
        nb_collectees = len(df)

        df_nouvelles = retirer_doublons_existants(client, df)
        nb_inserees = len(df_nouvelles)
        nb_doublons = nb_collectees - nb_inserees

        if nb_inserees > 0:
            lignes_json = json.loads(df_nouvelles.to_json(orient="records", date_format="iso"))
            charger(client, lignes_json, TABLE_DONNEES, SCHEMA_DONNEES)

        statut = "SUCCES" if not parcs_en_erreur else "PARTIEL"
        print(f"Collectées : {nb_collectees} | Doublons ignorés : {nb_doublons} | Insérées : {nb_inserees}")
        ecrire_log(client, date_execution, statut, nb_collectees, nb_doublons,
                   nb_inserees, parcs_en_erreur)

    except Exception as erreur:
        ecrire_log(client, date_execution, "ECHEC", message=str(erreur))
        raise   # l'exécution apparaît en échec dans GitHub Actions


if __name__ == "__main__":
    main()