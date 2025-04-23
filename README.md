# Grundversorgung Strom – Web-Extraktion & Analyse

In diesem Projekt werden Strom- und Gastarifdaten (Arbeitspreis und Grundpreis) automatisiert von Webseiten Grundversorger extrahiert. Der Fokus liegt auf öffentlich einsehbaren HTML-Inhalten, ggf. unterstützt durch GPT-Auswertung(Groq) von PDFs und unstrukturierten Webseiten.

---

## Projektübersicht

### Hauptbestandteile:

- **`strom_main.py`**  
  Einstiegspunkt für Strom. Lädt die Versorgerliste (`strom/grundversorger.csv`) und ruft die Extraktionslogik auf. Ergebnisse werden zentral in `strom/strompreise.csv` gespeichert.

 - **`gas_main.py`**  
  Einstiegspunkt für Gas. Lädt die Versorgerliste (`gas/gasversorger.csv`) und ruft die Extraktionslogik auf. Ergebnisse werden zentral in `gas/gaspreise.csv` gespeichert. 

- **`grundversorger.csv`** oder **`gasversorger.csv`**
  CSV-Datei mit allen Zielanbietern. Enthält:
  - Anbietername
  - Domain
  - URL zur Grundversorgung (bzw. direkt zum Preisblatt)

- **`strompreise.csv`**  oder **`gaspreise.csv`** 
  Ergebnisdatei mit allen extrahierten Preisen. Jede Zeile entspricht einem Preis (Arbeitspreis oder Grundpreis) eines Versorgers.


### Intelligente Extraktionslogik
Das Hauptskript durchläuft pro Anbieter folgende Extraktionskette:

1. scrape_swk_preise – Spezialparser für swk.de-basierte Seiten

2. extract_prices_from_html_groq – GPT-Analyse des HTML-Inhalts via Groq

3. find_and_process_pdf – Extraktion aus PDF-Dateien mit GPT

4. extract_prices_from_html – Klassische HTML-RegEx-Analyse

5. extract_prices_from_tarifrechner – Sonderfall: interaktive Tarifrechner (Selenium)

Ist eine Methode erfolgreich, wird die nächste nicht mehr aufgerufen.

Falls der erste Link keinen Erfolg liefert (z. B. alle Preise sind Unbekannt), wird automatisch die Fallback-URL getestet.

---

## Verzeichnis `utils/`

Modularer Aufbau zur Aufteilung der Extraktionslogik:

| Datei                    | Zweck                                                                 |
|--------------------------|-----------------------------------------------------------------------|
| `html_extractor.py`      | Hauptmodul für HTML-Parsing mit regulären Ausdrücken & BeautifulSoup  |
| `pdf_handler.py`         | Behandelt ggf. verlinkte Preisblätter als PDF (aktuell optional)      |
| `gpt_parser.py`          | GPT-basierte Extraktion aus PDFs oder HTML (Groq API)                 |
| `html_gpt_analyzer.py`   | GPT-Auswertung direkt auf HTML-Quelltext                              |
| `tarifrechner_scraper.py`| Speziallogik für Tarifrechner per Selenium                            |

---

## Datenformat

Die Dateien `strompreise.csv` und `gaspreise.csv`  haben den folgenden Aufbau:

| Anbieter              | Typ         | Wert             | Zeitraum        | kWh-Bereich      |
|-----------------------|-------------|------------------|------------------|------------------|
| Stadtwerke Emden      | Arbeitspreis| 37,31 ct/kWh     | ab 01.01.2025   | bis 10.000       |
| Stadtwerke Emden      | Grundpreis  | 124,64 €/Jahr    | ab 01.01.2025   | bis 10.000       |
| ...                   | ...         | ...              | ...             | ...              |

---

## Visualisierung

- **`strompreise.py`** und **`gaspreise.py`**  dienen der optionalen Auswertung und Visualisierung der extrahierten Daten.
- Nutzt `pandas` und `matplotlib`, um z. B. Anbieter nach Preisen zu sortieren oder Histogramme zu erstellen.

---

## Setup & Abhängigkeiten

### Voraussetzungen

- Python 3.10+
- Benötigte Pakete:
  ```
  pip install -r requirements.txt
  ```

- `.env` Datei mit evtl. API-Zugängen (z. B. Groq für GPT-Parsing) erforderlich:
  ```
  GROQ_API_KEY=...
  ```

---

## Hinweise zur Verarbeitung


- Bei GPT-Nutzung wird ein kleiner time.sleep() eingebaut, um Limits zu umgehen.
- Es wird immer zuerst die erste URL getestet – nur bei Misserfolg wird Grundversorgungsseite2 verwendet.
- Unterstützt sowohl klassische HTML-Strukturen als auch PDF und GPT-basierte Webanalyse.
- Es werden bevorzugt **Brutto-Preise** berücksichtigt.
- Wenn auf einer Webseite mehrere Tarife enthalten sind, wird nach Möglichkeit nur der **erste relevante Tarif zur Grundversorgung** verwendet.


---

## Weiteres

- `__pycache__/`: automatisch generiert – kann ignoriert werden.

---

