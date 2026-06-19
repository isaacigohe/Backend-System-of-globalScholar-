import os
import psycopg2
from django.contrib.auth.hashers import make_password

# 1. Fetch your database URL directly from Render's environment
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    print("❌ ERROR: DATABASE_URL environment variable not found.")
    exit(1)

# 2. Define your login credentials
email = "isaac@gmail.com"
raw_password = "Secure1234"
hashed_password = make_password(raw_password)

try:
    # Connect directly to PostgreSQL
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Check if the user already exists in your custom users table
    cursor.execute("SELECT id FROM users_customuser WHERE email = %s;", (email,))
    user_exists = cursor.fetchone()

    if not user_exists:
        # Insert the superuser directly into your database schema
        insert_query = """
        INSERT INTO users_customuser (password, is_superuser, email, is_staff, is_active)
        VALUES (%s, True, %s, True, True);
        """
        cursor.execute(insert_query, (hashed_password, email))
        conn.commit()
        print("🚀 SUPERUSER CREATED SUCCESSFULLY VIA DIRECT SQL!")
    else:
        print("✅ Superuser already exists in the database.")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Database error encountered: {e}")