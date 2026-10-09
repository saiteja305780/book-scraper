import csv
import logging
import re
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio book scraper)"}
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
FIELDNAMES = ["title", "price", "rating", "availability", "url", "page"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def fetch(session, url, retries=3):
    """Return page HTML, or None if all retries fail."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"  # fixes the £ symbol
            return response.text
        except requests.RequestException as error:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, error)
            time.sleep(2 ** attempt)
    return None


def parse_book(book, page):
    link = book.select_one("h3 a")
    price = book.select_one(".price_color")
    availability = book.select_one(".availability")
    rating = book.select_one(".star-rating")

    rating_word = next(
        (c for c in rating.get("class", []) if c != "star-rating"), None
    ) if rating else None

    return {
        "title": link.get("title") if link else None,
        "price": float(re.sub(r"[^\d.]", "", price.get_text())) if price else None,
        "rating": RATINGS.get(rating_word),
        "availability": availability.get_text(strip=True) if availability else None,
        "url": "https://books.toscrape.com/catalogue/" + link["href"] if link else None,
        "page": page,
    }


def scrape_all():
    books, page = [], 1
    with requests.Session() as session:
        session.headers.update(HEADERS)
        while True:
            log.info("Scraping page %d", page)
            html = fetch(session, BASE_URL.format(page))
            if html is None:
                log.error("Giving up on page %d", page)
                break

            soup = BeautifulSoup(html, "html.parser")
            books.extend(parse_book(b, page) for b in soup.select("article.product_pod"))

            if not soup.select_one("li.next"):  # last page reached
                break
            page += 1
            time.sleep(0.5)  # be polite
    return books


def save_csv(books, filename="books.csv"):
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(books)
    log.info("Saved %d books to %s", len(books), filename)


def print_report(books):
    counts = Counter(b["rating"] for b in books)
    print(f"\nTotal books: {len(books)}")
    for stars in sorted(k for k in counts if k):
        print(f"{stars} stars: {counts[stars]}")


def main():
    books = scrape_all()
    save_csv(books)
    print_report(books)


if __name__ == "__main__":
    main()