import os
import traceback
from loguru import logger as logging
import smtplib
from email.message import EmailMessage


class BooksMailer:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER")
        self.smtp_port = os.environ.get("SMTP_PORT") or 587
        self.sender_email = os.environ.get("SMTP_LOGIN")
        self.sender_password = os.environ.get("SMTP_PASSWORD")

    def send_email(self, to, subject, body):
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = "📚 Nouveaux livres cette semaine"
        msg["From"] = self.sender_email
        msg["To"] = to

        try:
            logging.debug(f"Connecting to SMTP server: {os.environ.get('SMTP_SERVER')}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Sécurise la connexion
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            logging.info(f"✉️ Email envoyé à {msg['To']}")
        except Exception as e:
            logging.warning(f"Erreur lors de l'envoi de l'email : {e}")
            logging.warning(traceback.format_exc())

    def send_weekly_news(self, to: str):
        """
        Send an email report of newly added books for the week.
        """
        body = ["📚 Des nouvelles de vos librairies !\n\n"]

        weekly_books = self.get_weekly_books()
        if not weekly_books:
            body.append("😫 Pas de nouveaux livres / édition parues la semaine dernière.")
        else:
            body.append("📚 Nouveaux livres parus la semaine dernière:")
            for book in weekly_books:
                body.append(f"- {book['title']} by {book['author']} ({book['publication_date']})")

        monthly_books = self.get_montly_books()
        if not monthly_books:
            body.append("😫 Pas de nouveaux livres / édition ce mois-ci.")
        else:
            body.append("📚 Nouveaux livres ce mois-ci:")
            for book in monthly_books:
                body.append(f"- {book['title']} by {book['author']} ({book['publication_date']})")

        BODY = "\n".join(body)

        self.send_email(to, "📚 Quoi de neuf en librairie ?", BODY)
