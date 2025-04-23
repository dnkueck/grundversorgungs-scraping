import pandas as pd

def filter_first_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gibt für jeden Anbieter nur den ersten Arbeitspreis und den ersten Grundpreis zurück.
    'Leistungspreis' wird dabei wie ein Grundpreis behandelt.
    """
    # Leistungspreise als Grundpreis behandeln
    df['Typ'] = df['Typ'].replace("Leistungspreis", "Grundpreis")

    gefiltert = []

    for anbieter in df['Anbieter'].unique():
        unter_df = df[df['Anbieter'] == anbieter]

        erster_ap = unter_df[unter_df['Typ'] == 'Arbeitspreis'].head(1)
        erster_gp = unter_df[unter_df['Typ'] == 'Grundpreis'].head(1)

        gefiltert.append(erster_ap)
        gefiltert.append(erster_gp)

    return pd.concat(gefiltert, ignore_index=True)

# Laden und anwenden
df = pd.read_csv("strompreise.csv")
df_gefiltert = filter_first_prices(df)
df_gefiltert.to_csv("strompreise_gefiltert.csv", index=False)
