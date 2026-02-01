"""
Database Export Utility

Exports all SQLite tables to CSV files for verification and reporting.
"""

import sqlite3
import csv
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DATABASE_FILE

def export_table(cursor, table_name, filename):
    """Write table contents to CSV file with headers."""
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        column_names = [description[0] for description in cursor.description]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(column_names)
            writer.writerows(rows)
            
        print(f"✓ Exported {len(rows)} rows from '{table_name}' to '{filename}'")
        
    except Exception as e:
        print(f"✗ Failed to export '{table_name}': {e}")

def main():
    print("=" * 60)
    print("DATABASE EXPORT UTILITY")
    print(f"Source: {DATABASE_FILE}")
    print("=" * 60)
    
    if not os.path.exists(DATABASE_FILE):
        print(f"[ERROR] Database file '{DATABASE_FILE}' not found.")
        print("Run the BDB server first to initialize the database.")
        return

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        tables = ['users', 'accounts', 'transfers', 'sessions', 'audit_logs']
        
        for table in tables:
            export_table(cursor, table, f"{table}.csv")
            
        conn.close()
        print("-" * 60)
        print("Export completed successfully.")
        
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

if __name__ == "__main__":
    main()
