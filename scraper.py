"""
Boericke's Homoeopathic Materia Medica Scraper
Scrapes http://homeoint.org/books/boericmm/ and produces boericke_remedies.json
"""

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import json
import time
import os
import re
from typing import Optional

BASE_URL = "http://homeoint.org/books/boericmm/"
OUTPUT_FILE = "boericke_remedies.json"
FAILED_FILE = "failed_urls.txt"
DELAY = 0.7

SECTION_KEYWORDS = [
    "Mind", "Head", "Eyes", "Ears", "Nose", "Face", "Mouth", "Throat",
    "Stomach", "Abdomen", "Stool", "Rectum", "Urine", "Urinary", "Male",
    "Female", "Respiratory", "Heart", "Back", "Extremities", "Sleep",
    "Skin", "Fever", "Modalities", "Generalities", "Dose",
    "Relationships", "Relationship"
]


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL and return BeautifulSoup. Logs failures to failed_urls.txt."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BoerickeBot/1.0)"}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"    ERROR fetching {url}: {e}")
        with open(FAILED_FILE, "a", encoding="utf-8") as f:
            f.write(url + "\n")
        return None


def fetch_letter_index(letter: str) -> Optional[BeautifulSoup]:
    """Fetch the index page for a given letter."""
    url = BASE_URL + f"{letter.lower()}.htm"
    return fetch_page(url)


def parse_remedy_links(soup: BeautifulSoup, letter: str) -> list:
    """
    Parse remedy abbreviations and URLs from a letter index page.
    Only keeps links that point to remedy subpages like a/abies-c.htm
    """
    remedies = []
    if not soup:
        return remedies

    blockquote = soup.find("blockquote")
    search_area = blockquote if blockquote else soup
    links = search_area.find_all("a", href=True)

    for link in links:
        href = link.get("href", "").strip()
        abbreviation = link.get_text(strip=True).upper()

        if not href or not abbreviation:
            continue

        # Skip single letter navigation links like "B", "C", "D"
        if len(abbreviation) <= 1:
            continue

        # Skip common navigation words
        if abbreviation.lower() in [
            "index", "next", "previous", "back", "home",
            "main", "top", "contents", "return"
        ]:
            continue

        # Must be a .htm link
        if ".htm" not in href.lower():
            continue

        # Skip letter navigation links like "b.htm", "c.htm"
        if "/" not in href and re.match(r"^[a-z]\.htm$", href.lower()):
            continue

        # Build full URL
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = "http://homeoint.org" + href
        else:
            clean_href = href.lstrip("./")
            full_url = BASE_URL + clean_href

        # URL must contain the letter subfolder e.g. /a/abies-c.htm
        letter_path = f"/{letter.lower()}/"
        if letter_path not in full_url.lower():
            continue

        remedies.append({
            "abbreviation": abbreviation,
            "url": full_url,
            "letter": letter.upper()
        })

    return remedies


def clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def is_section_heading(text: str) -> bool:
    """Check if bold text is a section heading."""
    cleaned = text.replace(".--", "").replace("--", "").strip()
    for keyword in SECTION_KEYWORDS:
        if cleaned.lower() == keyword.lower():
            return True
    if re.match(r"^[A-Z][a-z\s]+\.--$", text.strip()):
        return True
    return False


def extract_section_name(text: str) -> str:
    """Get clean section name from heading text."""
    return text.replace(".--", "").replace("--", "").strip()


def scrape_remedy_page(url: str, abbreviation: str, letter: str) -> Optional[dict]:
    """Scrape one remedy page and return structured dict."""
    soup = fetch_page(url)
    if not soup:
        return None

    full_name = ""
    common_name = None

    body = soup.find("body") or soup
    all_bold = body.find_all("b")

    for bold in all_bold:
        text = clean_text(bold.get_text())
        if not text:
            continue
        if is_section_heading(text):
            break
        if any(c.isupper() for c in text) and len(text) > 3:
            paren_match = re.search(r"\(([^)]+)\)", text)
            if paren_match:
                common_name = paren_match.group(1).strip()
                full_name = text[:text.find("(")].strip()
            else:
                parent_text = clean_text(bold.parent.get_text()) if bold.parent else ""
                paren_match2 = re.search(r"\(([^)]+)\)", parent_text)
                if paren_match2:
                    common_name = paren_match2.group(1).strip()
                full_name = text.strip()
            if full_name:
                break

    if not full_name:
        title = soup.find("title")
        if title:
            full_name = clean_text(title.get_text())

    # Flat traversal — fixes NavigableString bug
    sections = {}
    general_parts = []
    relationships = None
    current_section = None
    current_content = []
    in_general = True

    all_elements = list(body.descendants)

    for element in all_elements:
        if isinstance(element, Tag):
            if element.name == "b":
                bold_text = clean_text(element.get_text())
                if is_section_heading(bold_text):
                    if current_section is not None:
                        content = clean_text(" ".join(current_content))
                        if current_section.lower() in ["relationships", "relationship"]:
                            relationships = content if content else None
                        else:
                            if content:
                                sections[current_section] = content
                    elif in_general and current_content:
                        general_parts.extend(current_content)

                    current_section = extract_section_name(bold_text)
                    current_content = []
                    in_general = False

        elif isinstance(element, NavigableString):
            parent = element.parent
            if parent and parent.name in ["script", "style", "head"]:
                continue
            text = clean_text(str(element))
            if text and len(text) > 1:
                if text.lower() not in ["index", "next", "previous", "back"]:
                    current_content.append(text)

    # Save last section
    if current_section is not None:
        content = clean_text(" ".join(current_content))
        if current_section.lower() in ["relationships", "relationship"]:
            relationships = content if content else None
        else:
            if content:
                sections[current_section] = content
    elif in_general and current_content:
        general_parts.extend(current_content)

    general = clean_text(" ".join(general_parts))

    if full_name and general.startswith(full_name):
        general = general[len(full_name):].strip()
    if common_name and general.startswith(common_name):
        general = general[len(common_name):].strip()

    for key in list(sections.keys()):
        if key.lower() in ["relationships", "relationship"]:
            relationships = sections.pop(key)
            break

    return {
        "abbreviation": abbreviation,
        "full_name": full_name,
        "common_name": common_name if common_name else None,
        "source_url": url,
        "letter": letter,
        "general": general,
        "sections": sections,
        "relationships": relationships
    }


def load_existing_data() -> tuple:
    """Load existing JSON for resumability."""
    if not os.path.exists(OUTPUT_FILE):
        return [], set()
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        scraped_urls = {item["source_url"] for item in data}
        print(f"Resuming: {len(data)} remedies already scraped.")
        return data, scraped_urls
    except Exception as e:
        print(f"Warning: could not load existing data: {e}")
        return [], set()


def save_output(remedies: list) -> None:
    """Save remedies list to JSON."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(remedies, f, indent=2, ensure_ascii=False)


def main():
    """Main entry — crawls A-Z and scrapes all remedies."""
    print("=" * 60)
    print("Boericke's Homoeopathic Materia Medica Scraper")
    print("=" * 60)

    all_remedies, scraped_urls = load_existing_data()
    letters = "abcdefghijklmnopqrstuvwxyz"

    for letter in letters:
        print(f"\n[{letter.upper()}] Fetching index...")

        soup = fetch_letter_index(letter)
        if not soup:
            print(f"[{letter.upper()}] SKIPPED — could not fetch index")
            continue

        remedy_links = parse_remedy_links(soup, letter)
        total = len(remedy_links)

        if total == 0:
            print(f"[{letter.upper()}] No remedies found")
            continue

        print(f"[{letter.upper()}] Found {total} remedies")

        for i, info in enumerate(remedy_links, 1):
            url = info["url"]
            abbreviation = info["abbreviation"]

            if url in scraped_urls:
                continue

            print(f"  [{letter.upper()}] Scraped {i}/{total} - {abbreviation}")

            remedy = scrape_remedy_page(url, abbreviation, letter.upper())

            if remedy:
                all_remedies.append(remedy)
                scraped_urls.add(url)
                save_output(all_remedies)

            time.sleep(DELAY)

        time.sleep(1.0)

    save_output(all_remedies)

    print("\n" + "=" * 60)
    print(f"DONE. Total remedies scraped: {len(all_remedies)}")
    print(f"Output: {OUTPUT_FILE}")

    sample = all_remedies[:5]
    with open("sample_output.json", "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    print("Sample saved: sample_output.json")
    print("=" * 60)


if __name__ == "__main__":
    main()