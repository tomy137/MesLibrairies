import requests
import re
from loguru import logger as logging
from bs4 import BeautifulSoup
from datetime import date


FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}


class BooksScraper:
    """A class to scrape books from leslibraires.fr."""

    def scrap_books_by_author(self, author_id, author_slug):
        """Scrape books by a specific author from leslibraires.fr."""
        htmx_url = f"{self.source_url}/htmx/contributions/?personID={author_id}&contributionType=By(author)"
        page = 1
        added_books = []
        fetched_books = []

        logging.debug(f"🌎 Fetching {author_slug} books ...")

        while True:
            r = requests.get(htmx_url, params={"page": page}, headers=self.headers)

            if not r.content.strip():
                break

            books = self.extract_books_from_html(r.text)
            if not books:
                break

            fetched_books.extend(books)
            found_new_on_this_page = False

            for book in books:
                if not (book["title"] and book["author"]):
                    continue
                book_details = self.parse_livre_details(book["url"])
                non_null_details = {k: v for k, v in book_details.items() if v is not None}
                merged = {**book, **non_null_details, "author_id": author_id}

                if self.insert_book(merged):
                    logging.debug(f"├─ 📘 New book: {book['title']} by {book['author']}")
                    found_new_on_this_page = True
                    added_books.append(book)

            if not found_new_on_this_page:
                break

            page += 1

        logging.debug(f"🌎 Fetching {author_slug} books, find {len(fetched_books)} books, {len(added_books)} are new !")
        return added_books

    def parse_livre_details(self, url):
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        # === COUVERTURE depuis la page de détail ===
        cover_elem = soup.select_one("div.product-media img")
        picture_link = None
        if cover_elem and cover_elem.has_attr("src"):
            src = cover_elem["src"]
            if "default/book" not in src:
                picture_link = f"https:{src}" if src.startswith("//") else src

        # === DESCRIPTION ===
        desc_elem = soup.select_one("article.product-description")
        description = desc_elem.get_text(separator="\n").strip() if desc_elem else ""

        # === FIELDS TO EXTRACT ===
        wanted_fields = {
            "picture_link": picture_link,
            "Format": None,
            "EAN13": None,
            "ISBN": None,
            "Date de publication": None,
            "Collection": None,
            "Nombre de pages": None,
            "Langue": None,
            "description": description,
        }

        for row in soup.select("article.product-features table tr"):
            th = row.select_one("th")
            td = row.select_one("td")
            if th and td:
                label = th.get_text(strip=True)
                value = td.get_text(" ", strip=True)
                if label in wanted_fields:
                    wanted_fields[label] = value

        # Parse "Date de publication" to ISO format if present
        date_pub = wanted_fields.get("Date de publication")
        if date_pub:
            match = re.match(r"(\d{1,2}) (\w+) (\d{4})", date_pub)
            if match:
                day, month_fr, year = match.groups()
                month = FRENCH_MONTHS.get(month_fr.lower())
                if month:
                    try:
                        wanted_fields["Date de publication"] = date(int(year), month, int(day)).isoformat()
                    except ValueError:
                        pass

        collection = wanted_fields.get("Collection")
        if collection:
            wanted_fields["Collection"] = self.clean_name(collection)

        return wanted_fields

    def extract_books_from_html(self, html):
        soup = BeautifulSoup(html, "html.parser")

        books = []
        for book_item in soup.select("article.card-product"):
            title_elem = book_item.select_one(".card-product__title a")
            title = title_elem.text.strip() if title_elem else None
            link = self.source_url + title_elem["href"] if title_elem and title_elem.has_attr("href") else None

            picture_link_elem = book_item.select_one(".card-product__media img")
            picture_link = f"https:{picture_link_elem['src']}" if picture_link_elem and picture_link_elem.has_attr("src") else None

            author_elem = book_item.select_one(".card-product__author")
            author = author_elem.text.strip() if author_elem else None

            publisher_elem = book_item.select_one(".card-product__edition")
            publisher = publisher_elem.text.strip() if publisher_elem else None

            books.append(
                {
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "url": link,
                    "picture_link": picture_link,
                }
            )

        return books

    def clean_name(self, name: str) -> str:
        if not name:
            return ""
        # Supprimer uniquement les parenthèses contenant uniquement des chiffres
        name = re.sub(r"\s*\(\s*\d+\s*\)$", "", name)
        return name.strip()
