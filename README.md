# Boericke's Homoeopathic Materia Medica Scraper

A Python web scraper that crawls all A–Z remedy pages from [Boericke's Materia Medica](http://homeoint.org/books/boericmm/) and produces a clean, structured JSON dataset.

Built for **jarvis.care** — an AI-powered clinical assistant for homeopathic practitioners.



## Output

- **688 remedies** scraped across all 26 letters
- Structured JSON with sections, relationships, and common names
- Ready for use in remedy search, repertorization, and AI analysis



## Project Structure
## Project Structure

```
boericke-scraper/
├── scraper.py              # Main scraper script
├── requirements.txt        # Pinned dependencies
├── README.md               # This file
├── boericke_remedies.json  # Full dataset (688 remedies)
├── sample_output.json      # 5 remedy sample
└── failed_urls.txt         # URLs that failed
```

## Setup

**1. Clone the repository**
```bash
git clone https://github.com/Manshikatiyar/boericke-scraper.git
cd boericke-scraper
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

---

## Run

```bash
python scraper.py
```

**Sample output:**
---

## Output Schema

```json
{
  "abbreviation": "ABIES-C",
  "full_name": "ABIES CANADENSIS-PINUS CANADENSIS",
  "common_name": "Hemlock Spruce",
  "source_url": "http://homeoint.org/books/boericmm/a/abies-c.htm",
  "letter": "A",
  "general": "Mucous membranes are affected...",
  "sections": {
    "Head": "Feels light-headed, tipsy...",
    "Stomach": "Canine hunger with torpid liver...",
    "Dose": "First to third potency."
  },
  "relationships": null
}
```

---

## Features

- Crawls all 26 letter index pages (A–Z)
- Extracts full name, common name, general description, sections, and relationships
- **Resumable** — skips already-scraped URLs if interrupted
- **Error handling** — logs failed URLs to `failed_urls.txt` and continues
- 0.7 second delay between requests to respect the server
- Saves progress after every single remedy

---

## Tech Stack

- Python 3.9+
- `requests` — HTTP fetching
- `beautifulsoup4` — HTML parsing
- `json` — output formatting
