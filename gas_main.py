import os
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from utils.html_extractor import extract_prices_from_html
from utils.html_extractor import scrape_swk_preise
from utils.pdf_handler import find_and_process_pdf
from utils.html_gpt_analyzer import extract_prices_from_html_groq
from utils.tarifrechner_scraper import extract_prices_from_tarifrechner
from dotenv import load_dotenv

load_dotenv()
CSV_PATH = "gas/gasversorger.csv"
OUTPUT_PATH = "gas/gaspreise.csv"  


# CSV laden
df = pd.read_csv(CSV_PATH, comment="#")
df["Grundversorgungsseite"] = (
    df["Grundversorgungsseite"]
    .astype(str)
    .str.replace(r"[✅❌]", "", regex=True)
    .str.strip()
)
anbieter_liste = df.to_dict(orient="records")

# Selenium vorbereiten
options = webdriver.ChromeOptions()
options.add_argument("--headless") 
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# Ergebnisse hier sammeln
ergebnisse = []

for anbieter in anbieter_liste:
    name = anbieter["Name"]
    url = anbieter["Grundversorgungsseite"]

    if not url or pd.isna(url):
        print(f"{name}: ❌ Keine URL – übersprungen.")
        continue

    print(f"\n🔍 Bearbeite: {name}")
    preise_gefunden = False

    try:
        driver.get(url)
   

        try:
            html_element = driver.find_element(By.TAG_NAME, "main")
        except:
            html_element = driver.find_element(By.TAG_NAME, "body")

        html_text = html_element.get_attribute("innerText")[:40000]

        if "swk.de" in url:
            prices = scrape_swk_preise(html_text, anbieter_name=name)
            if prices:
                ergebnisse.extend(prices)
                preise_gefunden = True
                print(f"💡 SWK-Parser erfolgreich für {name}")

        # 🧠 GPT-HTML-Fallback
        if not preise_gefunden:
            

            html_gpt_preise = extract_prices_from_html_groq(html_text, name, typ="gas")  # ✅ GAS
            if html_gpt_preise:
                ergebnisse.extend(html_gpt_preise)
                preise_gefunden = True
                print(f"🧠 GPT-Auswertung des HTML erfolgreich für {name}")

            

        # 📄 PDF-Fallback
        if not preise_gefunden:
            pdf_preise = find_and_process_pdf(driver, name, url, typ="gas")  # ✅ GAS
            if pdf_preise:
                ergebnisse.extend(pdf_preise)
                preise_gefunden = True
                print(f"📄 PDF-Auswertung erfolgreich für {name}")
            else:
                print(f"⚠️ PDF ohne Ergebnis für {name}")

        # 🔎 Klassisches HTML
        if not preise_gefunden:
            html_preise = extract_prices_from_html(driver, name)
            if html_preise:
                ergebnisse.extend(html_preise)
                preise_gefunden = True
                print(f"✅ Klassisches HTML erfolgreich für {name}")
            else:
                print(f"❌ Keine Preise gefunden für {name}")

        # ⚙️ Tarifrechner-Spezialfälle
        if not preise_gefunden:
            tarif_preise = extract_prices_from_tarifrechner(driver, name)
            if tarif_preise:
                ergebnisse.extend(tarif_preise)
                preise_gefunden = True
                print(f"⚙️ Tarifrechner-Scraping erfolgreich für {name}")

    except Exception as e:
        print(f"❌ Fehler bei {name}: {e}")

   

driver.quit()

# Ergebnisse speichern
df_out = pd.DataFrame(ergebnisse)

# Einheitliche Reihenfolge festlegen
gewünschte_reihenfolge = ["Anbieter", "Typ", "Wert", "Zeitraum", "kWh-Bereich"]

# Fehlende Spalten auffüllen
for spalte in gewünschte_reihenfolge:
    if spalte not in df_out.columns:
        df_out[spalte] = "Unbekannt"

# Spaltenreihenfolge anwenden
df_out = df_out[gewünschte_reihenfolge]

# Speichern
df_out.to_csv(OUTPUT_PATH, index=False)
print(f"\n📁 Export abgeschlossen: {OUTPUT_PATH}")