"""Database adapter — SQLite (local) or PostgreSQL/Supabase (production)."""
import os
import re
import sqlite3
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

INSERT_OR_IGNORE_CONFLICT = {
    "suppressions": "ON CONFLICT (email) DO NOTHING",
    "campaign_leads": "ON CONFLICT (campaign_id, lead_id) DO NOTHING",
}


def _normalize_database_url(database_url):
    url = database_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    is_pooler = "pooler.supabase.com" in url or ":6543/" in url or url.rstrip("/").endswith(":6543")

    parsed = urlparse(url)
    # psycopg2/libpq rejects pgbouncer=; disable prepared statements for pooler instead.
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "pgbouncer"]
    if not any(k.lower() == "sslmode" for k, _ in query):
        query.append(("sslmode", "require"))
    url = urlunparse(parsed._replace(query=urlencode(query)))
    return url, is_pooler


def _translate_sql_postgres(sql):
    m = re.match(
        r"INSERT OR IGNORE INTO (\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
        sql.strip(),
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        table = m.group(1)
        cols = m.group(2)
        vals = m.group(3)
        conflict = INSERT_OR_IGNORE_CONFLICT.get(table, "ON CONFLICT DO NOTHING")
        sql = f"INSERT INTO {table} ({cols}) VALUES ({vals}) {conflict}"
    return sql.replace("?", "%s")


class _Result:
    def __init__(self, cursor, is_select=False, is_insert=False):
        self._cursor = cursor
        self.rowcount = cursor.rowcount
        self.lastrowid = None
        self._is_select = is_select
        if is_insert:
            row = cursor.fetchone()
            if row:
                self.lastrowid = row.get("id")

    def fetchone(self):
        if self._is_select:
            return self._cursor.fetchone()
        return None

    def fetchall(self):
        if self._is_select:
            return self._cursor.fetchall()
        return []


class PostgresConnection:
    backend = "postgres"

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        import psycopg2.extras

        sql = _translate_sql_postgres(sql)
        params = tuple(params) if params else ()
        head = sql.strip().upper()
        is_select = head.startswith("SELECT")
        is_insert = head.startswith("INSERT")

        run_sql = sql
        if is_insert and "RETURNING" not in head:
            run_sql = sql.rstrip().rstrip(";") + " RETURNING id"

        cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(run_sql, params)
        return _Result(cur, is_select=is_select, is_insert=is_insert)

    def commit(self):
        self._raw.commit()

    def executescript(self, script):
        pass


def _clean_database_url(database_url):
    url = (database_url or "").strip()
    if url.upper().startswith("DATABASE_URL="):
        url = url.split("=", 1)[1].strip()
    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1]
    return url


def _check_serverless_database_url(url):
    if not os.getenv("VERCEL"):
        return
    is_direct = re.search(r"@db\.[^/]+\.supabase\.co:5432/", url)
    if is_direct:
        raise ValueError(
            "DATABASE_URL uses Supabase direct connection (port 5432). "
            "Vercel requires the Transaction pooler (port 6543). "
            "In Supabase → Project Settings → Database → Connection string, "
            "choose URI + Transaction pooler, then update DATABASE_URL in Vercel."
        )


def connect_postgres(database_url):
    import psycopg2

    url, is_pooler = _normalize_database_url(_clean_database_url(database_url))
    _check_serverless_database_url(url)
    raw = psycopg2.connect(url)
    if is_pooler:
        raw.prepare_threshold = None
    raw.autocommit = False
    return PostgresConnection(raw)


def connect_sqlite(path):
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.backend = "sqlite"  # type: ignore[attr-defined]
    return con


def get_connection(database_path="campaign.db"):
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return connect_postgres(database_url)
    return connect_sqlite(database_path)
