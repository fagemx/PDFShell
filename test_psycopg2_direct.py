# test_psycopg2_direct.py
import psycopg2
import os

print("--- Direkt psycopg2 Verbindungstest ---")

# Diese Werte sollten mit Ihren Einstellungen in settings.py übereinstimmen
# und den Werten, die Sie für sauber halten.
db_params = {
    'host': 'db',
    'dbname': 'pdfshell_db',
    'user': 'pdfshell_user',
    'password': 'pdfshell_pass',
    'port': '5432',
    'client_encoding': 'UTF8' # Explizit setzen, wie in Django settings
}

print(f"Verbindungsparameter für psycopg2.connect():")
for key, value in db_params.items():
    print(f"  {key}: '{value}' (Typ: {type(value)})")
    try:
        # Versuchen, den Wert als Bytes auszugeben, um verdächtige Zeichen zu sehen
        print(f"    Bytes (UTF-8): {value.encode('utf-8')}")
        print(f"    Bytes (Latin-1, zur Inspektion): {value.encode('latin-1', 'replace')}")
    except Exception as e:
        print(f"    Konnte Bytes nicht kodieren: {e}")


# Versuchen, PostgreSQL Umgebungsvariablen auszulesen, die psycopg2 beachten könnte
print("\nPotenziell relevante PostgreSQL Umgebungsvariablen:")
pg_env_vars = [
    'PGHOST', 'PGHOSTADDR', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD',
    'PGPASSFILE', 'PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS', 'PGAPPNAME',
    'PGSSLMODE', 'PGREQUIRESSL', 'PGSSLCOMPRESSION', 'PGSSLCERT',
    'PGSSLKEY', 'PGSSLROOTCERT', 'PGSSLCSR', 'PGKRBSRVNAME', 'PGGSSLIB',
    'PGCLIENTENCODING', 'PGDATESTYLE', 'PGTZ', 'PGGEQO', 'PGSYSCONFDIR',
    'PGLOCALEDIR', 'DATABASE_URL' # Auch DATABASE_URL prüfen
]
for var_name in pg_env_vars:
    var_value = os.getenv(var_name)
    if var_value is not None:
        print(f"  {var_name}: '{var_value}'")
        try:
            print(f"    Bytes (UTF-8): {var_value.encode('utf-8', 'replace')}")
            print(f"    Bytes (Latin-1, zur Inspektion): {var_value.encode('latin-1', 'replace')}")
        except Exception as e:
            print(f"    Konnte Bytes für {var_name} nicht kodieren: {e}")


conn = None
try:
    print("\nVersuche, Verbindung herzustellen mit psycopg2.connect()...")
    # conn = psycopg2.connect(**db_params) # Variante 1: Mit expliziten Parametern
    
    # Variante 2: Als DSN-String (ähnlicher zu DATABASE_URL, aber ohne dj_database_url)
    # Wir bauen den DSN-String manuell, um sicherzustellen, dass er sauber ist.
    # Achtung: Passwörter mit Sonderzeichen müssten hier URL-kodiert werden, aber 'pdfshell_pass' ist einfach.
    dsn_string = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}?client_encoding={db_params['client_encoding']}"
    print(f"Verwende DSN-String: {dsn_string}")
    conn = psycopg2.connect(dsn_string)


    print("Verbindung erfolgreich hergestellt!")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"PostgreSQL Version: {version}")
    cur.close()
except psycopg2.Error as e:
    print(f"psycopg2 Fehler: {e}")
    print(f"Fehlertyp: {type(e)}")
    if hasattr(e, 'pgcode'):
        print(f"PostgreSQL Fehlercode: {e.pgcode}")
    if hasattr(e, 'pgerror'):
        print(f"PostgreSQL Fehlermeldung: {e.pgerror}")
    # Wenn es ein UnicodeDecodeError ist, hat es möglicherweise keine pgcode/pgerror Attribute
    if isinstance(e, UnicodeDecodeError):
        print("Es ist ein UnicodeDecodeError aufgetreten.")
        # Hier könnten wir versuchen, e.object, e.start, e.end, e.reason auszugeben, falls verfügbar
        print(f"  Fehler beim Dekodieren von: {e.object if hasattr(e, 'object') else 'N/A'}")
        print(f"  Startposition: {e.start if hasattr(e, 'start') else 'N/A'}")
        print(f"  Endposition: {e.end if hasattr(e, 'end') else 'N/A'}")
        print(f"  Grund: {e.reason if hasattr(e, 'reason') else 'N/A'}")

except Exception as e_gen:
    print(f"Allgemeiner Python Fehler: {e_gen}")
    print(f"Fehlertyp: {type(e_gen)}")
finally:
    if conn:
        conn.close()
        print("Verbindung geschlossen.")

print("\n--- Test Ende ---") 