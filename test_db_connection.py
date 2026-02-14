#!/usr/bin/env python3
"""Test database connectivity to 192.168.2.3:5433"""
import psycopg2
import sys

def test_connection():
    """Test connection to PostgreSQL database"""
    host = "192.168.2.3"
    port = "5433"
    database = "kevsrobots_cms"
    user = "Hd4AZn:NlSpH"  # Note: username contains a colon
    password = "8&0+6849Mx#S"  # Special characters: & + #

    print(f"Testing connection to {host}:{port}/{database} as user '{user}'...")
    print("-" * 60)

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5
        )

        print("✓ Connection successful!")

        # Test a simple query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✓ PostgreSQL version: {version}")

        # Check current user and database
        cur.execute("SELECT current_user, current_database();")
        current_user, current_db = cur.fetchone()
        print(f"✓ Connected as: {current_user}")
        print(f"✓ Database: {current_db}")

        cur.close()
        conn.close()

        return True

    except psycopg2.OperationalError as e:
        print(f"✗ Connection failed!")
        print(f"Error: {e}")
        print("\nPossible causes:")
        print("1. PostgreSQL is not running on the server")
        print("2. PostgreSQL is not listening on 0.0.0.0:5433")
        print("3. pg_hba.conf does not allow connections from your IP")
        print("4. Firewall is blocking port 5433")
        print("5. Incorrect username/password")
        return False

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
