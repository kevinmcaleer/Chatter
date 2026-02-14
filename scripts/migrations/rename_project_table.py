#!/usr/bin/env python3
"""Rename project table to projects"""
import psycopg2

DB_HOST = "192.168.2.3"
DB_PORT = "5433"
DB_NAME = "kevsrobots_cms"
DB_USER = "Hd4AZn:NlSpH"
DB_PASSWORD = "8&0+6849Mx#S"

try:
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()

    print("Renaming project → projects...")
    cur.execute("ALTER TABLE IF EXISTS project RENAME TO projects;")
    conn.commit()

    print("✓ Done")

    cur.close()
    conn.close()
except Exception as e:
    print(f"✗ Error: {e}")
