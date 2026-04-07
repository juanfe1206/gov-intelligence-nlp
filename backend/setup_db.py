#!/usr/bin/env python3
"""Database setup script - creates database and pgvector extension."""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import sql

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_SYNC_URL",
    "postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp",
)
parsed = urlparse(DATABASE_URL)
if parsed.scheme != "postgresql" or not parsed.hostname or not parsed.path:
    print("ERROR: Invalid DATABASE_SYNC_URL format")
    sys.exit(1)

user = parsed.username
password = parsed.password or ""
host = parsed.hostname
port = parsed.port or 5432
dbname = parsed.path.lstrip("/")

if not user or not dbname:
    print("ERROR: DATABASE_SYNC_URL must include username and database name")
    sys.exit(1)

# Connect to default postgres database to create new database
try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Create database if not exists
    cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
    print(f"[OK] Database '{dbname}' created successfully")
    cursor.close()
    conn.close()

except psycopg2.Error as e:
    if "already exists" in str(e):
        print(f"[INFO] Database '{dbname}' already exists")
    else:
        print(f"ERROR: {e}")
        sys.exit(1)

# Connect to new database to create pgvector extension
try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=dbname
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Create pgvector extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    print("[OK] pgvector extension created successfully")
    cursor.close()
    conn.close()

except psycopg2.Error as e:
    print(f"ERROR creating pgvector extension: {e}")
    sys.exit(1)

print("\n[DONE] Database setup complete!")
