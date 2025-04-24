import os
import glob
import pandas as pd

# Ordner und Suchmuster definieren
input_dir = "strom"
pattern = os.path.join(input_dir, "strompreise_*.csv")
output_file = os.path.join(input_dir, "strompreise.csv")

# Alle passenden Dateien finden
csv_files = glob.glob(pattern)
print(f"🔍 Gefundene Dateien: {len(csv_files)}")

# Daten zusammenführen
dfs = []
for file in csv_files:
    print(f"📥 Lese: {file}")
    df = pd.read_csv(file)
    dfs.append(df)

if not dfs:
    print("⚠️ Keine Dateien gefunden – Abbruch.")
    exit()

merged = pd.concat(dfs, ignore_index=True)

# Doppelte Einträge entfernen
merged = merged.drop_duplicates(subset=["Anbieter", "Typ", "Wert", "Zeitraum"])

# Einheitliche Spaltenreihenfolge sicherstellen
columns = ["Anbieter", "Typ", "Wert", "Zeitraum"]
for col in columns:
    if col not in merged.columns:
        merged[col] = "Unbekannt"

merged = merged[columns]

# Ergebnis speichern
merged.to_csv(output_file, index=False)
print(f"\n✅ Ergebnis gespeichert in: {output_file}")
