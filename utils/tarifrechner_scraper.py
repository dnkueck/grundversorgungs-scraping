from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def extract_prices_from_tarifrechner(driver, anbieter):
    if anbieter == "E.ON":
        return scrape_eon(driver)
    if anbieter == "SWB Bremen":
        return scrape_swb_bremen(driver)
    return []

def parse_prices_from_text(preis_text, anbieter_name):
    arbeitspreis_match = re.search(r"(\d{1,2},\d{2})\s*Cent\s*/\s*kWh", preis_text)
    grundpreis_match = re.search(r"(\d{1,2},\d{2})\s*EUR\s*/\s*Monat", preis_text)

    arbeitspreis = f"{arbeitspreis_match.group(1)} ct/kWh" if arbeitspreis_match else None
    grundpreis_raw = grundpreis_match.group(1) if grundpreis_match else None

    grundpreis = f"{grundpreis_raw} €/Monat" if grundpreis_raw else None

    einträge = []
    if arbeitspreis:
        einträge.append({
            "Typ": "Arbeitspreis", "Wert": arbeitspreis, "Zeitraum": "Unbekannt",
            "kWh-Bereich": "Unbekannt", "Anbieter": anbieter_name
        })
    if grundpreis:
        grundwert = float(grundpreis_raw.replace(",", "."))
        grundpreis_jahr = f"{grundwert * 12:.2f} €/Jahr"
        einträge.append({
            "Typ": "Grundpreis", "Wert": grundpreis_jahr, "Zeitraum": "Unbekannt",
            "kWh-Bereich": "Unbekannt", "Anbieter": anbieter_name
        })
    return einträge

def scrape_swb_bremen(driver):
    url = "https://www.swb.de/strom/strom-basis"
    wait = WebDriverWait(driver, 15)

    def accept_cookies_if_present():
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Alle Cookies zulassen')]"))
            )
            cookie_button.click()
            print("🍪 Cookie-Banner akzeptiert.")
            time.sleep(1)
        except:
            print("ℹ Kein Cookie-Banner sichtbar.")

    try:
        print("🌐 Öffne Seite...")
        driver.get(url)
        accept_cookies_if_present()
        time.sleep(2)

        print("🔎 Suche PLZ-Feld...")
        plz_input = wait.until(EC.presence_of_element_located((By.ID, "zipcode")))
        plz_input.clear()
        plz_input.send_keys("28195")

        print("🔎 Suche Verbrauchsfeld...")
        consumption_input = wait.until(EC.presence_of_element_located((By.ID, "consumption")))
        consumption_input.clear()
        consumption_input.send_keys("2400")

        print("🔎 Suche Button...")
        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "calc-button")))
        driver.execute_script("arguments[0].click();", submit_button)

        print("⏳ Warte auf Ergebnisanzeige...")
        time.sleep(5)

        try:
            preisbereich = driver.find_element(By.CLASS_NAME, "tariff-calculator__result-box")
            preis_text = preisbereich.text.strip()
        except:
            print("⚠ Ergebnisbox nicht gefunden – versuche Fallback mit <main> oder <body>")
            try:
                preis_text = driver.find_element(By.TAG_NAME, "main").text.strip()
            except:
                preis_text = driver.find_element(By.TAG_NAME, "body").text.strip()

        print(f"📦 Vollständiger Preistext:\n{preis_text[:1000]}")

        return parse_prices_from_text(preis_text, "SWB Bremen")

    except Exception as e:
        print("❌ Ausnahme beim Tarifrechner:", e)
        driver.save_screenshot("swb_error_debug.png")
        with open("swb_debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return []
    

def scrape_eon(driver):
   


    url = "https://www.eon.de/de/pk/produkte/strom/grundversorgung.html"
    wait = WebDriverWait(driver, 20)

    print("🌐 Öffne E.ON-Website...")
    driver.get(url)
    time.sleep(3)  # Warte auf vollständiges Laden der Seite

    # Cookie-Banner erkennen und akzeptieren
    try:
        akzeptieren_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(), 'Akzeptieren')]")
        ))
        time.sleep(1)
        akzeptieren_button.click()
        print(" Cookie-Einwilligung akzeptiert.")
        time.sleep(2)
    except Exception as e:
        print("ℹ Kein Cookie-Dialog gefunden oder klickbar:", e)

    # PLZ + Verbrauch via JS setzen (Shadow DOM umgehen)
    js_script = """
        const zipInput = document.querySelector('eon-ui-input[name="zipInput"]');
        const kwhInput = document.querySelector('input[type="number"]');
        if (zipInput && zipInput.shadowRoot) {
            const zip = zipInput.shadowRoot.querySelector('input');
            zip.value = '14542 Werder';
            zip.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (kwhInput) {
            kwhInput.value = '2500';
            kwhInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    """
    driver.execute_script(js_script)
    print("🧾 PLZ & Verbrauch gesetzt")
    time.sleep(2)  # Zeit geben, um Felder zu übernehmen

    # Button klicken
    try:
        submit_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space(text())='Tarif finden']")
        ))
        time.sleep(1)
        submit_button.click()
        print("📤 Button geklickt")
    except Exception as e:
        print("❌ Kein Button gefunden:", e)
        return []

    time.sleep(6)  # Warten auf Ergebnisanzeige

    # Preise extrahieren
    body_text = driver.find_element(By.TAG_NAME, "body").text
    print("📦 Seiteninhalt (Ausschnitt):\n", body_text[:800])

    arbeitspreis_match = re.search(r"(\d{2},\d{2})\s*Cent\s*/\s*kWh", body_text)
    grundpreis_match = re.search(r"(\d{1,2},\d{2})\s*EUR\s*/\s*Monat", body_text)

    arbeitspreis = arbeitspreis_match.group(1) + " ct/kWh" if arbeitspreis_match else None
    grundpreis = grundpreis_match.group(1) + " €/Monat" if grundpreis_match else None

    print("✅ Arbeitspreis:", arbeitspreis)
    print("✅ Grundpreis:", grundpreis)

    einträge = []
    if arbeitspreis:
        einträge.append({
            "Typ": "Arbeitspreis", "Wert": arbeitspreis,
            "Zeitraum": "Unbekannt", "kWh-Bereich": "Unbekannt", "Anbieter": "E.ON"
        })
    if grundpreis:
        grundwert = float(grundpreis.replace(" €/Monat", "").replace(",", "."))
        einträge.append({
            "Typ": "Grundpreis", "Wert": f"{grundwert * 12:.2f} €/Jahr",
            "Zeitraum": "Unbekannt", "kWh-Bereich": "Unbekannt", "Anbieter": "E.ON"
        })


    return einträge