"""
Collecte de la météo horaire des parcs (API Open-Meteo) et chargement dans BigQuery.
Projet Ayline Parcs - auteur : Zohair
"""

import json
from datetime import datetime, timezone

import pandas as pd
import requests
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

# Réutilisation de la connexion et du chargement déjà écrits pour Queue-Times
from collecte import PROJET, DATASET, LOCALISATION, SCHEMA_LOGS, connexion_bigquery, charger

TABLE_METEO = f"{PROJET}.{DATASET}.meteo_horaire"
TABLE_PARCS = f"{PROJET}.{DATASET}.parcs"
TABLE_LOGS_METEO = f"{PROJET}.{DATASET}.logs_meteo"
URL_METEO = "https://api.open-meteo.com/v1/forecast"

SCHEMA_METEO = [
    bigquery.SchemaField("id_parc", "INTEGER"),
    bigquery.SchemaField("nom_parc", "STRING"),
    bigquery.SchemaField("heure_utc", "TIMESTAMP"),
    bigquery.SchemaField("temperature_c", "FLOAT"),
    bigquery.SchemaField("precipitation_mm", "FLOAT"),
    bigquery.SchemaField("code_meteo", "INTEGER"),
    bigquery.SchemaField("libelle_meteo", "STRING"),
    bigquery.SchemaField("vent_kmh", "FLOAT"),
    bigquery.SchemaField("date_collecte", "TIMESTAMP"),
]

SCHEMA_PARCS = [
    bigquery.SchemaField("id_parc", "INTEGER"),
    bigquery.SchemaField("nom_parc", "STRING"),
    bigquery.SchemaField("pays", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT"),
    bigquery.SchemaField("longitude", "FLOAT"),
]


# ============ PARCS FRANÇAIS ============
def recuperer_parcs_france():
    """Liste des parcs français et de leurs coordonnées (endpoint parks.json de Queue-Times)."""
    reponse = requests.get("https://queue-times.com/parks.json", timeout=10)
    reponse.raise_for_status()
    lignes = []
    for groupe in reponse.json():
        for parc in groupe["parks"]:
            if parc["country"] == "France":
                lignes.append({
                    "id_parc": parc["id"],
                    "nom_parc": parc["name"],
                    "pays": parc["country"],
                    "latitude": float(parc["latitude"]),
                    "longitude": float(parc["longitude"]),
                })
    return pd.DataFrame(lignes)


# ============ MÉTÉO ============
def libelle_meteo(code):
    """Codes météo WMO regroupés en libellés lisibles."""
    if code == 0:
        return "Ciel dégagé"
    if code in (1, 2):
        return "Peu nuageux"
    if code == 3:
        return "Couvert"
    if code in (45, 48):
        return "Brouillard"
    if 51 <= code <= 57:
        return "Bruine"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "Pluie"
    if 71 <= code <= 77 or code in (85, 86):
        return "Neige"
    if 95 <= code <= 99:
        return "Orage"
    return "Autre"


def collecter_meteo(parc):
    """Météo horaire d'un parc : 2 jours passés + aujourd'hui."""
    params = {
        "latitude": parc["latitude"],
        "longitude": parc["longitude"],
        "hourly": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": "UTC",
        "past_days": 2,
        "forecast_days": 1,
    }
    reponse = requests.get(URL_METEO, params=params, timeout=10)
    reponse.raise_for_status()
    df = pd.DataFrame(reponse.json()["hourly"])
    df["id_parc"] = int(parc["id_parc"])
    df["nom_parc"] = parc["nom_parc"]
    return df


def nettoyer(df, date_execution):
    """Mêmes règles que dans le notebook 02_exploration_meteo."""
    df = df.rename(columns={
        "time": "heure_utc",
        "temperature_2m": "temperature_c",
        "precipitation": "precipitation_mm",
        "weather_code": "code_meteo",
        "wind_speed_10m": "vent_kmh",
    })
    df["heure_utc"] = pd.to_datetime(df["heure_utc"], utc=True)
    df = df[df["heure_utc"] < date_execution]          # heures passées uniquement
    df = df.dropna(subset=["temperature_c", "code_meteo"])
    df["code_meteo"] = df["code_meteo"].astype(int)
    df["libelle_meteo"] = df["code_meteo"].apply(libelle_meteo)
    df["date_collecte"] = date_execution
    return df.drop_duplicates(subset=["id_parc", "heure_utc"]).reset_index(drop=True)


# ============ ANTI-DOUBLONS ============
def retirer_heures_existantes(client, df):
    """Retire les heures déjà présentes dans BigQuery pour chaque parc."""
    requete = f"SELECT DISTINCT id_parc, heure_utc FROM `{TABLE_METEO}`"
    try:
        resultat = client.query(requete, location=LOCALISATION).result()
    except NotFound:
        return df   # première exécution : la table n'existe pas encore
    deja = {f"{r.id_parc}|{r.heure_utc.strftime('%Y-%m-%dT%H')}" for r in resultat}
    cles = df["id_parc"].astype(str) + "|" + df["heure_utc"].dt.strftime("%Y-%m-%dT%H")
    return df[~cles.isin(deja)]


# ============ LOGS ============
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
    charger(client, [log], TABLE_LOGS_METEO, SCHEMA_LOGS)
    print("Log enregistré :", log)


# ============ PROGRAMME PRINCIPAL ============
def main():
    date_execution = datetime.now(timezone.utc)
    print(f"=== Début de la collecte météo : {date_execution.isoformat()} ===")
    client = connexion_bigquery()

    try:
        # 1. Table de référence des parcs (remplacée à chaque exécution)
        parcs = recuperer_parcs_france()
        config_parcs = bigquery.LoadJobConfig(schema=SCHEMA_PARCS, write_disposition="WRITE_TRUNCATE")
        client.load_table_from_json(parcs.to_dict(orient="records"), TABLE_PARCS,
                                    job_config=config_parcs, location=LOCALISATION).result()
        print(f"Table parcs mise à jour : {len(parcs)} parcs")

        # 2. Météo de chaque parc
        tables, parcs_en_erreur = [], []
        for _, parc in parcs.iterrows():
            try:
                tables.append(collecter_meteo(parc))
                print(f"{parc['nom_parc']} : météo récupérée")
            except requests.exceptions.RequestException as erreur:
                parcs_en_erreur.append(parc["nom_parc"])
                print(f"ERREUR {parc['nom_parc']} : {erreur}")

        if not tables:
            ecrire_log(client, date_execution, "ECHEC", parcs_en_erreur=parcs_en_erreur,
                       message="Aucune donnée météo récupérée")
            return

        df = nettoyer(pd.concat(tables, ignore_index=True), date_execution)
        nb_collectees = len(df)

        # 3. Anti-doublons puis chargement
        df_nouvelles = retirer_heures_existantes(client, df)
        nb_inserees = len(df_nouvelles)
        nb_doublons = nb_collectees - nb_inserees

        if nb_inserees > 0:
            lignes = json.loads(df_nouvelles.to_json(orient="records", date_format="iso"))
            charger(client, lignes, TABLE_METEO, SCHEMA_METEO)

        statut = "SUCCES" if not parcs_en_erreur else "PARTIEL"
        print(f"Collectées : {nb_collectees} | Doublons ignorés : {nb_doublons} | Insérées : {nb_inserees}")
        ecrire_log(client, date_execution, statut, nb_collectees, nb_doublons, nb_inserees, parcs_en_erreur)

    except Exception as erreur:
        ecrire_log(client, date_execution, "ECHEC", message=str(erreur))
        raise


if __name__ == "__main__":
    main()