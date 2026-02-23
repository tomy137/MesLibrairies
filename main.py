#!/usr/bin/env python3
"""
Scraper for leslibraires.fr to fetch books by author and store them in a SQLite database.
This script can also send an email report of newly added books.
"""

import argparse
from loguru import logger as logging
import os

from core.scrapper import BooksScraper
from core.db import BooksDB
from core.mailer import BooksMailer


class MesLibrairies(
    BooksDB,
    BooksScraper,
    BooksMailer,
):
    def __init__(self):
        self.db_path = os.environ.get("DB_PATH") or "books.db"
        self.source_url = os.environ.get("SOURCE_URL") or "https://www.leslibraires.fr"
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "HX-Request": "true",
        }
        self.last_scrapping_summary = []

        BooksDB.__init__(self)
        BooksScraper.__init__(self)
        BooksMailer.__init__(self)

    def refresh_missing_covers(self):
        books = self.get_books_missing_cover()
        if not books:
            return
        logging.info(f"🖼️ {len(books)} livre(s) sans couverture, tentative de récupération...")
        updated = 0
        for book in books:
            try:
                details = self.parse_livre_details(book["url"])
                cover = details.get("picture_link")
                if cover:
                    self.update_book_cover(book["url"], cover)
                    updated += 1
            except Exception as e:
                logging.warning(f"Erreur récupération couverture pour {book['title']}: {e}")
        logging.info(f"🖼️ {updated} couverture(s) mise(s) à jour.")

    def refresh_books(self):
        """Refresh books for all authors in the database."""
        cur = self.conn.cursor()
        cur.execute("SELECT id, slug FROM authors")
        authors = cur.fetchall()
        cur.close()

        self.last_scrapping_summary = []
        total_added = 0

        for author_id, author_slug in authors:
            try:
                added_books = self.scrap_books_by_author(author_id=author_id, author_slug=author_slug)
                total_added += len(added_books)
                self.last_scrapping_summary.append({
                    'author_slug': author_slug,
                    'author_id': author_id,
                    'books_added': len(added_books),
                    'books': added_books,
                })
            except Exception as e:
                logging.warning(f"😟 Error fetching books for author {author_slug}: {e}")
                self.last_scrapping_summary.append({
                    'author_slug': author_slug,
                    'author_id': author_id,
                    'books_added': 0,
                    'books': [],
                    'error': str(e),
                })

        if total_added:
            logging.info(f"📚 {total_added} books added to the database.")
        else:
            logging.info("No new books were added.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape books from leslibraires.fr")
    parser.add_argument("--author_id", required=False, help="Author ID from leslibraires.fr (e.g., 1949874 for Stephen King)")
    parser.add_argument("--author_slug", required=False, help="Author Slug from leslibraires.fr (e.g., stephen-king for Stephen King)")
    parser.add_argument("--mail_to", required=False, help="Send report by mail to")
    parser.add_argument("command", nargs="?", choices=["send_report", "refresh", "add", "preview"], help="Special command (e.g., send_report, refresh, add, preview)")
    args = parser.parse_args()

    mesLibrairies = MesLibrairies()

    if args.command == "add":
        logging.debug(f"Ajout de l'auteur {args.author_slug}({args.author_id}) à la base de données.")
        mesLibrairies.get_add_author(args.author_id, args.author_slug)

    elif args.command == "refresh":
        logging.debug("Rafraichissement des livres des auteurs déjà en base de données.")
        mesLibrairies.refresh_books()

    elif args.command == "send_report":
        logging.debug("Envoi du rapport par mail.")
        mesLibrairies.refresh_missing_covers()
        mesLibrairies.send_weekly_news(args.mail_to)

    elif args.command == "preview":
        logging.debug("Génération de la preview HTML.")
        html = mesLibrairies.build_newsletter_html()
        with open("/tmp/mail_preview.html", "w") as f:
            f.write(html)
        logging.info("✅ Preview saved to /tmp/mail_preview.html")

    else:
        logging.debug("Rafraichissement des livres des auteurs déjà en base de données ET envoi par mail.")
        mesLibrairies.refresh_books()
        if args.mail_to:
            mesLibrairies.refresh_missing_covers()
            mesLibrairies.send_weekly_news(args.mail_to)
