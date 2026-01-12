"""NUFORC UFO Report Scraper for Oregon/Portland"""
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from datetime import datetime
from config import RAW_DIR, NUFORC_DELAY, OREGON_BBOX, PORTLAND_BBOX
from db_utils import insert_records
import os

NUFORC_BASE = "https://nuforc.org/webreports"

def scrape_oregon_reports():
    """Scrape all Oregon UFO reports from NUFORC"""
    print("Fetching Oregon index page...")

    # Try to get the Oregon-specific page
    oregon_url = f"{NUFORC_BASE}/ndxlOR.html"
    response = requests.get(oregon_url, timeout=30)

    if response.status_code != 200:
        print(f"Failed to fetch Oregon index: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    reports = []

    # Find all report links
    table = soup.find('table')
    if not table:
        print("No table found on page")
        return []

    rows = table.find_all('tr')[1:]  # Skip header
    print(f"Found {len(rows)} Oregon report entries")

    for i, row in enumerate(rows):
        try:
            cols = row.find_all('td')
            if len(cols) < 7:
                continue

            # Extract link to detail page
            link = cols[0].find('a')
            if not link:
                continue

            detail_url = f"{NUFORC_BASE}/{link.get('href')}"

            # Parse basic info from index
            date_str = cols[0].get_text(strip=True)
            city = cols[1].get_text(strip=True)
            state = cols[2].get_text(strip=True)
            country = cols[3].get_text(strip=True)
            shape = cols[4].get_text(strip=True)
            duration = cols[5].get_text(strip=True)
            summary = cols[6].get_text(strip=True) if len(cols) > 6 else ""

            report = {
                'event_date': parse_date(date_str),
                'city': city,
                'state': 'OR',
                'raw_location': f"{city}, OR",
                'phenomenon_type': 'ufo_uap',
                'phenomenon_subtype': shape,
                'description': summary,
                'duration_seconds': parse_duration(duration),
                'data_source': 'nuforc',
                'source_url': detail_url,
                'report_source': 'NUFORC'
            }

            # Check if Portland metro area
            if is_portland_area(city):
                report['loc_precision'] = 'city'

            reports.append(report)

            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(rows)} entries")

        except Exception as e:
            print(f"Error parsing row {i}: {e}")
            continue

        time.sleep(NUFORC_DELAY * 0.1)  # Light delay for index parsing

    return reports

def is_portland_area(city):
    """Check if city is in Portland metro area"""
    portland_cities = [
        'portland', 'beaverton', 'hillsboro', 'gresham', 'tigard',
        'lake oswego', 'oregon city', 'milwaukie', 'tualatin', 'west linn',
        'wilsonville', 'sherwood', 'happy valley', 'clackamas', 'troutdale',
        'fairview', 'wood village', 'maywood park', 'gladstone', 'johnson city',
        'rivergrove', 'durham', 'king city', 'damascus', 'sandy'
    ]
    return city.lower().strip() in portland_cities

def parse_date(date_str):
    """Parse NUFORC date format"""
    try:
        # Common formats: "1/15/2023", "01/15/23"
        for fmt in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
            except:
                continue
    except:
        pass
    return None

def parse_duration(duration_str):
    """Parse duration string to seconds"""
    if not duration_str:
        return None

    duration_str = duration_str.lower().strip()

    # Try to extract numbers
    numbers = re.findall(r'[\d.]+', duration_str)
    if not numbers:
        return None

    try:
        value = float(numbers[0])

        if 'hour' in duration_str:
            return int(value * 3600)
        elif 'minute' in duration_str or 'min' in duration_str:
            return int(value * 60)
        elif 'second' in duration_str or 'sec' in duration_str:
            return int(value)
        else:
            return int(value * 60)  # Default to minutes
    except:
        return None

def main():
    print("=" * 60)
    print("NUFORC Oregon UFO Report Scraper")
    print("=" * 60)

    reports = scrape_oregon_reports()

    if not reports:
        print("No reports scraped")
        return

    print(f"\nScraped {len(reports)} Oregon reports")

    # Save raw data
    raw_file = os.path.join(RAW_DIR, "nuforc_oregon.json")
    with open(raw_file, 'w') as f:
        json.dump(reports, f, indent=2, default=str)
    print(f"Saved raw data to {raw_file}")

    # Filter for Portland metro
    portland_reports = [r for r in reports if is_portland_area(r.get('city', ''))]
    print(f"Portland metro area reports: {len(portland_reports)}")

    # Insert into database
    print("\nInserting into database...")
    inserted, errors = insert_records('specter_paranormal_reports', reports)
    print(f"Inserted {inserted} records")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:5]:
            print(f"  {e}")

    return reports

if __name__ == "__main__":
    main()
