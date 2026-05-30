import os
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Pfade definieren
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
INPUT_PATH = PROJECT_ROOT / "Daten" / "candidates.json"
OUTPUT_PATH = PROJECT_ROOT / "Daten" / "verified_providers.json"
STATE_PATH = PROJECT_ROOT / "Daten" / "processed_state.json"  # NEU: Speichert ALLE geprüften Namen

# .env laden
load_dotenv(ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(f"Bitte GEMINI_API_KEY in der .env Datei unter {ENV_PATH} eintragen!")

client = genai.Client(api_key=GEMINI_API_KEY)

class ProviderVerification(BaseModel):
    is_dexa_body_composition: bool = Field(
        description="NUR true, wenn die Praxis/das Studio explizit DEXA/DXA Ganzkörper-Scans für Fett/Muskelmasse anbietet. Wenn sie nur BIA, InBody, Seca oder nur Knochendichte bei Osteoporose anbieten, MUSS dies false sein."
    )
    is_bloodlab_selfpayer: bool = Field(
        description="NUR true, wenn man hier als Privatperson/Selbstzahler ohne ärztliche Überweisung direkt Blut abnehmen und testen lassen kann."
    )
    extracted_services: list[str] = Field(
        description="Liste der konkret gefundenen relevanten Leistungen."
    )
    price_info: str = Field(
        description="Gefundene Preise auf der Website. Falls nichts gefunden wurde: 'Nicht öffentlich verfügbar'."
    )
    explanation: str = Field(
        description="Präzise Begründung auf Deutsch."
    )

def clean_text(text):
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)

def scrape_website(base_url, max_subpages=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    scraped_content = []
    visited_urls = set()
    urls_to_visit = [base_url]
    keywords = ["leistung", "preis", "diagnostik", "labor", "dexa", "dxa", "tarife", "blut", "angebot", "preise", "services"]

    print(f"  -> Scrape Website: {base_url}")
    while urls_to_visit and len(visited_urls) < max_subpages:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            continue
        try:
            response = requests.get(current_url, headers=headers, timeout=8)
            if response.status_code != 200:
                continue
            visited_urls.add(current_url)
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            text = clean_text(soup.get_text())
            scraped_content.append(text)
            
            if len(visited_urls) == 1:
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = urljoin(base_url, href)
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        if any(kw in href.lower() for kw in keywords) and full_url not in visited_urls:
                            urls_to_visit.append(full_url)
        except Exception:
            pass
    return "\n\n--- SEITENWECHSEL ---\n\n".join(scraped_content)[:25000]

def verify_with_gemini(website_text, max_retries=3):
    prompt = f"""
    Analysiere den folgenden Website-Text eines Gesundheitsanbieters im DACH-Raum extrem kritisch.

    Website-Text:
    ---
    {website_text}
    ---

    Prüfe streng diese zwei Kriterien:
    1. DEXA Body Composition: Es MUSS die DEXA/DXA-Technologie für Fett/Muskelmasse genannt werden. BIA (InBody, Seca) oder reine Osteoporose-Knochendichte ist FALSE.
    2. Selbstzahler-Blutlabor: Direktlabor, Walk-in-Labor oder Arztpraxen mit expliziten Selbstzahler-Blutprofilen ohne Überweisung.
    """
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ProviderVerification,
                    temperature=0.0
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                # 65 Sekunden abkühlen bei 429
                print(f"     ⚠️ Rate-Limit (429). Kühle Verbindung für 65s ab (Versuch {attempt}/{max_retries})...")
                time.sleep(65)
            else:
                print(f"     Gemini API Fehler: {e}")
                break
    return None

def main():
    if not INPUT_PATH.exists():
        print(f"Fehler: candidates.json wurde unter {INPUT_PATH} nicht gefunden!")
        return

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    # 1. Bereits verifizierte "JA"-Anbieter laden
    verified_list = []
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                verified_list = json.load(f)
        except:
            pass

    # 2. ALLE bereits verarbeiteten Anbieter (JA & NEIN) aus State laden
    processed_names = set()
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                processed_names = set(json.load(f))
                print(f"Zustands-Speicher geladen: {len(processed_names)} Anbieter bereits analysiert.")
        except:
            pass

    print(f"Starte AI-Verifizierung für {len(candidates)} Kandidaten...\n")

    for idx, candidate in enumerate(candidates, 1):
        name = candidate["name"]
        
        # Komplett überspringen, wenn wir diesen Namen schon einmal an der API hatten (JA oder NEIN)
        if name in processed_names:
            continue
            
        website = candidate["contact"].get("website")
        print(f"[{idx}/{len(candidates)}] Prüfe: {name}")
        
        if not website:
            print("  -> Keine Website vorhanden. Überspringe.")
            processed_names.add(name)
            continue
            
        text = scrape_website(website)
        if not text:
            print("  -> Website konnte nicht gelesen werden. Überspringe.")
            processed_names.add(name)
            continue
            
        print("  -> Sende an Gemini AI...")
        analysis = verify_with_gemini(text)
        
        # Wir markieren den Anbieter JETZT als verarbeitet (egal ob Erfolg oder Fehler)
        processed_names.add(name)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(list(processed_names), f, indent=2, ensure_ascii=False)
        
        if analysis:
            is_dexa = analysis.get("is_dexa_body_composition", False)
            is_blood = analysis.get("is_bloodlab_selfpayer", False)
            explanation = analysis.get("explanation", "")
            extracted_services = analysis.get("extracted_services", [])
            price_info = analysis.get("price_info", "Nicht öffentlich verfügbar")
            
            print(f"     * DEXA Body Comp: {'✅ JA' if is_dexa else '❌ NEIN'}")
            print(f"     * Selbstzahler-Labor: {'✅ JA' if is_blood else '❌ NEIN'}")
            print(f"     * Leistungen: {extracted_services}")
            print(f"     * Preise: {price_info}")
            print(f"     * Begründung: {explanation}")
            
            if is_dexa or is_blood:
                category = "DEXA" if is_dexa else "Bloodlab"
                verified_candidate = {
                    "name": name,
                    "category": category,
                    "services": extracted_services if extracted_services else ([ "Body Composition" ] if is_dexa else [ "Blood Test (Self-Payer)" ]),
                    "address": candidate["address"],
                    "searchCity": candidate["searchCity"],
                    "searchCountry": candidate["searchCountry"],
                    "coordinates": candidate["coordinates"],
                    "contact": candidate["contact"],
                    "selfPayer": True,
                    "priceRange": price_info,
                    "ai_justification": explanation
                }
                verified_list.append(verified_candidate)
                
                # In verified_providers.json speichern
                with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(verified_list, f, indent=2, ensure_ascii=False)
        else:
            print("  -> Analyse fehlgeschlagen.")
            
        # Ruhige 20 Sekunden Pause, um Google-Sperren im Free Tier aktiv zu vermeiden!
        time.sleep(20)
        print("-" * 50)

    print(f"\nFertig! Alle verifizierten Einträge wurden unter '{OUTPUT_PATH}' gespeichert.")

if __name__ == "__main__":
    main()