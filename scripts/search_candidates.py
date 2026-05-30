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
#
# The real API key is stored in the local .env file and should NOT be committed to GitHub.
# Example .env content:
# GOOGLE_PLACES_API_KEY=your_real_google_api_key_here
load_dotenv(ENV_PATH)
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


"""
Define search configurations used to find potential DEXA and blood test providers
in selected DACH cities.

Instead of a simple list of query strings, each search entry contains:
- query: the actual search text sent to Google Places API
- regionCode: country focus for Google Places API
- country: country code used later for documentation and filtering
- city: selected city used later for documentation and filtering

Selected prototype regions:
- Hannover, Germany
- Wien, Austria
- Zürich, Switzerland

This approach demonstrates that the data collection process is extendable
to the full DACH region while still focusing on data quality.
"""
SEARCH_CONFIG = [
    # Deutschland: Hannover
    {
        "query": "DEXA Body Composition Hannover",
        "regionCode": "DE",
        "country": "DE",
        "city": "Hannover"
    },
    {
        "query": "DEXA Körperzusammensetzung Hannover",
        "regionCode": "DE",
        "country": "DE",
        "city": "Hannover"
    },
    {
        "query": "DEXA Scan Hannover",
        "regionCode": "DE",
        "country": "DE",
        "city": "Hannover"
    },
    {
        "query": "Blutlabor Selbstzahler Hannover",
        "regionCode": "DE",
        "country": "DE",
        "city": "Hannover"
    },
    {
        "query": "Blutuntersuchung Selbstzahler Hannover",
        "regionCode": "DE",
        "country": "DE",
        "city": "Hannover"
    },
    {
        "query": "Labor Blutabnahme ohne Überweisung Hannover",
        "regionCode": "DE",
        "country": "DE",
        "city": "Hannover"
    },

    # Österreich: Wien
    {
        "query": "DEXA Body Composition Wien",
        "regionCode": "AT",
        "country": "AT",
        "city": "Wien"
    },
    {
        "query": "DEXA Körperzusammensetzung Wien",
        "regionCode": "AT",
        "country": "AT",
        "city": "Wien"
    },
    {
        "query": "DEXA Scan Wien",
        "regionCode": "AT",
        "country": "AT",
        "city": "Wien"
    },
    {
        "query": "Blutlabor Selbstzahler Wien",
        "regionCode": "AT",
        "country": "AT",
        "city": "Wien"
    },
    {
        "query": "Blutuntersuchung Selbstzahler Wien",
        "regionCode": "AT",
        "country": "AT",
        "city": "Wien"
    },
    {
        "query": "Labor Blutabnahme ohne Überweisung Wien",
        "regionCode": "AT",
        "country": "AT",
        "city": "Wien"
    },

    # Schweiz: Zürich
    {
        "query": "DEXA Body Composition Zürich",
        "regionCode": "CH",
        "country": "CH",
        "city": "Zürich"
    },
    {
        "query": "DEXA Körperzusammensetzung Zürich",
        "regionCode": "CH",
        "country": "CH",
        "city": "Zürich"
    },
    {
        "query": "DEXA Scan Zürich",
        "regionCode": "CH",
        "country": "CH",
        "city": "Zürich"
    },
    {
        "query": "Blutlabor Selbstzahler Zürich",
        "regionCode": "CH",
        "country": "CH",
        "city": "Zürich"
    },
    {
        "query": "Blutuntersuchung Selbstzahler Zürich",
        "regionCode": "CH",
        "country": "CH",
        "city": "Zürich"
    },
    {
        "query": "Labor Blutabnahme ohne Überweisung Zürich",
        "regionCode": "CH",
        "country": "CH",
        "city": "Zürich"
    },
]


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

    Returns:
        list[dict]: A list of dictionaries. Each dictionary represents one provider candidate
                    and contains name, address, coordinates, contact information,
                    search metadata and verification status.

    Process:
        1. Define the Google Places API endpoint.
        2. Extract query, regionCode, city and country from the search configuration.
        3. Build the request headers with:
            - Content-Type: JSON request format
            - Google API key
            - Field mask defining which fields should be returned
        4. Build the request body with the search query, language and region.
        5. Send a POST request to the Google Places API.
        6. Convert the JSON response into Python data structures.
        7. Extract all returned places and transform them into a custom provider format.
    """
    url = "https://places.googleapis.com/v1/places:searchText"

    query = search_item["query"]
    region_code = search_item["regionCode"]
    country = search_item["country"]
    city = search_item["city"]

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
        2. Iterate over all configured DACH search queries.
        3. Collect all candidate results from the Google Places API.
        4. Remove duplicate provider candidates.
        5. Save the generated candidates to Daten/candidates.json.

    Important:
        The generated candidates are NOT final verified providers.
        They must be manually checked before being copied to src/data/providers.json.
    """
    if not API_KEY:
        raise ValueError(
            "GOOGLE_PLACES_API_KEY fehlt. Bitte prüfe, ob die .env Datei im Hauptordner liegt."
        )

    all_results = []

    for search_item in SEARCH_CONFIG:
        print(
            f"Suche: {search_item['query']} "
            f"({search_item['city']}, {search_item['country']})"
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