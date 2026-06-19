import os
import base64
import hashlib
import secrets
import psycopg2

# 1. Fetch your database URL directly from Render's environment
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    print("❌ ERROR: DATABASE_URL environment variable not found.")
    exit(1)

# 2. Define your login credentials
email = "isaac@gmail.com"
raw_password = "YourSecurePassword123!"

# 3. Generate a proper Django-compatible PBKDF2 SHA256 password hash
iterations = 870000  # Django 6.0 default iterations
salt = secrets.token_hex(6)  # Generate a random unique text salt
hash_bytes = hashlib.pbkdf2_hmac(
    'sha256', 
    raw_password.encode('utf-8'), 
    salt.encode('utf-8'), 
    iterations
)
encoded_hash = base64.b64encode(hash_bytes).decode('ascii').strip()
# Final string structure matching Django's layout: pbkdf2_sha256$iterations$salt$hash
hashed_password = f"pbkdf2_sha256${iterations}${salt}${encoded_hash}"

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
        print("🚀 SUPERUSER CREATED SUCCESSFULLY VIA PURE PYTHON SQL INJECTION!")
    else:
        print("✅ Superuser already exists in the database.")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Database error encountered: {e}")