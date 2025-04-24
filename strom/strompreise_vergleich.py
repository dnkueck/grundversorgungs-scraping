import pandas as pd
import re
import plotly.graph_objects as go
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
    df = df[df["Wert"].str.contains(r"\d", na=False)]
    df["Preis"] = df["Wert"].apply(parse_preiswert)

    # Monatswerte zu Jahreswerten umrechnen
    def adjust(row):
        if row["Typ"] == "Grundpreis" and row["Preis"] < 20:
            return row["Preis"] * 12
        return row["Preis"]

    df["Preis"] = df.apply(adjust, axis=1)
    return df.dropna(subset=["Preis"])

# Daten laden
df = load_and_prepare("strom/strompreise.csv")

# URLs laden
urls_df = pd.read_csv("strom/grundversorger.csv", sep=",")
urls_df["Grundversorgungsseite"] = urls_df["Grundversorgungsseite"].apply(clean_url)
url_map = dict(zip(urls_df["Name"].str.strip(), urls_df["Grundversorgungsseite"]))

# Gruppieren nach Typ
def prepare_grouped(df, typ):
    gruppe = df[df["Typ"] == typ]
    gruppiert = gruppe.groupby("Anbieter")["Preis"].mean().dropna()
    return gruppiert.to_dict()

preise_ap = prepare_grouped(df, "Arbeitspreis")
preise_gp = prepare_grouped(df, "Grundpreis")

anbieter = sorted(set(preise_ap.keys()) & set(preise_gp.keys()))
urls = [url_map.get(name, "") for name in anbieter]

# Preislisten aufbauen
werte_ap_plot = [preise_ap.get(name, None) for name in anbieter]
werte_gp_plot = [preise_gp.get(name, None) for name in anbieter]

farben_ap = ["yellow" if name == "EWE" else "cornflowerblue" for name in anbieter]
farben_gp = ["yellow" if name == "EWE" else "darkorange" for name in anbieter]

# Plot erstellen
fig = go.Figure()

fig.add_trace(go.Bar(
    x=anbieter,
    y=werte_ap_plot,
    name="Arbeitspreis (ct/kWh)",
    marker_color=farben_ap,
    offsetgroup=0,
    customdata=urls,
    hovertemplate="<b>%{x}</b><br>%{y:.2f} ct/kWh<br><a href='%{customdata}'>Zur Website</a><extra></extra>"
))

fig.add_trace(go.Bar(
    x=anbieter,
    y=werte_gp_plot,
    name="Grundpreis (€/Jahr)",
    marker_color=farben_gp,
    offsetgroup=1,
    customdata=urls,
    hovertemplate="<b>%{x}</b><br>%{y:.2f} €/Jahr<br><a href='%{customdata}'>Zur Website</a><extra></extra>"
))

# Layout
fig.update_layout(
    title="Strompreise Grundversorgung – Arbeitspreis & Grundpreis je Anbieter",
    barmode="group",
    height=900,
    width=4000,
    xaxis_tickangle=-45,
    showlegend=True,
    margin=dict(b=200),
)

# Datei schreiben
html_file = "strom_preise_vergleich.html"
fig.write_html(html_file, include_plotlyjs='cdn', full_html=True)

# JS-Interaktion einfügen
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
