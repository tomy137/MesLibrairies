import sqlite3
from loguru import logger as logging
import pendulum


class BooksDB:
    def __init__(self):
        """
        Get a SQLite database connection.

        :param path: Path to the SQLite database file.
        :return: SQLite connection object.
        """
        self.conn = sqlite3.connect(self.db_path)
        cur = self.conn.cursor()

        # Crée la table des auteurs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY,
                slug TEXT,
                url TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author_id INTEGER,                
                author TEXT,
                publisher TEXT,
                url TEXT UNIQUE,
                format TEXT,
                ean13 TEXT,
                isbn TEXT,
                publication_date DATE,
                collection TEXT,
                pages INTEGER,
                language TEXT,
                description TEXT,
                picture_link TEXT,
                FOREIGN KEY (author_id) REFERENCES authors(id)                
            )
        """)

        self.conn.commit()
        cur.close()
        logging.debug("Database initialized and tables created.")
        return self.conn

    def get_add_author(self, author_id, author_slug):
        """
        Add an author to the database.
        :param author_id: ID of the author from leslibraires.fr
        :param author_slug: Slug of the author from leslibraires.fr
        """

        cur = self.conn.cursor()
        cur.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
        author_row = cur.fetchone()

        ## If the author is not found in the database, add them.
        if not author_row:
            author_url = f"{self.source}/personne/{author_slug}/{author_id}/"

            with self.conn as conn:
                author_row = conn(
                    """
                    INSERT INTO authors (id, slug, url)
                    VALUES (?, ?, ?)
                    RETURNING *                      -- renvoie la ligne tout de suite
                    """,
                    (author_id, author_slug, author_url),
                ).fetchone()

            logging.info(f"Author {author_slug} ({author_id}) added to the database.")

        return author_row

    def insert_book(self, book: dict) -> bool:
        with self.conn as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO books (
                        title, author, publisher, url,
                        format, ean13, isbn, publication_date,
                        collection, pages, language, description, author_id, picture_link
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        book.get("title"),
                        book.get("author"),
                        book.get("publisher"),
                        book.get("url"),
                        book.get("Format"),
                        book.get("EAN13"),
                        book.get("ISBN"),
                        book.get("Date de publication"),
                        book.get("Collection"),
                        int(book.get("Nombre de pages") or 0),
                        book.get("Langue"),
                        book.get("description"),
                        book.get("author_id"),
                        book.get("picture_link"),
                    ),
                )
                conn.commit()

                return True
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                logging.error(f"Error inserting book {book.get('title')}: {e}")
                return False

    def get_weekly_books(self):
        """
        Get books added in the last 7 days.
        """
        start_of_week = pendulum.now().start_of("week").date().isoformat()
        end_of_week = pendulum.now().end_of("week").date().isoformat()

        return self.get_books(f"""
            SELECT * FROM books
            WHERE publication_date >= {start_of_week} AND publication_date <= {end_of_week}
            ORDER BY publication_date DESC
        """)

    def get_montly_books(self):
        """
        Get books added during this month.
        """
        start_of_month = pendulum.now().start_of("month").date().isoformat()
        end_of_month = pendulum.now().end_of("month").date().isoformat()
        start_of_week = pendulum.now().start_of("week").date().isoformat()
        end_of_week = pendulum.now().end_of("week").date().isoformat()

        return self.get_books(f"""
            SELECT * FROM books
            WHERE (publication_date >= {start_of_month} AND publication_date <= {end_of_month})
            AND NOT (publication_date >= {start_of_week} AND publication_date <= {end_of_week})
            ORDER BY publication_date DESC
        """)

    def get_books(self, _SQL: str) -> list[dict]:
        """
        Get books from the database based on a SQL query.
        """
        with self.conn as conn:
            cur = conn.execute(_SQL)
            rows = cur.fetchall()
            columns = [column[0] for column in cur.description]

            books = []
            for row in rows:
                book = dict(zip(columns, row))
                books.append(book)

            return books
