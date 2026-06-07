```python
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


# Define project paths:
# - Script folder
# - Project root folder
# - Location of the .env file containing the Gemini API key
# - Input path for the raw candidates collected with search_candidates.py
# - Output path for AI-verified providers
# - State path for already processed providers
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
INPUT_PATH = PROJECT_ROOT / "Daten" / "candidates.json"
OUTPUT_PATH = PROJECT_ROOT / "Daten" / "verified_providers.json"
STATE_PATH = PROJECT_ROOT / "Daten" / "processed_state.json"


# Load environment variables from the .env file
# and read the Gemini API key.
# The real API key is stored in the local .env file and should not be committed to GitHub.
# GEMINI_API_KEY=your_real_gemini_api_key_here
load_dotenv(ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if not GEMINI_API_KEY:
    raise ValueError(f"Please add GEMINI_API_KEY to the .env file at {ENV_PATH}!")


# Create the Gemini client.
client = genai.Client(api_key=GEMINI_API_KEY)


"""
AI-based verification approach for provider candidates.

This script is an experimental second verification method.

Input:
- Daten/candidates.json
  Contains raw provider candidates collected with the Google Places API.

Goal:
- Visit each provider website.
- Extract relevant website text.
- Send the text to Gemini.
- Ask Gemini to classify whether the provider matches one of the two challenge categories:
  1. DEXA Body Composition Scan
  2. Blood test as a self-payer without medical referral

Important:
The candidates from Google Places are only potential matches.
They are not automatically correct.
This script tries to verify them by checking the provider website content.

Limitation:
The Gemini API request limit can be reached quickly.
Because of this, this approach was used as an additional prototype verification method,
not as the only final verification process.
"""


class ProviderVerification(BaseModel):
    """
    Structured response schema for Gemini.

    Gemini must answer in this format.
    This makes the verification result easier to process automatically.
    """

    is_dexa_body_composition: bool = Field(
        description=(
            "Only true if the provider explicitly offers DEXA/DXA full-body scans "
            "for body fat and muscle mass. If the provider only offers BIA, InBody, "
            "Seca, or only bone density measurement for osteoporosis, this must be false."
        )
    )

    is_bloodlab_selfpayer: bool = Field(
        description=(
            "Only true if private customers or self-payers can directly get blood tests "
            "without a medical referral or doctor's order."
        )
    )

    extracted_services: list[str] = Field(
        description="List of the relevant services found on the website."
    )

    price_info: str = Field(
        description=(
            "Price information found on the website. "
            "If no price was found, return: 'Not publicly available'."
        )
    )

    explanation: str = Field(
        description="Precise explanation of the decision."
    )


def clean_text(text):
    """
    Clean extracted website text.

    Why this function:
        Website text often contains many empty lines, duplicated spaces,
        navigation text or layout-related whitespace.

    Args:
        text (str): Raw text extracted from a website.

    Returns:
        str: Cleaned text with empty chunks removed.
    """
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def scrape_website(base_url, max_subpages=3):
    """
    Scrape the provider website and return relevant text content.

    Args:
        base_url (str): Provider website URL.
        max_subpages (int): Maximum number of pages to read from the same website.

    Returns:
        str: Cleaned website text, limited to 25,000 characters.

    Process:
        1. Open the provider website.
        2. Extract visible text content.
        3. Remove scripts, styles, header, footer and navigation.
        4. Search for relevant internal subpages.
        5. Scrape a small number of relevant subpages.
        6. Return the combined cleaned text.

    Relevant subpages are detected by keywords such as:
    - leistung
    - preis
    - diagnostik
    - labor
    - dexa
    - blut
    - services

    Important:
        This is a lightweight scraping approach.
        It is not a full crawler and only checks a few relevant subpages.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    scraped_content = []
    visited_urls = set()
    urls_to_visit = [base_url]

    keywords = [
        "leistung",
        "preis",
        "diagnostik",
        "labor",
        "dexa",
        "dxa",
        "tarife",
        "blut",
        "angebot",
        "preise",
        "services",
    ]

    print(f"  -> Scraping website: {base_url}")

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

            # Remove elements that usually do not contain relevant provider information.
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            text = clean_text(soup.get_text())
            scraped_content.append(text)

            # Only search for additional internal links on the first visited page.
            if len(visited_urls) == 1:
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = urljoin(base_url, href)

                    # Only follow links from the same domain.
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        if (
                            any(keyword in href.lower() for keyword in keywords)
                            and full_url not in visited_urls
                        ):
                            urls_to_visit.append(full_url)

        except Exception:
            # If one website cannot be read, the script continues with the next candidate.
            pass

    return "\n\n--- PAGE BREAK ---\n\n".join(scraped_content)[:25000]


def verify_with_gemini(website_text, max_retries=3):
    """
    Send extracted website text to Gemini and request a structured verification result.

    Args:
        website_text (str): Cleaned website text from the provider website.
        max_retries (int): Number of retry attempts in case of API errors.

    Returns:
        dict | None: Structured Gemini result as a dictionary, or None if verification fails.

    Gemini checks two strict criteria:
        1. DEXA Body Composition:
           The website must clearly mention DEXA/DXA technology for body composition,
           body fat or muscle mass. Pure osteoporosis bone density measurement is not enough.

        2. Self-payer blood lab:
           The website must clearly indicate that private customers/self-payers can get
           blood tests without a medical referral or doctor's order.

    The response is requested as JSON using the ProviderVerification schema.
    """
    prompt = f"""
    Analyze the following website text of a health provider in the DACH region very critically.

    Website text:
    ---
    {website_text}
    ---

    Strictly check these two criteria:
    1. DEXA Body Composition:
       The provider must explicitly mention DEXA/DXA technology for body fat and/or muscle mass.
       BIA, InBody, Seca or pure osteoporosis bone density measurement is false.

    2. Self-payer blood lab:
       The provider must be a direct lab, walk-in lab or medical provider with explicit
       self-payer blood test options without a medical referral.
    """

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ProviderVerification,
                    temperature=0.0,
                ),
            )

            return json.loads(response.text)

        except Exception as e:
            error_msg = str(e)

            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                # Wait after a rate-limit error before retrying.
                print(
                    f"     ⚠️ Rate limit reached. "
                    f"Waiting 65 seconds before retrying "
                    f"(attempt {attempt}/{max_retries})..."
                )
                time.sleep(65)
            else:
                print(f"     Gemini API error: {e}")
                break

    return None


def main():
    """
    Main execution flow for the AI verification script.

    Process:
        1. Check whether Daten/candidates.json exists.
        2. Load all raw provider candidates.
        3. Load already verified providers if the output file already exists.
        4. Load already processed provider names from the state file.
        5. Iterate over all candidates.
        6. Skip candidates that were already processed.
        7. Scrape the provider website.
        8. Send the extracted text to Gemini.
        9. Save matching providers to Daten/verified_providers.json.
        10. Save processed provider names to Daten/processed_state.json.

    Important:
        The state file stores all processed provider names, not only accepted providers.
        This prevents repeated API calls after restarting the script.

    Data quality rule:
        For DEXA:
            Only accept providers that clearly offer DEXA/DXA Body Composition.

        For blood labs:
            Only accept providers where self-payer/private blood testing without
            referral or doctor's order is clearly supported.
    """
    if not INPUT_PATH.exists():
        print(f"Error: candidates.json was not found at {INPUT_PATH}!")
        return

    with open(INPUT_PATH, "r", encoding="utf-8") as file:
        candidates = json.load(file)

    # Load already verified providers if the output file exists.
    verified_list = []

    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as file:
                verified_list = json.load(file)
        except Exception:
            pass

    # Load all already processed providers from the state file.
    # This includes accepted and rejected providers.
    processed_names = set()

    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as file:
                processed_names = set(json.load(file))
                print(
                    f"State file loaded: "
                    f"{len(processed_names)} providers already analyzed."
                )
        except Exception:
            pass

    print(f"Starting AI verification for {len(candidates)} candidates...\n")

    for idx, candidate in enumerate(candidates, 1):
        name = candidate["name"]

        # Skip this provider if it was already sent to the API before.
        if name in processed_names:
            continue

        website = candidate["contact"].get("website")

        print(f"[{idx}/{len(candidates)}] Checking: {name}")

        if not website:
            print("  -> No website available. Skipping.")
            processed_names.add(name)
            continue

        text = scrape_website(website)

        if not text:
            print("  -> Website could not be read. Skipping.")
            processed_names.add(name)
            continue

        print("  -> Sending website text to Gemini...")
        analysis = verify_with_gemini(text)

        # Mark the provider as processed, independent of the result.
        processed_names.add(name)

        with open(STATE_PATH, "w", encoding="utf-8") as file:
            json.dump(list(processed_names), file, indent=2, ensure_ascii=False)

        if analysis:
            is_dexa = analysis.get("is_dexa_body_composition", False)
            is_blood = analysis.get("is_bloodlab_selfpayer", False)
            explanation = analysis.get("explanation", "")
            extracted_services = analysis.get("extracted_services", [])
            price_info = analysis.get("price_info", "Not publicly available")

            print(f"     * DEXA Body Composition: {'YES' if is_dexa else 'NO'}")
            print(f"     * Self-payer blood lab: {'YES' if is_blood else 'NO'}")
            print(f"     * Services: {extracted_services}")
            print(f"     * Prices: {price_info}")
            print(f"     * Explanation: {explanation}")

            if is_dexa or is_blood:
                category = "DEXA" if is_dexa else "Bloodlab"

                verified_candidate_ai = {
                    "name": name,
                    "category": category,
                    "services": extracted_services
                    if extracted_services
                    else (
                        ["Body Composition"]
                        if is_dexa
                        else ["Blood Test (Self-Payer)"]
                    ),
                    "address": candidate["address"],
                    "searchCity": candidate["searchCity"],
                    "searchCountry": candidate["searchCountry"],
                    "coordinates": candidate["coordinates"],
                    "contact": candidate["contact"],
                    "selfPayer": True,
                    "priceRange": price_info,
                    "ai_justification": explanation,
                }

                verified_list.append(verified_candidate_ai)

                # Save the accepted provider to verified_providers.json.
                with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
                    json.dump(verified_list, file, indent=2, ensure_ascii=False)

        else:
            print("  -> Analysis failed.")

        # Wait between requests to reduce the risk of rate limits.
        time.sleep(20)

        print("-" * 50)

    print(f"\nDone! All verified entries were saved to '{OUTPUT_PATH}'.")


if __name__ == "__main__":
    main()
```
