import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup


def scrape_swk_preise(html_text, anbieter_name):
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator="\n")
    text_flat = text.replace("\n", " ")  # komplette Zeile zusammenhängend prüfen

    arbeitspreis = grundpreis = datenstand = "Unbekannt"

    # Robustere Muster für eng zusammengesetzte Infos
    ap_match = re.search(r"arbeitspreis\s*[:\-]?\s*([\d.,]+)\s*ct/?kwh", text_flat, re.IGNORECASE)
    gp_match = re.search(r"(grundpreis|leistungspreis)\s*[:\-]?\s*([\d.,]+)\s*€", text_flat, re.IGNORECASE)
    ds_match = re.search(r"(stand|datenstand|gültig ab)[^\d]*(\d{2}\.\d{2}\.\d{4})", text_flat, re.IGNORECASE)

    if ap_match:
        arbeitspreis = ap_match.group(1) + " ct/kWh"
    if gp_match:
        grundpreis = gp_match.group(2) + " €/Jahr"
    if ds_match:
        datenstand = ds_match.group(2)

    print(f"🔎 [SWK] Gefundene Werte:")
    print(f"   Arbeitspreis: {arbeitspreis}")
    print(f"   Grundpreis:   {grundpreis}")
    print(f"   Datenstand:   {datenstand}")

    return [
        {
            "Anbieter": anbieter_name,
            "Typ": "Arbeitspreis",
            "Wert": arbeitspreis,
            "Zeitraum": datenstand,
        },
        {
            "Anbieter": anbieter_name,
            "Typ": "Grundpreis",
            "Wert": grundpreis,
            "Zeitraum": datenstand,
        }
    ]

def extract_prices_from_html(driver, anbieter_name):
    ergebnisse = []
    last_kwh_range = "Unbekannt"
    last_zeitraum = []

    

    try:
        domain = driver.current_url.split("//")[-1].split("/")[0]

        if "stadtwerke-norden.de" in domain:
            print("🧠 Spezialfall Stadtwerke Norden – HTML-Kartenstruktur wird analysiert")

            try:
                karten = driver.find_elements(By.CLASS_NAME, "uk-card-body")

                for karte in karten:
                    text = karte.text.lower()
                    if "grundversorgung" not in text:
                        continue  # Nur "Nörder strom basis"

                    zeilen = karte.find_elements(By.TAG_NAME, "p")
                    current_typ = None

                    for z in zeilen:
                        raw = z.get_attribute("innerText").strip()

                        if "arbeitspreis" in raw.lower():
                            current_typ = "Arbeitspreis"
                            continue
                        if "grundpreis" in raw.lower():
                            current_typ = "Grundpreis"
                            continue

                        if current_typ and "brutto" in raw.lower():
                            match = re.search(r"(\d+,\d+)", raw)
                            if match:
                                wert = match.group(1).replace(",", ".")
                                einheit = "ct/kWh" if current_typ == "Arbeitspreis" else "€/Monat"
                                ergebnisse.append({
                                    "Anbieter": anbieter_name,
                                    "Typ": current_typ,
                                    "Wert": f"{wert} {einheit}",
                                    "Zeitraum": "ab 01.01.2025",
                                    "kWh-Bereich": "Unbekannt"
                                })

            except Exception as e:
                print(f"⚠️ Fehler beim Auslesen der Norden-Karte: {e}")

            return ergebnisse  # Frühzeitiges return – keine weitere Verarbeitung nötig
        

        if "stadtwerke-nordhorn.de" in domain:
            print("🧠 Spezialfall Nordhorn – HTML-Divs werden analysiert")

            try:
                content = driver.find_element(By.ID, "section-3-35")  # Abschnitt mit den Preisen

                arbeitspreis_divs = content.find_elements(By.XPATH, ".//div[contains(text(), 'Arbeitspreis')]")
                grundpreis_divs = content.find_elements(By.XPATH, ".//div[contains(text(), 'Grundpreis')]")

                def finde_bruttopreis(start_divs):
                    for div in start_divs:
                        try:
                            # Suche nächsten Div-Nachbarn mit Euro-Zeichen oder "Cent"
                            siblings = div.find_elements(By.XPATH, "following::div[contains(@class, 'ct-div-block')]")
                            for s in siblings:
                                txt = s.text.strip()
                                if "€" in txt or "cent" in txt.lower():
                                    return txt
                        except:
                            continue
                    return None

                ap = finde_bruttopreis(arbeitspreis_divs)
                gp = finde_bruttopreis(grundpreis_divs)

                if ap:
                    ergebnisse.append({
                        "Anbieter": anbieter_name,
                        "Typ": "Arbeitspreis",
                        "Wert": ap,
                        "Zeitraum": "Gültig ab 01.05.2024",
                    })

                if gp:
                    ergebnisse.append({
                        "Anbieter": anbieter_name,
                        "Typ": "Grundpreis",
                        "Wert": gp,
                        "Zeitraum": "Gültig ab 01.05.2024",
                    })

            except Exception as e:
                print(f"⚠️ Fehler bei Nordhorn-Parsing: {e}")


        soup = BeautifulSoup(driver.page_source, "html.parser")

        if "bielefeld" in anbieter_name.lower():
            print("🟡 Spezialfall Bielefeld – extrahiere direkt aus .tariffDetail")
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                price_box = soup.select_one("div.stageCt2__tariffDetailContainer")

                gp_raw = price_box.find("div", class_="stageCt2__tariffDetail__basePrice")
                gp_value = gp_raw.find("span").get_text(strip=True).replace(",", ".") + " €/Jahr"

                ap_raw = price_box.find("div", class_="stageCt2__tariffDetail__laborPrice")
                ap_value = ap_raw.find("span").get_text(strip=True).replace(",", ".") + " ct/kWh"

                return [
                    {
                        "Anbieter": anbieter_name,
                        "Typ": "Grundpreis",
                        "Wert": gp_value,
                        "Zeitraum": "Unbekannt",
                    },
                    {
                        "Anbieter": anbieter_name,
                        "Typ": "Arbeitspreis",
                        "Wert": ap_value,
                        "Zeitraum": "Unbekannt",
                    }
                ]
            except Exception as e:
                print(f"❌ Fehler im Bielefeld-Parser: {e}")
                return []

  
        if "ewe.de" in domain:
            print("🧠 EWE erkannt – nutze Strom-only Tabellenfilter")

            bereiche = driver.find_elements(By.CLASS_NAME, "toggler__info-wrapper")
            strom_tabellen = []

            for bereich in bereiche:
                try:
                    titel_element = bereich.find_element(By.CLASS_NAME, "toggler__info-section-title")
                    titel = titel_element.text.lower()

                    if not any(w in titel for w in ["stromversorgung", "grundversorgung strom", "preise für die grundversorgung strom"]):
                        print(f"⛔ Abschnitt übersprungen wegen Titel: {titel}")
                        continue

                    tabellen = bereich.find_elements(By.TAG_NAME, "table")
                    print(f"✅ {len(tabellen)} Strom-Tabellen gefunden in Abschnitt: {titel}")
                    strom_tabellen.extend(tabellen)

                except Exception as e:
                    print(f"⚠️ Fehler beim Analysieren eines Bereichs: {e}")
                    continue

            tabellen = strom_tabellen

        else:
            print("🌍 Kein EWE – verwende allgemeine Tabellenlogik mit Gas-Filter")

            alle_tabellen = driver.find_elements(By.TAG_NAME, "table")
            tabellen = []

            for tabelle in alle_tabellen:
                try:
                    umgebungstext = ""
                    eltern = tabelle.find_elements(By.XPATH, "./preceding::strong[1]") \
                            or tabelle.find_elements(By.XPATH, "./preceding::h2[1]") \
                            or tabelle.find_elements(By.XPATH, "./preceding::div[1]")

                    if eltern:
                        umgebungstext = eltern[0].text.strip().lower()
                    else:
                        umgebungstext = tabelle.text.lower()

                    if any(w in umgebungstext for w in ["wärmestrom", "heizung", "speicherheizung", "wärmepumpe", "strom comfort"]):
                        print(f"⛔ Tabelle übersprungen: {umgebungstext}")
                        continue

                except Exception as e:
                    print(f"⚠️ Fehler beim Auslesen der Umgebung: {e}")
                    continue

                tabellen.append(tabelle)

            if not tabellen:
                raise Exception("❌ Keine gültigen Tabellen gefunden")

            
        last_kwh_range = "Unbekannt"
        last_zeitraum = []

       

        for tabelle in tabellen:
            

            rows = tabelle.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                

                cols = row.find_elements(By.TAG_NAME, "td") or row.find_elements(By.TAG_NAME, "th")
                data = []
                for col in cols:
                    text = col.text.strip()
                    if not text:
                        # Versuche, innerHTML auszulesen, um eingebettete Inhalte wie <strong><br> zu bekommen
                        try:
                            html = col.get_attribute("innerHTML")
                            text = re.sub(r"<[^>]+>", " ", html)  # Entferne HTML-Tags
                            text = re.sub(r"\s+", " ", text).strip()
                        except:
                            continue
                    if text:
                        data.append(text)
                if not data:
                    continue

                
                # Heuristik: Zeile muss brutto oder Preisangaben enthalten
                if not any(re.search(r"(brutto|ct/kwh|€/jahr|€/monat|cent|euro)", x.lower()) for x in data):
                    continue


                if any("arbeitspreis" in x.lower() for x in data) and any(re.search(r"\d+,\d+", x) for x in data):
                    for preis in data:
                        if re.search(r"\d+,\d+", preis):
                            ergebnisse.append({
                                "Anbieter": anbieter_name,
                                "Typ": "Arbeitspreis",
                                "Wert": preis + " ct/kWh",
                                "Zeitraum": "ab 01.01.2025",
                            })

                if any("grundpreis" in x.lower() for x in data) and any(re.search(r"\d+,\d+", x) for x in data):
                    for preis in data:
                        if re.search(r"\d+,\d+", preis):
                            ergebnisse.append({
                                "Anbieter": anbieter_name,
                                "Typ": "Grundpreis",
                                "Wert": preis + " €/Monat",
                                "Zeitraum": "ab 01.01.2025",
                            })

                 # 🆕 Lingen-Spezialfall: Wenn genau zwei Werte (Arbeitspreis, Grundpreis)
                if len(data) == 2 and re.search(r"arbeitspreis", row.text.lower()) and re.search(r"grundpreis", row.text.lower()):
                    try:
                        ap_value = data[0].replace(",", ".")
                        gp_value = data[1].replace(",", ".")
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Arbeitspreis",
                            "Wert": f"{data[0]} ct/kWh",
                            "Zeitraum": "Unbekannt",
                        })
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Grundpreis",
                            "Wert": f"{data[1]} €/Jahr",
                            "Zeitraum": "Unbekannt",
                        })
                    except:
                        pass
                    continue

                # ⏳ Zeitraum merken (z. B. „Gültig ab ...“)
                if len(data) == 1 and any(k in data[0].lower() for k in ["gültig", "ab", "bis", "stand"]):
                    last_zeitraum = [data[0]]
                    continue

                elif any(any(c.isdigit() for c in x) and any(w in x.lower() for w in ["ab", "bis", "gültig", "."]) for x in data[1:]):
                    last_zeitraum = data[1:]
                    continue

                elif any("kwh" in x.lower() and any(w in x.lower() for w in ["bis", "ab", "-"]) for x in data):
                    for x in data:
                        if "kwh" in x.lower():
                            last_kwh_range = x
                            break
                    continue
                

                # ✅ NEU: Stadtwerke Lingen & ähnliche – Werte direkt in Zeile
                if any("arbeitspreis" in d.lower() for d in data) and len(data) >= 2:
                    for preis in data[1:]:
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Arbeitspreis",
                            "Wert": preis + " ct/kWh",
                            "Zeitraum": "Unbekannt",
                        })
                    continue

                if any("grundpreis" in d.lower() for d in data) and len(data) >= 2:
                    for preis in data[1:]:
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Grundpreis",
                            "Wert": preis + " €/Jahr",
                            "Zeitraum": "Unbekannt",
                        })
                    continue

                # 🧠 Spezialfall für komplexe Tabellen mit Preiszeilen (Springe etc.)
                if len(data) == 6 and re.search(r"\d", data[0]) and "," in data[1]:
                    try:
                        kwh_bereich = data[0]
                        arbeitspreis = data[2]
                        grundpreis = data[4]

                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Arbeitspreis",
                            "Wert": f"{arbeitspreis} ct/kWh",
                            "Zeitraum": "Unbekannt",
                        })
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Grundpreis",
                            "Wert": f"{grundpreis} €/Monat",
                            "Zeitraum": "Unbekannt",
                        })
                    except Exception as e:
                        print(f"⚠️ Fehler beim Extrahieren aus Springe-Tabelle: {e}")
                    continue

                


                # 🔁 Standard-Erkennung mit Kontext
                elif any(x.lower().startswith("arbeitspreis") or x.lower().startswith("verbrauchspreis") for x in data):
                    for j, preis in enumerate(data[1:]):
                        zeitraum = last_zeitraum[j] if j < len(last_zeitraum) else (last_zeitraum[0] if last_zeitraum else "Unbekannt")
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Arbeitspreis",
                            "Wert": preis,
                            "Zeitraum": zeitraum,
                        })

                elif any("grundpreis" in x.lower() for x in data):
                    for j, preis in enumerate(data[1:]):
                        zeitraum = last_zeitraum[j] if j < len(last_zeitraum) else (last_zeitraum[0] if last_zeitraum else "Unbekannt")
                        ergebnisse.append({
                            "Anbieter": anbieter_name,
                            "Typ": "Grundpreis",
                            "Wert": preis,
                            "Zeitraum": zeitraum,
                        })



    except Exception as e:
        print(f"❌ HTML-Fallback gescheitert: {e}")

        # Falls Tabellen fehlen, prüfen wir strukturierte <div>-Elemente
    try:
        print("🔁 Suche strukturierte div-Preisblöcke...")

        zeitraum_text = "Unbekannt"
        try:
            zeitraum_div = driver.find_element(By.XPATH, "//h2[contains(text(), 'Gültig ab')]")
            zeitraum_text = zeitraum_div.text.strip()
        except NoSuchElementException:
            pass

        all_divs = driver.find_elements(By.CLASS_NAME, "ct-text-block")
        current_typ = None
        last_kwh_range = "Unbekannt"

        for div in all_divs:
            text = div.text.strip()
            if not text:
                continue

            if "arbeitspreis" in text.lower():
                current_typ = "Arbeitspreis"
                continue
            elif "grundpreis" in text.lower():
                current_typ = "Grundpreis"
                continue

            if current_typ and re.search(r"\d{1,3},\d{2}", text):
                einheit = "ct/kWh" if current_typ == "Arbeitspreis" else "€/Jahr"
                ergebnisse.append({
                    "Anbieter": anbieter_name,
                    "Typ": current_typ,
                    "Wert": text + " " + einheit,
                    "Zeitraum": zeitraum_text,
                    "kWh-Bereich": last_kwh_range
                })

    except Exception as e:
        print(f"❌ Div-Fallback gescheitert: {e}")

        # 🔍 Weitere Fallback-Strategie für eingebettete Preise wie bei Stadtwerke Bielefeld
    try:
        print("🔁 Prüfung auf eingebettete Preisangaben mit <span>-Struktur...")

        # Alle divs mit bekannten Klassen, die auf Preisarten deuten
        preis_divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'basePrice') or contains(@class, 'laborPrice')]")

        for div in preis_divs:
            text = div.text.lower()
            span = div.find_element(By.TAG_NAME, "span")
            value = span.text.strip()

            if "grundpreis" in text:
                ergebnisse.append({
                    "Anbieter": anbieter_name,
                    "Typ": "Grundpreis",
                    "Wert": value,
                    "Zeitraum": "Unbekannt",
                })

            elif "arbeitspreis" in text or "verbrauchspreis" in text:
                ergebnisse.append({
                    "Anbieter": anbieter_name,
                    "Typ": "Arbeitspreis",
                    "Wert": value,
                    "Zeitraum": "Unbekannt",
                })

    except Exception as e:
        print(f"❌ Bielefeld-Fallback gescheitert: {e}")


    return ergebnisse
