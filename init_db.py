import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('warranty.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS bearings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bearing_code TEXT NOT NULL UNIQUE,
        sku TEXT NOT NULL,
        is_used INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS mechanics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        loyalty_points INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS installations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bearing_id INTEGER NOT NULL,
        mechanic_id INTEGER NOT NULL,
        location TEXT,
        install_date TEXT NOT NULL,
        warranty_expiry TEXT NOT NULL,
        FOREIGN KEY (bearing_id) REFERENCES bearings(id),
        FOREIGN KEY (mechanic_id) REFERENCES mechanics(id)
    )
''')

# Seed sample bearings (unused, ready to be verified/installed)
sample_bearings = [
    ('NBC-6205-2RS-00123', '6205-2RS'),
    ('NBC-6205-2RS-00124', '6205-2RS'),
    ('NBC-6308-ZZ-00891', '6308-ZZ'),
    ('NBC-6308-ZZ-00892', '6308-ZZ'),
    ('NBC-6002-2RS-00456', '6002-2RS'),
]
for code, sku in sample_bearings:
    cursor.execute(
        'INSERT OR IGNORE INTO bearings (bearing_code, sku) VALUES (?, ?)',
        (code, sku)
    )

# Seed sample mechanics with login credentials (demo passwords - fine for a portfolio project)
sample_mechanics = [
    ('Rajesh Kumar', 'rajesh', 'pass123'),
    ('Suresh Patel', 'suresh', 'pass123'),
    ('Amit Singh', 'amit', 'pass123'),
]
for name, username, password in sample_mechanics:
    cursor.execute('SELECT id FROM mechanics WHERE username = ?', (username,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO mechanics (name, username, password_hash) VALUES (?, ?, ?)',
            (name, username, generate_password_hash(password))
        )

# Seed one admin account
cursor.execute('SELECT id FROM admins WHERE username = ?', ('admin',))
if not cursor.fetchone():
    cursor.execute(
        'INSERT INTO admins (username, password_hash) VALUES (?, ?)',
        ('admin', generate_password_hash('admin123'))
    )

conn.commit()
conn.close()
print("Database initialized: warranty.db")
print(f"Seeded {len(sample_bearings)} bearings, {len(sample_mechanics)} mechanics, 1 admin.")
print("\nDemo login credentials:")
for name, username, password in sample_mechanics:
    print(f"  Mechanic - username: {username} / password: {password}  ({name})")
print("  Admin    - username: admin / password: admin123")
