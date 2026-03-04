import psycopg2
from psycopg2.extras import RealDictCursor
from core.config import DB_URL

def get_db_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)