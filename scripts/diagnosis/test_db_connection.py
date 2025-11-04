#!/usr/bin/env python3
"""
Test PostgreSQL connection with different credential formats
"""

import sys
import getpass
from urllib.parse import quote, quote_plus
import psycopg2

def test_connection(host, port, database, username, password):
    """Test database connection with given credentials"""

    # Try different encodings
    encodings = {
        'Original': password,
        'URL Encoded (quote)': quote(password, safe=''),
        'URL Encoded (quote_plus)': quote_plus(password),
    }

    for encoding_name, encoded_password in encodings.items():
        print(f"\nTrying: {encoding_name}")
        print(f"Encoded password: {encoded_password}")

        # Try direct connection (not URL)
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password  # Use original password for direct connection
            )
            print(f"✅ SUCCESS with direct connection (not URL)")

            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"   PostgreSQL: {version.split(',')[0]}")

            cur.close()
            conn.close()

            # Show the correct DATABASE_URL format
            print(f"\n✅ Use this in your .env file:")
            print(f'DATABASE_URL="postgresql://{username}:{encoded_password}@{host}:{port}/{database}"')
            return True

        except psycopg2.OperationalError as e:
            print(f"❌ Failed: {e}")
            continue
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    return False

def main():
    print("=" * 60)
    print("PostgreSQL Connection Tester")
    print("=" * 60)
    print()

    # Get credentials
    print("Enter your PostgreSQL credentials:")
    print("(Press Ctrl+C to cancel)")
    print()

    try:
        host = input("Host [192.168.2.3]: ").strip() or "192.168.2.3"
        port = input("Port [5433]: ").strip() or "5433"
        database = input("Database [kevsrobots_cms]: ").strip() or "kevsrobots_cms"
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")

        print()
        print("Testing connection...")

        if test_connection(host, port, database, username, password):
            print("\n✅ Connection successful!")
            print("Update your app/.env with the DATABASE_URL shown above")
        else:
            print("\n❌ Could not connect with any encoding")
            print("\nPossible issues:")
            print("1. Wrong password")
            print("2. User doesn't exist")
            print("3. User doesn't have permission to access the database")
            print("\nTry connecting directly from the server:")
            print(f"  ssh your_user@{host}")
            print(f"  psql -h localhost -p {port} -U {username} -d {database}")

    except KeyboardInterrupt:
        print("\n\nCancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
