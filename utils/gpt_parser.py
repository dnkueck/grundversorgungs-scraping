import os
import requests
import json

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def extract_prices_from_pdf_content_groq(pdf_text, anbieter_name, typ="strom"):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"🧾 Anfrage an Groq für {anbieter_name} mit Text ({len(pdf_text)} Zeichen)")

    if typ == "gas":
        system_prompt = (
            "Du extrahierst **Gaspreise** aus PDF-Texten deutscher Energieversorger. "
            "Extrahiere **ausschließlich Preise für Gas** – ignoriere alle Strompreise oder Stromtarife. "
            "Gib **genau einen Arbeitspreis (ct/kWh)** und **genau einen passenden Grundpreis (€/Jahr)** zurück – **immer als Bruttowert**. "
            "Falls mehrere Preisstufen, Verbrauchsgrenzen oder Zeiträume angegeben sind, wähle **die Haupttarif-Variante für Haushaltskunden**. "
            "Wenn nur Monatswerte vorkommen (z. B. 12,00 €/Monat), rechne auf Jahr hoch (×12). "
            "Ignoriere Nettoangaben, Grundversorgung, Ersatzversorgung, Sonderverträge, Boni, Messentgelte oder Zusatzkosten. "
            "Beziehe dich nicht auf Strom, Stromklassik, meinBestStrom oder ähnliche Begriffe. "
            "Antworte **nur** im JSON-Format wie:\n"
            "[{\"Typ\": \"Arbeitspreis\", \"Wert\": \"8,12 ct/kWh\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}, "
            "{\"Typ\": \"Grundpreis\", \"Wert\": \"144,00 €/Jahr\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}]"
        )
    else:
        system_prompt = (
            "Du extrahierst **Strompreise** aus PDF-Texten deutscher Energieversorger. "
            "Extrahiere **ausschließlich Preise für Strom – keine Gaspreise**. "
            "Gib **genau einen Arbeitspreis (ct/kWh)** und **genau einen passenden Grundpreis (€/Jahr)** zurück – **immer als Bruttowert**. "
            "Wähle den **Haupttarif für Haushaltskunden** (keine Grundversorgung, Sondertarife, Ersatzversorgung, Eintarife, Boni, Nachtstrom, Wärmestrom etc.). "
            "Wenn nur Monatswerte vorkommen (z. B. 12,00 €/Monat), rechne auf Jahr hoch (×12). "
            "Ignoriere Nettoangaben, Messentgelte, Boni, Rabatte, Stromsteuer oder weitere Nebenkosten. "
            "Antworte **nur** im JSON-Format wie:\n"
            "[{\"Typ\": \"Arbeitspreis\", \"Wert\": \"29,95 ct/kWh\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}, "
            "{\"Typ\": \"Grundpreis\", \"Wert\": \"143,88 €/Jahr\", \"Zeitraum\": \"Unbekannt\", \"kWh-Bereich\": \"Unbekannt\"}]"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"PDF-Text von {anbieter_name}:\n{pdf_text}"}
    ]

    json_data = {
        "model": "gemma2-9b-it",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 2048
    }

    try:
        response = requests.post(url, headers=headers, json=json_data, timeout=45)
        print("🔁 Statuscode:", response.status_code)
        print("🔁 Antwortinhalt (gekürzt):", response.text[:400])
        response.raise_for_status()

        result = response.json()
        output_text = result["choices"][0]["message"]["content"].strip()

        json_start = output_text.find('[')
        json_end = output_text.rfind(']') + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("Keine gültige JSON-Liste in der Antwort gefunden.")

        json_string = output_text[json_start:json_end]
        parsed = json.loads(json_string)

        for eintrag in parsed:
            eintrag["Anbieter"] = anbieter_name

        return parsed

    except Exception as e:
        print(f"❌ Fehler bei Groq-Anfrage: {e}")
        return []
