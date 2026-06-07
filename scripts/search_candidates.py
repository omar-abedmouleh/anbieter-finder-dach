import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv

# Define project paths:
# - Project root folder
# - Location of the .env file containing the API key
# - Output path for the generated candidates JSON file
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
OUTPUT_PATH = PROJECT_ROOT / "Daten" / "candidates.json"


# Load environment variables from the .env file
# and read the Google Places API key.
# The real API key is stored in the local .env file and should notbe committed to GitHub.
# GOOGLE_PLACES_API_KEY=your_real_google_api_key_here
load_dotenv(ENV_PATH)
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


"""
Define search configurations used to find potential DEXA and blood test providers
in selected DACH regions.

Instead of writing every search query manually, this script  uses:
- city lists
- query templates
- an automatic build_search_config() function

This makes the search approach more scalable and easier to extend.

Search strategy:
- Germany:
  Search broadly across many large and medically relevant cities.

- Austria:
  focused on Wien.

- Switzerland:
focused on Zürich.
The generated results are only CANDIDATES.
They are not automatically verified providers.
After this script creates Daten/candidates.json, each candidate must still be checked:
- DEXA must really be Body Composition, not only Knochendichte/Osteoporose.
- Blood labs must really allow self-payer/private blood tests without referral.
"""



# Cities used for the automated search
# Germany is searched broadly across many important cities.
# You can add or remove cities here without changing the rest of the code.
GERMANY_CITIES = [
    "Berlin",
    "Hamburg",
    "München",
    "Köln",
    "Frankfurt am Main",
    "Stuttgart",
    "Düsseldorf",
    "Dortmund",
    "Essen",
    "Leipzig",
    "Bremen",
    "Dresden",
    "Hannover",
    "Nürnberg",
    "Duisburg",
    "Bochum",
    "Wuppertal",
    "Bielefeld",
    "Bonn",
    "Münster",
    "Karlsruhe",
    "Mannheim",
    "Augsburg",
    "Wiesbaden",
    "Gelsenkirchen",
    "Mönchengladbach",
    "Braunschweig",
    "Chemnitz",
    "Kiel",
    "Aachen",
    "Halle",
    "Magdeburg",
    "Freiburg",
    "Krefeld",
    "Mainz",
    "Lübeck",
    "Erfurt",
    "Rostock",
    "Kassel",
    "Göttingen",
    "Minden",
]


# Austria.
AUSTRIA_CITIES = [
    "Wien",
]


# Switzerland.
SWITZERLAND_CITIES = [
    "Zürich",
]



# Query templates for DEXA Body Composition

# Goal:
# Find providers that do NOT only offer bone density measurement,
# but specifically offer DEXA/DXA Body Composition:
# - full-body scan / Ganzkörpermessung
# - body fat / Körperfett / Fettmasse
# - muscle mass / Muskelmasse / Lean Mass / Magermasse
# - bone density / Knochendichte / Knochenmasse
#
# The placeholder {city} is replaced automatically for every city.
DEXA_QUERY_TEMPLATES = [
    "DEXA Body Composition {city} Körperfett Muskelmasse Knochendichte Ganzkörper DXA",
    "DXA Ganzkörper Körperzusammensetzung {city} Fettmasse Muskelmasse Knochen",
    "DEXA Körperzusammensetzung {city} Körperfett Muskelmasse",
    "DEXA Body Scan {city} Body Composition",
    "DXA Body Composition Scan {city}",
]

# Query templates for blood labs / self-payer blood tests
# Goal:
# Find labs where private customers can get blood tests:
# - blood draw / Blutabnahme
# - lab analysis / Laboranalyse
# - self-payer / Selbstzahler / Privatabrechnung
# - without referral / ohne Überweisung / ohne ärztlichen Auftrag
#
# The placeholder {city} is replaced automatically for every city.
BLOOD_QUERY_TEMPLATES = [
    "Blutlabor Selbstzahler {city}",
    "Blutuntersuchung Selbstzahler {city}",
    "Labor Blutabnahme ohne Überweisung {city}",
    "Direktlabor {city} Selbstzahler Blutabnahme",
    "Bluttest ohne ärztliche Überweisung {city}",
]


def build_search_config():
    """
    Build search configurations for the Google Places API.

    Why this function:
        This function automatically creates all search items from:
        - city lists
        - DEXA query templates
        - blood lab query templates

    Returns:
        list[dict]: A list of search configuration dictionaries.

    Each dictionary contains:
        - query (str): The search text sent to Google Places API
        - regionCode (str): Country focus for the API request: DE, AT, CH
        - country (str): Country code stored in the result
        - city (str): City used for the search
        - targetCategory (str): Intended category: DEXA or Blutlabor

    """
    config = []

    
    # Germany:
    # For every German city:
    # 1. Generate several DEXA Body Composition search queries.
    # 2. Generate several blood lab self-payer search queries.
    for city in GERMANY_CITIES:
        for query_template in DEXA_QUERY_TEMPLATES:
            config.append(
                {
                    "query": query_template.format(city=city),
                    "regionCode": "DE",
                    "country": "DE",
                    "city": city,
                    "targetCategory": "DEXA",
                }
            )

        for query_template in BLOOD_QUERY_TEMPLATES:
            config.append(
                {
                    "query": query_template.format(city=city),
                    "regionCode": "DE",
                    "country": "DE",
                    "city": city,
                    "targetCategory": "Blutlabor",
                }
            )

    
    # Austria: 
    # Austria is focused on Wien for this prototype.
    for city in AUSTRIA_CITIES:
        for query_template in DEXA_QUERY_TEMPLATES:
            config.append(
                {
                    "query": query_template.format(city=city),
                    "regionCode": "AT",
                    "country": "AT",
                    "city": city,
                    "targetCategory": "DEXA",
                }
            )

        for query_template in BLOOD_QUERY_TEMPLATES:
            config.append(
                {
                    "query": query_template.format(city=city),
                    "regionCode": "AT",
                    "country": "AT",
                    "city": city,
                    "targetCategory": "Blutlabor",
                }
            )

    
    # Switzerland: 
    # Switzerland is focused on Zürich for this prototype.
    for city in SWITZERLAND_CITIES:
        for query_template in DEXA_QUERY_TEMPLATES:
            config.append(
                {
                    "query": query_template.format(city=city),
                    "regionCode": "CH",
                    "country": "CH",
                    "city": city,
                    "targetCategory": "DEXA",
                }
            )

        for query_template in BLOOD_QUERY_TEMPLATES:
            config.append(
                {
                    "query": query_template.format(city=city),
                    "regionCode": "CH",
                    "country": "CH",
                    "city": city,
                    "targetCategory": "Blutlabor",
                }
            )

    return config


# SEARCH_CONFIG is generated automatically.
SEARCH_CONFIG = build_search_config()


def search_places(search_item):
    """
    Send a text search request to the Google Places API and return provider candidates.

    Args:
        search_item (dict): Search configuration used to find potential providers.
                            It contains:
                            - query (str): Search query sent to Google Places API
                            - regionCode (str): Country focus for the API request: DE, AT, CH
                            - country (str): Country code stored in the result
                            - city (str): City stored in the result
                            - targetCategory (str): Intended category of the query:
                                                    DEXA or Blutlabor

    Returns:
        list[dict]: A list of dictionaries.
                    Each dictionary represents one provider candidate and contains:
                    - source query
                    - search city
                    - search country
                    - intended target category
                    - provider name
                    - address
                    - coordinates
                    - contact information
                    - verification status

    Process:
        1. Define the Google Places API endpoint.
        2. Extract query, regionCode, city, country and targetCategory
           from the search configuration.
        3. Build the request headers with:
            - Content-Type: JSON request format
            - Google API key
            - Field mask defining which fields should be returned
        4. Build the request body with the search query, language and region.
        5. Send a POST request to the Google Places API.
        6. Convert the JSON response into Python data structures.
        7. Extract all returned places and transform them into a custom provider format.

    Important:
        This function only creates candidates.
        It does not prove that a provider really fulfills the challenge criteria.
    """
    url = "https://places.googleapis.com/v1/places:searchText"

    query = search_item["query"]
    region_code = search_item["regionCode"]
    country = search_item["country"]
    city = search_item["city"]
    target_category = search_item["targetCategory"]

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.nationalPhoneNumber,"
            "places.websiteUri,"
            "places.googleMapsUri"
        ),
    }

    body = {
        "textQuery": query,
        "languageCode": "de",
        "regionCode": region_code,
    }

    response = requests.post(url, headers=headers, json=body, timeout=20)

    if response.status_code != 200:
        print("API Fehler:", response.status_code)
        print(response.text)
        return []

    data = response.json()
    places = data.get("places", [])

    results = []

    for place in places:
        results.append(
            {
                "sourceQuery": query,
                "searchCity": city,
                "searchCountry": country,
                "targetCategory": target_category,
                "name": place.get("displayName", {}).get("text", ""),
                "address": place.get("formattedAddress", ""),
                "coordinates": {
                    "lat": place.get("location", {}).get("latitude"),
                    "lng": place.get("location", {}).get("longitude"),
                },
                "contact": {
                    "phone": place.get("nationalPhoneNumber", ""),
                    "website": place.get("websiteUri", ""),
                    "googleMaps": place.get("googleMapsUri", ""),
                },
                "verificationStatus": "candidate",
            }
        )

    return results


def remove_duplicates(items):
    """
    Remove duplicate provider candidates from a list.

    Args:
        items (list[dict]): List of provider candidates.

    Returns:
        list[dict]: List of provider candidates without duplicates.

    The function uses a temporary dictionary to identify duplicates.
    Each provider is stored with a generated key based on its name and address.
    Since dictionary keys must be unique, duplicate providers with the same
    name and address are overwritten and therefore only kept once.

    Important:
        If the same provider is found by different queries, this function keeps
        only one version of that provider.

        Because we search many cities and many query templates, duplicates
        are expected and normal.
    """
    unique = {}

    for item in items:
        key = f"{item.get('name', '')}-{item.get('address', '')}"
        unique[key] = item

    return list(unique.values())


def main():
    """
    Main execution flow for the data collection script.

    Process:
        1. Check whether the Google Places API key is available.
        2. Build/use all configured DACH search queries.
        3. Iterate over all search queries.
        4. Collect all candidate results from the Google Places API.
        5. Remove duplicate provider candidates.
        6. Save the generated candidates to Daten/candidates.json.


    Data quality rule:
        For DEXA:
            Only accept providers that clearly offer DEXA/DXA Body Composition,
            meaning full-body scan with body fat, muscle mass and bone density.

        For blood labs:
            Only accept providers where self-payer/private blood testing without
            referral or without doctor's order is clearly supported.
    """
    if not API_KEY:
        raise ValueError(
            "GOOGLE_PLACES_API_KEY fehlt. Bitte prüfe, ob die .env Datei im Hauptordner liegt."
        )

    all_results = []

    print(f"Anzahl Suchanfragen: {len(SEARCH_CONFIG)}")

    for search_item in SEARCH_CONFIG:
        print(
            f"Suche: {search_item['query']} "
            f"({search_item['city']}, {search_item['country']}, {search_item['targetCategory']})"
        )
        results = search_places(search_item)
        all_results.extend(results)

    unique_results = remove_duplicates(all_results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(unique_results, file, indent=2, ensure_ascii=False)

    print(f"{len(unique_results)} Kandidaten gespeichert in:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()