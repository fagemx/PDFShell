import psycopg2
import os
import sys

# 嘗試強制 Python I/O 使用 UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

print(f"psycopg2 version: {psycopg2.__version__}")
print(f"Python default encoding: {sys.getdefaultencoding()}")
print(f"sys.stdin.encoding: {sys.stdin.encoding}")
print(f"sys.stdout.encoding: {sys.stdout.encoding}")
print(f"os.environ.get('PYTHONUTF8'): {os.environ.get('PYTHONUTF8')}") # 檢查 PYTHONUTF8

# 連接參數
dbname = 'pdfshell_db'
user = 'pdfshell_user'
password = 'pdfshell_pass'  # 我們將檢查這個密碼的位元組
port = '5432'

# 驗證參數的位元組表示
print("\n--- Parameter Byte Representations (UTF-8) ---")
try:
    print(f"dbname: {dbname.encode('utf-8')}")
    print(f"user: {user.encode('utf-8')}")
    print(f"password: {password.encode('utf-8')}") # 預期 b'pdfshell_pass'
    # host 將在每個測試中單獨編碼和列印
    print(f"port: {port.encode('utf-8')}")
except Exception as e:
    print(f"Error encoding parameters: {e}")


def attempt_connection(host_val: str, conn_password: str):
    print(f"\n--- Testing Connection with host='{host_val}' ---")
    print(f"host parameter byte representation: {host_val.encode('utf-8')}")
    
    dsn_params = {
        "dbname": dbname,
        "user": user,
        "password": conn_password,
        "host": host_val,
        "port": port,
    }
    print(f"Attempting with params: {dsn_params}")
    try:
        conn = psycopg2.connect(**dsn_params)
        print("Connection successful!")
        conn.close()
        return True
    except psycopg2.Error as e:
        print(f"PostgreSQL Error: {e}")
        if hasattr(e, 'pgcode') and e.pgcode: print(f"pgcode: {e.pgcode}")
        if hasattr(e, 'pgerror') and e.pgerror: print(f"pgerror: {e.pgerror}")
    except Exception as e:
        print(f"General Error: {e}")
    return False

# 測試 1: 使用 host='db' (原始嘗試，用於 Docker 內部網路)
attempt_connection(host_val='db', conn_password=password)

# 測試 2: 使用 host='localhost' (從主機連接到 Docker 映射連接埠的標準方式)
attempt_connection(host_val='localhost', conn_password=password)

# 測試 3: 使用 host='127.0.0.1' ( localhost 的 IP )
attempt_connection(host_val='127.0.0.1', conn_password=password)

print("\n--- End of tests ---") 