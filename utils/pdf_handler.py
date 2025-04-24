import os
import re
import requests
import pdfplumber
from urllib.parse import urljoin
from utils.gpt_parser import extract_prices_from_pdf_content_groq
from selenium.webdriver.common.by import By

def find_and_process_pdf(driver, anbieter_name, base_url, typ="strom"):
    pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
    pdf_candidates = []

    for link in pdf_links:
        href = link.get_attribute("href")
        linktext = link.text.strip().lower()

        if not href:
            continue

        # ❌ Ausschlüsse
        if typ == "strom":
            ausschluss = r"(agb|bedingungen|stromgvv|vertrag|widerruf|kennzeichnung|ersatzversorgung|datenschutz|gas|wärme)"
        else:  # gas
            ausschluss = r"(agb|bedingungen|gasgvv|vertrag|widerruf|kennzeichnung|ersatzversorgung|datenschutz|strom|wärme)"

        if re.search(ausschluss, href, re.IGNORECASE) or re.search(ausschluss, linktext, re.IGNORECASE):
            continue

        # ✅ Favorisierte Formulierungen
        if typ == "strom":
            favoriten = [
                "preisblatt grundversorgung strom",
                "allgemeine preise strom",
                "grundversorgung strom"
            ]
        else:
            favoriten = [
                "preisblatt grundversorgung gas",
                "allgemeine preise gas",
                "grundversorgung gas"
            ]

        if any(fav in linktext for fav in favoriten):
            pdf_candidates = [(href, linktext)]
            break

        # Als Fallback trotzdem aufnehmen
        if "preisblatt" in linktext or "grundversorgung" in linktext:
            pdf_candidates.append((href, linktext))

    if not pdf_candidates:
        print("⚠️ Kein passender PDF-Link gefunden.")
        return []

    # Lade die erste gültige PDF-Datei
    for href, linktext in pdf_candidates:
        test_url = urljoin(base_url, href)
        try:
            r = requests.get(test_url, timeout=10)
            if r.headers.get("Content-Type", "").lower().startswith("application/pdf") and r.content.startswith(b"%PDF"):
                print(f"📄 Lade PDF von: {test_url}")
                os.makedirs("downloads", exist_ok=True)
                temp_pdf = os.path.join("downloads", f"temp_{anbieter_name.replace(' ', '_')}_{typ}.pdf")
                with open(temp_pdf, "wb") as f:
                    f.write(r.content)

                #  Text aus PDF extrahieren
                with pdfplumber.open(temp_pdf) as pdf:
                    pdf_text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)

                print(f"🧾 Anfrage an Groq für {anbieter_name} mit Text ({len(pdf_text)} Zeichen)")
                return extract_prices_from_pdf_content_groq(pdf_text, anbieter_name)

        except Exception as e:
            print(f"❌ Fehler beim Laden von {test_url}: {e}")

    return []
