import os
import traceback
from html import escape
from loguru import logger as logging
import smtplib
from email.message import EmailMessage

DEFAULT_COVER = "https://static.leslibraires.fr//websites/design_2024/static/assets/icons/default/book.avif"


class BooksMailer:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER")
        self.smtp_port = os.environ.get("SMTP_PORT") or 587
        self.sender_email = os.environ.get("SMTP_LOGIN")
        self.sender_password = os.environ.get("SMTP_PASSWORD")

    def send_email(self, to, subject, html_body):
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to
        msg.set_content("Votre client mail ne supporte pas le HTML.")
        msg.add_alternative(html_body, subtype="html")

        try:
            logging.debug(f"Connecting to SMTP server: {os.environ.get('SMTP_SERVER')}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            logging.info(f"✉️ Email envoyé à {msg['To']}")
        except Exception as e:
            logging.warning(f"Erreur lors de l'envoi de l'email : {e}")
            logging.warning(traceback.format_exc())

    def _book_cover_url(self, book):
        url = book.get("picture_link") or ""
        if DEFAULT_COVER in url or not url.startswith("https://"):
            return None
        return url

    REEDITION_KEYWORDS = [
        "nouvelle traduction",
        "édition collector",
        "collector",
        "nouvelle édition",
        "édition anniversaire",
        "édition illustrée",
        "edition 20",
    ]

    def _detect_reedition(self, book) -> bool:
        """Return True if the book is likely a reprint/reedition."""
        # 1. Format Poche
        if (book.get("format") or "").lower() == "poche":
            return True

        # 2. Keywords in title
        title_lower = (book.get("title") or "").lower()
        for kw in self.REEDITION_KEYWORDS:
            if kw in title_lower:
                return True

        # 3. Same author already has a similar title in DB
        author_id = book.get("author_id")
        book_id = book.get("id")
        if author_id and book_id:
            if self.has_similar_book(author_id, book.get("title", ""), book_id):
                return True

        return False

    def _render_book_card(self, book):
        title = escape(book.get("title") or "Sans titre")
        author = escape(book.get("author") or "Inconnu")
        date = escape(book.get("publication_date") or "")
        publisher = escape(book.get("publisher") or "")
        url = book.get("url") or "#"
        cover_url = self._book_cover_url(book)

        is_reedition = self._detect_reedition(book)
        if is_reedition:
            badge = '<span style="display:inline-block;background:#fed7aa;color:#c2410c;font-size:11px;font-weight:600;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:middle;">📙 Réédition</span>'
        else:
            badge = '<span style="display:inline-block;background:#bbf7d0;color:#15803d;font-size:11px;font-weight:600;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:middle;">📗 Nouveau</span>'

        cover_html = ""
        if cover_url:
            cover_html = f"""
                <td style="vertical-align:top;padding-right:12px;width:80px;">
                    <img src="{escape(cover_url)}" alt="{title}" style="width:80px;border-radius:4px;" />
                </td>"""

        publisher_html = f"<br/><span style='color:#888;font-size:12px;'>{publisher}</span>" if publisher else ""

        return f"""
        <tr><td style="padding:8px 0;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
                {cover_html}
                <td style="vertical-align:top;">
                    <a href="{escape(url)}" style="color:#2c5282;text-decoration:none;font-weight:600;font-size:14px;">{title}</a>
                    {badge}
                    <br/><span style="color:#555;font-size:13px;">{author}</span>
                    {publisher_html}
                    <br/><span style="color:#888;font-size:12px;">📅 {date}</span>
                </td>
            </tr></table>
        </td></tr>"""

    def _render_books_section(self, title, books):
        if not books:
            return f"""
            <div style="margin:20px 0;padding:16px;background:#f7f7f7;border-radius:8px;color:#666;text-align:center;">
                😫 {escape(title)} : rien de nouveau.
            </div>"""

        cards = "\n".join(self._render_book_card(book) for book in books)
        return f"""
        <div style="margin:20px 0;">
            <h2 style="color:#2c5282;font-size:18px;border-bottom:2px solid #2c5282;padding-bottom:6px;">📚 {escape(title)}</h2>
            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                {cards}
            </table>
        </div>"""

    def _render_scrapping_report(self):
        if not hasattr(self, 'last_scrapping_summary') or not self.last_scrapping_summary:
            return ""

        total_books = sum(s['books_added'] for s in self.last_scrapping_summary)
        total_authors = len(self.last_scrapping_summary)

        rows = []
        for s in self.last_scrapping_summary:
            slug = escape(s['author_slug'])
            if 'error' in s:
                rows.append(f"<tr><td style='padding:3px 8px;'>❌ {slug}</td><td style='color:red;padding:3px 8px;'>Erreur</td></tr>")
            elif s['books_added'] == 0:
                rows.append(f"<tr><td style='padding:3px 8px;'>✅ {slug}</td><td style='color:#888;padding:3px 8px;'>Aucun nouveau</td></tr>")
            else:
                book_lines = "".join(
                    f"<div style='padding:1px 0 1px 16px;color:#555;'>└─ {escape(b.get('title', 'N/A'))} ({escape(b.get('author', 'N/A'))})</div>"
                    for b in s['books']
                )
                rows.append(f"<tr><td colspan='2' style='padding:3px 8px;'>📘 {slug} : <strong>{s['books_added']} ajouté(s)</strong>{book_lines}</td></tr>")

        return f"""
        <div style="margin:30px 0 10px;padding:16px;background:#f0f4f8;border-radius:8px;font-size:13px;">
            <strong>📋 Rapport de scrapping</strong> — {total_authors} auteur(s), {total_books} livre(s) ajouté(s)
            <table cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;width:100%;">
                {"".join(rows)}
            </table>
        </div>"""

    def send_weekly_news(self, to: str):
        weekly_books = self.get_weekly_books()
        monthly_books = self.get_monthly_books()

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
<div style="max-width:600px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <div style="background:#2c5282;color:white;padding:24px;text-align:center;">
        <h1 style="margin:0;font-size:22px;">📚 Des nouvelles de vos librairies !</h1>
    </div>
    <div style="padding:20px 24px;">
        {self._render_books_section("Cette semaine", weekly_books)}
        {self._render_books_section("Ce mois-ci", monthly_books)}
        {self._render_scrapping_report()}
    </div>
    <div style="background:#f0f4f8;padding:12px;text-align:center;font-size:11px;color:#888;">
        MesLibrairies — données issues de leslibraires.fr
    </div>
</div>
</body></html>"""

        self.send_email(to, "📚 Quoi de neuf en librairie ?", html)
