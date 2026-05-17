#!/usr/bin/env python3
import requests
import sys
from datetime import datetime

# ── KONFIGURATION ──────────────────────────────────────────────
NTFY_TOPIC = "VZbayern123"   # <- hier deinen Kanal eintragen!

BOOKING_URL = (
    "https://www.terminland.de/verbraucherzentrale/default.aspx"
    "?m=14148&ll=MKpQ3&dpp=MKpQ3&step=1&dlg=5"
    "&a271391665=271391668&a271497983=293385721"
    "&a272595181=272595244&a2776432946=2776433792"
    "&a288597890=288597929&a288868389=288868548&css=1&ldlg=6"
)

TERMINLAND_BASE = "https://www.terminland.de/verbraucherzentrale"

PARAMS = {
    "m":           "14148",
    "ll":          "MKpQ3",
    "dpp":         "MKpQ3",
    "step":        "2",
    "ldlg":        "6",
    "a271391665":  "271391668",
    "a271497983":  "293385721",
    "a272595181":  "272595244",
    "a2776432946": "2776433792",
    "a288597890":  "288597929",
    "a288868389":  "288868548",
    "css":         "1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json, text/html, */*",
    "Referer":    "https://www.terminland.de/verbraucherzentrale/",
    "X-Requested-With": "XMLHttpRequest",
}

API_ENDPOINTS = [
    f"{TERMINLAND_BASE}/api/availabledates",
    f"{TERMINLAND_BASE}/api/appointments/available",
    f"{TERMINLAND_BASE}/api/free",
    f"{TERMINLAND_BASE}/api/slots",
]

# ── FUNKTIONEN ─────────────────────────────────────────────────

def check_via_api():
    for endpoint in API_ENDPOINTS:
        try:
            r = requests.get(endpoint, params=PARAMS, headers=HEADERS, timeout=15)
            print(f"  API {endpoint}: HTTP {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"  Antwort: {str(data)[:200]}")
                if isinstance(data, list):
                    return len(data) > 0, f"{len(data)} Eintraege"
                if isinstance(data, dict):
                    for key in ("dates", "slots", "appointments", "items", "data"):
                        if key in data:
                            return len(data[key]) > 0, f"{len(data[key])} Eintraege"
        except Exception as e:
            print(f"  Fehler: {e}")
    return None, "keine API erreichbar"


def check_via_html():
    try:
        r = requests.get(
            f"{TERMINLAND_BASE}/default.aspx",
            params=PARAMS,
            headers={**HEADERS, "Accept": "text/html"},
            timeout=20,
        )
        html = r.text.lower()
        print(f"  HTML Laenge: {len(html)} Zeichen")

        negative = [
            "keine freien termine", "kein termin verfuegbar",
            "leider keine termine", "keine termine verfuegbar",
            "no appointments available",
        ]
        positive = [
            "freier termin", "termin waehlen", "datum waehlen",
            "fc-day-grid-event", "data-date=", "buchbar",
        ]

        for sig in negative:
            if sig in html:
                return False, f"Kein-Termin-Meldung: '{sig}'"
        for sig in positive:
            if sig in html:
                return True, f"Signal: '{sig}'"

        return False, "Kein eindeutiges Signal (JS-Seite)"
    except Exception as e:
        return False, f"HTML-Fehler: {e}"


def send_ntfy(topic, message, url):
    try:
        r = requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title":    "Termin verfuegbar! Verbraucherzentrale Bayern",
                "Priority": "urgent",
                "Tags":     "calendar,white_check_mark",
                "Click":    url,
                "Content-Type": "text/plain; charset=utf-8",
            },
            timeout=10,
        )
        if r.status_code == 200:
            print("ntfy.sh: Benachrichtigung gesendet!")
        else:
            print(f"ntfy.sh Fehler: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"ntfy.sh Fehler: {e}")


# ── MAIN ───────────────────────────────────────────────────────

def main():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    print(f"[{now}] Pruefe Terminverfuegbarkeit...")

    available, reason = check_via_api()

    if available is None:
        print("Fallback auf HTML...")
        available, reason = check_via_html()

    print(f"Ergebnis: {'TERMINE VERFUEGBAR' if available else 'Keine Termine'} ({reason})")

    if available:
        send_ntfy(
            NTFY_TOPIC,
            f"Freie Termine bei der Verbraucherzentrale Bayern!\nJetzt buchen: {BOOKING_URL}",
            BOOKING_URL,
        )
    else:
        print("Keine Benachrichtigung gesendet.")


if __name__ == "__main__":
    main()
