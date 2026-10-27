import sys
import sqlite3
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('output/nutrition_master.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print('Tables in DB:', tables)

print('\n=== Users ===')
cursor.execute("SELECT id, name, email, google_id, is_onboarded, created_at FROM users WHERE id >= 150")
users = cursor.fetchall()
for u in users:
    print('User:', u)

print('\n=== User Preferences ===')
cursor.execute("SELECT user_id, preference_type, value FROM user_preferences WHERE user_id >= 150")
prefs = cursor.fetchall()
for p in prefs:
    print('Pref:', p)

if 'profiles' in tables:
    print('\n=== Profiles ===')
    cursor.execute("SELECT * FROM profiles WHERE user_id >= 150")
    profs = cursor.fetchall()
    for pr in profs:
        print('Profile:', pr)

conn.close()
