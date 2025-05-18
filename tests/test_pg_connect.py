import psycopg2
import os
import sys

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

print(f"psycopg2 version: {psycopg2.__version__}")
print(f"Python default encoding: {sys.getdefaultencoding()}")
print(f"stdin encoding: {sys.stdin.encoding}")
print(f"stdout encoding: {sys.stdout.encoding}")

# Connection parameters
dbname = 'pdfshell_db'
user = 'pdfshell_user'
password = 'pdfshell_pass'  # Re-type this manually
host = 'db'
port = '5432'

# Verify parameter encoding
print("Parameter bytes:")
print(f"dbname: {dbname.encode('utf-8')}")
print(f"user: {user.encode('utf-8')}")
print(f"password: {password.encode('utf-8')}")
print(f"host: {host.encode('utf-8')}")
print(f"port: {port.encode('utf-8')}")

dsn_params = {
    "dbname": dbname,
    "user": user,
    "password": password,
    "host": host,
    "port": port,
}

# Test 1: Keyword arguments
print("\n--- Test 1: Keyword arguments ---")
print(f"Attempting with params: {dsn_params}")
try:
    conn = psycopg2.connect(**dsn_params)
    print("Connection successful!")
    conn.close()
except psycopg2.Error as e:
    print(f"PostgreSQL Error: {e}")
    print(f"Error code: {e.pgcode}")
    print(f"Error details: {e.pgerror}")
except Exception as e:
    print(f"General Error: {e}")

# Test 2: DSN string
manual_dsn = f"dbname='{dbname}' user='{user}' password='{password}' host='{host}' port='{port}'"
print("\n--- Test 2: DSN string ---")
print(f"Attempting with DSN: {repr(manual_dsn)}")
try:
    conn = psycopg2.connect(manual_dsn)
    print("Connection successful!")
    conn.close()
except psycopg2.Error as e:
    print(f"PostgreSQL Error: {e}")
    print(f"Error code: {e.pgcode}")
    print(f"Error details: {e.pgerror}")
except Exception as e:
    print(f"General Error: {e}")