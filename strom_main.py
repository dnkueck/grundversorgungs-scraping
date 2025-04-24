import time
import re
import os
import sys
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
from datetime import datetime


# Argumente für Batching
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end = int(sys.argv[2]) if len(sys.argv) > 2 else start + 90

# Dynamischer Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_PATH = f"strom/strompreise_{timestamp}.csv"

load_dotenv()
CSV_PATH = "strom/grundversorger.csv"



# CSV laden
df = pd.read_csv(CSV_PATH, comment="#")
df["Grundversorgungsseite"] = (
    df["Grundversorgungsseite"]
    .astype(str)
    .str.replace(r"[✅❌]", "", regex=True)
    .str.strip()
)
anbieter_liste = df.iloc[start:end].to_dict(orient="records")

# Browser vorbereiten
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# Ergebnisse hier sammeln
ergebnisse = []

for anbieter in anbieter_liste:
    name = anbieter["Name"]
    urls = [anbieter.get("Grundversorgungsseite", ""), anbieter.get("Grundversorgungsseite2", "")]
    urls = [u for u in urls if pd.notna(u) and u.strip() != ""]

    if not urls:
        print(f"{name}: ❌ Keine gültige URL – übersprungen.")
        continue
        

    print(f"\n🔍 Bearbeite: {name}")
    preise_gefunden = False


    for url in urls:
        try:
            driver.get(url)
            try:
                html_element = driver.find_element(By.TAG_NAME, "main")
            except:
                html_element = driver.find_element(By.TAG_NAME, "body")

            html_text = html_element.get_attribute("innerText")[:400000]

            # Spezieller SWK-Parser
            if "swk.de" in url:
                prices = scrape_swk_preise(html_text, anbieter_name=name)
                if prices:
                    alle_unbekannt = all(p["Wert"] == "Unbekannt" for p in prices)
                    if not alle_unbekannt:
                        ergebnisse.extend(prices)
                        preise_gefunden = True
                        print(f"💡 SWK-Parser erfolgreich für {name}")
                        break
                    else:
                        print(f"⚠️ SWK-Parser lieferte nur 'Unbekannt' – versuche nächste URL")

            # GPT-Analyse des HTML
            if not preise_gefunden:
                html_gpt_preise = extract_prices_from_html_groq(html_text, name, typ="strom")
                if html_gpt_preise:
                    ergebnisse.extend(html_gpt_preise)
                    preise_gefunden = True
                    print(f"🧠 GPT-Auswertung des HTML erfolgreich für {name}")
                    time.sleep(10)
                    break

            # PDF-Fallback
            if not preise_gefunden:
                pdf_preise = find_and_process_pdf(driver, name, url, typ="strom")
                if pdf_preise:
                    ergebnisse.extend(pdf_preise)
                    preise_gefunden = True
                    print(f"📄 PDF-Auswertung erfolgreich für {name}")
                    time.sleep(10)
                    break

            # Klassisches HTML
            if not preise_gefunden:
                html_preise = extract_prices_from_html(driver, name)
                if html_preise:
                    ergebnisse.extend(html_preise)
                    preise_gefunden = True
                    print(f"✅ Klassisches HTML erfolgreich für {name}")
                    break

            # Tarifrechner-Fallback
            if not preise_gefunden:
                tarif_preise = extract_prices_from_tarifrechner(driver, name)
                if tarif_preise:
                    ergebnisse.extend(tarif_preise)
                    preise_gefunden = True
                    print(f"⚙️ Tarifrechner-Scraping erfolgreich für {name}")
                    break
                

        except Exception as e:
            print(f"❌ Fehler bei {name}: {e}")
    
    if not preise_gefunden:
        print(f"❌ Keine Preise gefunden für {name} bei beiden URLs")        

    

# Browser schließen
driver.quit()

# Ergebnisse speichern
df_out = pd.DataFrame(ergebnisse)

# Einheitliche Reihenfolge
gewünschte_reihenfolge = ["Anbieter", "Typ", "Wert", "Zeitraum"]
for spalte in gewünschte_reihenfolge:
    if spalte not in df_out.columns:
        df_out[spalte] = "Unbekannt"

df_out = df_out[gewünschte_reihenfolge]
df_out.to_csv(OUTPUT_PATH, index=False)
print(f"\n📁 Export abgeschlossen: {OUTPUT_PATH}")