import os
from html import escape
from loguru import logger as logging
import smtplib
from email.message import EmailMessage

# URL de l'image placeholder utilisée quand un livre n'a pas de couverture
DEFAULT_COVER = "https://static.leslibraires.fr//websites/design_2024/static/assets/icons/default/book.avif"


class BooksMailer:
    """Génération et envoi de la newsletter HTML par email (SMTP)."""

    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER")
        self.smtp_port = os.environ.get("SMTP_PORT") or 587
        self.sender_email = os.environ.get("SMTP_LOGIN")
        self.sender_password = os.environ.get("SMTP_PASSWORD")

    def send_email(self, to, subject, html_body):
        """Envoie un email HTML via SMTP avec STARTTLS."""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to
        msg.set_content("Votre client mail ne supporte pas le HTML.")
        msg.add_alternative(html_body, subtype="html")

        try:
            logging.debug(f"Connecting to SMTP server: {self.smtp_server}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            logging.info(f"✉️ Email envoyé à {msg['To']}")
        except Exception:
            logging.opt(exception=True).warning("Erreur lors de l'envoi de l'email")

    def _book_cover_url(self, book):
        """Retourne l'URL de couverture du livre, ou None si c'est l'image par défaut ou une URL invalide."""
        url = book.get("picture_link") or ""
        if DEFAULT_COVER in url or not url.startswith("https://"):
            return None
        return url

    # Mots-clés dans le titre qui indiquent une réédition plutôt qu'une nouveauté
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
        if any(kw in title_lower for kw in self.REEDITION_KEYWORDS):
            return True

        # 3. Same author already has a similar title in DB
        author_id = book.get("author_id")
        book_id = book.get("id")
        return bool(
            author_id and book_id
            and self.has_similar_book(author_id, book.get("title", ""), book_id)
        )

    def _render_book_card(self, book):
        """Génère le HTML d'une carte livre (couverture + titre + badge nouveau/réédition)."""
        title = escape(book.get("title") or "Sans titre")
        author = escape(book.get("author") or "Inconnu")
        date = escape(book.get("publication_date") or "")
        publisher = escape(book.get("publisher") or "")
        url = book.get("url") or "#"
        cover_url = self._book_cover_url(book)

        badge_style = "display:inline-block;font-size:11px;font-weight:600;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:middle;"
        if self._detect_reedition(book):
            badge = f'<span style="{badge_style}background:#fed7aa;color:#c2410c;">📙 Réédition</span>'
        else:
            badge = f'<span style="{badge_style}background:#bbf7d0;color:#15803d;">📗 Nouveau</span>'

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
        """Génère une section HTML (titre + liste de cartes livres), ou un message vide si aucun livre."""
        if not books:
            return f"""
            <div style="margin:20px 0;padding:16px;background:#f7f7f7;border-radius:8px;color:#666;text-align:center;">
                😫 {escape(title)} : rien de nouveau.
            </div>"""

        # Séparer nouveautés et rééditions, nouveautés en premier
        nouveautes = [b for b in books if not self._detect_reedition(b)]
        reeditions = [b for b in books if self._detect_reedition(b)]
        sorted_books = nouveautes + reeditions

        cards = "\n".join(self._render_book_card(book) for book in sorted_books)
        return f"""
        <div style="margin:20px 0;">
            <h2 style="color:#2c5282;font-size:18px;border-bottom:2px solid #2c5282;padding-bottom:6px;">📚 {escape(title)}</h2>
            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                {cards}
            </table>
        </div>"""

    def _render_scrapping_report(self):
        """Génère le tableau HTML récapitulatif du scrapping (auteurs traités, livres ajoutés, erreurs)."""
        summary = getattr(self, 'last_scrapping_summary', [])
        if not summary:
            return ""

        total_books = sum(s['books_added'] for s in summary)
        total_authors = len(summary)

        rows = []
        cell = "padding:3px 8px;"
        for s in summary:
            slug = escape(s['author_slug'])
            if 'error' in s:
                rows.append(f"<tr><td style='{cell}'>❌ {slug}</td><td style='color:red;{cell}'>Erreur</td></tr>")
            elif s['books_added'] == 0:
                rows.append(f"<tr><td style='{cell}'>✅ {slug}</td><td style='color:#888;{cell}'>Aucun nouveau</td></tr>")
            else:
                book_lines = "".join(
                    f"<div style='padding:1px 0 1px 16px;color:#555;'>└─ {escape(b.get('title', 'N/A'))} ({escape(b.get('author', 'N/A'))})</div>"
                    for b in s['books']
                )
                rows.append(f"<tr><td colspan='2' style='{cell}'>📘 {slug} : <strong>{s['books_added']} ajouté(s)</strong>{book_lines}</td></tr>")

        return f"""
        <div style="margin:30px 0 10px;padding:16px;background:#f0f4f8;border-radius:8px;font-size:13px;">
            <strong>📋 Rapport de scrapping</strong> — {total_authors} auteur(s), {total_books} livre(s) ajouté(s)
            <table cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;width:100%;">
                {"".join(rows)}
            </table>
        </div>"""

    def build_newsletter_html(self, extra_content: str = "") -> str:
        """Build the full HTML newsletter with weekly/monthly books and optional extra content."""
        weekly_books = self.get_weekly_books()
        monthly_books = self.get_monthly_books()

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
<div style="max-width:600px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <div style="background:#2c5282;color:white;padding:24px;text-align:center;">
        <h1 style="margin:0;font-size:22px;">📚 Des nouvelles de vos librairies !</h1>
    </div>
    <div style="padding:20px 24px;">
        {self._render_books_section("Cette semaine", weekly_books)}
        {self._render_books_section("Ce mois-ci", monthly_books)}
        {extra_content}
    </div>
    <div style="background:#f0f4f8;padding:12px;text-align:center;font-size:11px;color:#888;">
        MesLibrairies — données issues de leslibraires.fr
    </div>
</div>
</body></html>"""

    def send_weekly_news(self, to: str):
        """Construit et envoie la newsletter hebdomadaire avec le rapport de scrapping."""
        html = self.build_newsletter_html(extra_content=self._render_scrapping_report())
        self.send_email(to, "📚 Quoi de neuf en librairie ?", html)
