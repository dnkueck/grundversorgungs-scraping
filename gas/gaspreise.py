import pandas as pd
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser

# Hilfsfunktionen
def parse_preiswert(wert):
    match = re.search(r"(\d+[.,]\d+)", str(wert))
    if match:
        return float(match.group(1).replace(",", "."))
    return None

def clean_url(url):
    return re.sub(r"[^\x00-\x7F]+", "", str(url)).strip()

def load_and_prepare(file):
    df = pd.read_csv(file)
    df["Wert_num"] = df["Wert"].apply(parse_preiswert)
    df = df[df['Wert'].str.contains(r"\d", na=False)]
    df["Preis"] = df["Wert"].apply(parse_preiswert)

    # Monatswerte zu Jahreswerten umrechnen
    def adjust(row):
        if row["Typ"] == "Grundpreis" and row["Preis"] < 20:
            return row["Preis"] * 12
        return row["Preis"]
    
    df["Preis"] = df.apply(adjust, axis=1)
    return df.dropna(subset=["Preis"])

# Daten laden
strom_df = load_and_prepare("gas/gaspreise.csv")

# URLs laden
urls_df = pd.read_csv("gas/gasversorger.csv", sep=",")
urls_df["Grundversorgungsseite"] = urls_df["Grundversorgungsseite"].apply(clean_url)
url_map = dict(zip(urls_df["Name"].str.strip(), urls_df["Grundversorgungsseite"]))

# Gruppieren und sortieren
def prepare_grouped(df, typ):
    gruppe = df[df["Typ"] == typ]
    gruppiert = gruppe.groupby("Anbieter")["Preis"].mean().dropna()
    sortiert = gruppiert.sort_values()
    urls = [url_map.get(name, "") for name in sortiert.index]
    return sortiert.index.tolist(), sortiert.values.tolist(), urls

anbieter_ap, werte_ap, urls_ap = prepare_grouped(strom_df, "Arbeitspreis")
anbieter_gp, werte_gp, urls_gp = prepare_grouped(strom_df, "Grundpreis")

# Farben vorbereiten (EWE in rot hervorheben)
farben_ap = ["yellow" if name == "EWE" else "cornflowerblue" for name in anbieter_ap]
farben_gp = ["yellow" if name == "EWE" else "darkorange" for name in anbieter_gp]

# Subplots erstellen
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=["Gas: Arbeitspreis (ct/kWh)", "Gas: Grundpreis (€/Jahr)"]
)

fig.add_trace(go.Bar(
    x=anbieter_ap, y=werte_ap,
    customdata=urls_ap,
    name="Gas Arbeitspreis",
    marker_color=farben_ap,
    hovertemplate="<b>%{x}</b><br>%{y:.2f} ct/kWh<br><a href='%{customdata}'>Zur Website</a><extra></extra>"
), row=1, col=1)

fig.add_trace(go.Bar(
    x=anbieter_gp, y=werte_gp,
    customdata=urls_gp,
    name="Gas Grundpreis",
    marker_color=farben_gp,
    hovertemplate="<b>%{x}</b><br>%{y:.2f} €/Jahr<br><a href='%{customdata}'>Zur Website</a><extra></extra>"
), row=2, col=1)

# Layout
fig.update_layout(
    title="Gaspreise Grundversorgung – Arbeitspreis & Grundpreis (aufsteigend)",
    height=1200,
    width=4000,
    showlegend=False,
    margin=dict(b=200),
)
fig.update_xaxes(tickangle=-45, tickfont=dict(size=10), automargin=True)

# HTML-Datei schreiben
html_file = "gas_preise_visualisierung.html"
fig.write_html(html_file, include_plotlyjs='cdn', full_html=True)

# JS für Klick-Interaktion
custom_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    const plots = document.getElementsByClassName("plotly-graph-div");
    for (const plot of plots) {
        plot.on('plotly_click', function(data) {
            const url = data.points[0].customdata;
            if (url) window.open(url, '_blank');
        });
    }
});
</script>
"""

with open(html_file, "r", encoding="utf-8") as f:
    html_content = f.read()

html_content = html_content.replace("</body>", custom_js + "\n</body>")

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

# Im Browser öffnen
webbrowser.open(html_file)
