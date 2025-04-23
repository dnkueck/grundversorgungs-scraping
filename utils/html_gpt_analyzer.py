import os
import requests
import json
import time

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def build_system_prompt(typ="strom"):
    if typ.lower() == "gas":
        return (
            "Du erhältst Textinhalt (aus HTML oder PDF) von einer Website eines deutschen **GAS-Versorgers**. "
            "Extrahiere ausschließlich einen **Gas-Arbeitspreis (ct/kWh)** und einen **Gas-Grundpreis (€/Jahr)** – **immer als Bruttowert**. "
            "Achte genau darauf, dass es sich NICHT um Strompreise handelt – **ignoriere alle Informationen zu Strom, Wärmestrom, E-Mobilität etc.** "
            "Falls mehrere Tarife vorkommen, wähle den **Gas-Grundversorgungstarif für Haushaltskunden**. "
            "Ignoriere Sondertarife, Ersatzversorgung, Boni, Messkosten, Nettoangaben und Leistungspreise in €/kW. "
            "Wenn der Grundpreis nur in €/Monat angegeben ist, rechne ihn auf Jahr hoch (×12). "
            "Wenn kein geeigneter Preis gefunden werden kann, gib eine leere Liste zurück: `[]`. "
            "Antwort ausschließlich im JSON-Format, z. B.:\n"
            "[{\"Typ\": \"Arbeitspreis\", \"Wert\": \"8,45 ct/kWh\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}, "
            "{\"Typ\": \"Grundpreis\", \"Wert\": \"144,00 €/Jahr\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}]"
        )
    else:
        return (
            "Du erhältst Textinhalt (aus HTML extrahiert) von einer Website eines deutschen **Stromanbieters**. "
            "Extrahiere **exakt einen Arbeitspreis (ct/kWh)** und **einen Grundpreis (€/Jahr)** – immer als **Bruttowert**. "
            "Falls mehrere Tarife vorkommen, wähle den **Tarif der Strom-Grundversorgung für Haushaltskunden**. "
            "Ignoriere Wärmepumpen-, Wärmestrom-, Naturstrom-, Sonder- oder Mobilitätstarife. "
            "Beachte: Grundpreis kann auch als **'Leistungspreis'** oder **'monatlicher Grundpreis'** bezeichnet sein – rechne Monatswerte auf Jahreswerte hoch (×12). "
            "Bruttopreise stehen oft neben Nettopreisen – **verwende nur Bruttowerte**. "
            "Gib **ausschließlich** den Preis im folgenden JSON-Format zurück. Wenn kein Preis gefunden wird, gib eine leere Liste `[]` zurück.\n"
            "[{\"Typ\": \"Arbeitspreis\", \"Wert\": \"32,45 ct/kWh\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}, "
            "{\"Typ\": \"Grundpreis\", \"Wert\": \"144,00 €/Jahr\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}]"
        )

def extract_prices_from_html_groq(html_text, anbieter_name, typ="strom", max_retries=3):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"🧾 Anfrage an Groq für {anbieter_name} mit HTML-Ausschnitt:\n{html_text[:400]}...\n")

    system_prompt = build_system_prompt(typ)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"HTML-Inhalt von {anbieter_name} (Typ: {typ}):\n{html_text}"}
    ]

    json_data = {
        "model": "gemma2-9b-it",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 2048
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=json_data, timeout=30)
            response.raise_for_status()
            result = response.json()
            output = result["choices"][0]["message"]["content"]

            parsed = json.loads(output)
            for eintrag in parsed:
                eintrag["Anbieter"] = anbieter_name
            return parsed

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            print(f"⚠️ Groq HTTP-Fehler ({status}) bei {anbieter_name} (Versuch {attempt})")

            if status == 429:
                wait = 10 + attempt * 5
                print(f"⏳ Rate Limit erreicht – warte {wait}s...")
                time.sleep(wait)
            elif status == 413:
                print("📦 HTML zu groß für Groq – Anfrage abgebrochen.")
                return []
            else:
                break

        except Exception as e:
            print(f"❌ Fehler bei Groq-HTML-Anfrage: {e}")
            break

    return []
