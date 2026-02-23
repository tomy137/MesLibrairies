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
        """
        Refresh books for all authors in the database.
        This method should be implemented to scrape books for each author.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT id, slug FROM authors")
        authors = cur.fetchall()

        self.last_scrapping_summary = []
        total_added_books = []
        
        for author in authors:
            author_id, author_slug = author
            try:
                added_books = self.scrap_books_by_author(author_id=author_id, author_slug=author_slug)
                total_added_books += added_books
                
                # Ajouter un résumé pour cet auteur
                self.last_scrapping_summary.append({
                    'author_slug': author_slug,
                    'author_id': author_id,
                    'books_added': len(added_books),
                    'books': added_books
                })
            except Exception as e:
                logging.warning(f"😟 Error fetching books for author {author_slug}: {e}")
                self.last_scrapping_summary.append({
                    'author_slug': author_slug,
                    'author_id': author_id,
                    'books_added': 0,
                    'books': [],
                    'error': str(e)
                })
                continue

        cur.close()
        if total_added_books:
            logging.info(f"📚 {len(total_added_books)} books added to the database.")
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
        author_id = args.author_id
        author_slug = args.author_slug
        logging.debug(f"Ajout de l'auteur {author_slug}({author_id}) à la base de données.")

        mesLibrairies.get_add_author(author_id, author_slug)
        # mesLibrairies.scrap_books_by_author(author_id, author_slug)

    elif args.command == "refresh":
        logging.debug("Rafraichissement des livres des auteurs déjà en base de données.")
        mesLibrairies.refresh_books()

    elif args.command == "send_report":
        logging.debug("Envoi du rapport par mail.")
        mesLibrairies.refresh_missing_covers()
        mesLibrairies.send_weekly_news(args.mail_to)

    elif args.command == "preview":
        logging.debug("Génération de la preview HTML.")
        weekly_books = mesLibrairies.get_weekly_books()
        monthly_books = mesLibrairies.get_monthly_books()

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
<div style="max-width:600px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <div style="background:#2c5282;color:white;padding:24px;text-align:center;">
        <h1 style="margin:0;font-size:22px;">📚 Des nouvelles de vos librairies !</h1>
    </div>
    <div style="padding:20px 24px;">
        {mesLibrairies._render_books_section("Cette semaine", weekly_books)}
        {mesLibrairies._render_books_section("Ce mois-ci", monthly_books)}
    </div>
    <div style="background:#f0f4f8;padding:12px;text-align:center;font-size:11px;color:#888;">
        MesLibrairies — données issues de leslibraires.fr
    </div>
</div>
</body></html>"""

        with open("/tmp/mail_preview.html", "w") as f:
            f.write(html)
        logging.info("✅ Preview saved to /tmp/mail_preview.html")

    else:
        logging.debug("Rafraichissement des livres des auteurs déjà en base de données ET envoi par mail.")
        mesLibrairies.refresh_books()
        if args.mail_to:
            mesLibrairies.refresh_missing_covers()
            mesLibrairies.send_weekly_news(args.mail_to)
