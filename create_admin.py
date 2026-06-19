import os
import base64
import hashlib
import secrets
import psycopg2

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("❌ ERROR: DATABASE_URL environment variable not found.")
    exit(1)

email = "Ema@gmail.com"
raw_password = "Kisiwani@1234"

# Generate Django-compatible password hash
iterations = 870000  
salt = secrets.token_hex(6)  
hash_bytes = hashlib.pbkdf2_hmac(
    'sha256', 
    raw_password.encode('utf-8'), 
    salt.encode('utf-8'), 
    iterations
)
encoded_hash = base64.b64encode(hash_bytes).decode('ascii').strip()
hashed_password = f"pbkdf2_sha256${iterations}${salt}${encoded_hash}"

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # 1. First, find out exactly what your custom user table is named
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name LIKE '%user%' AND table_schema = 'public';
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    # Fallback default if custom checking doesn't find it
    target_table = "users_customuser"
    for t in tables:
        if "customuser" in t or "user" in t:
            target_table = t
            break

    print(f"🔍 Targeting user database table: {target_table}")

    # 2. Check if the entry already exists
    cursor.execute(f"SELECT id FROM {target_table} WHERE email = %s;", (email,))
    user_exists = cursor.fetchone()

    if not user_exists:
        # Insert admin user with EVERY backend flag set to true
        insert_query = f"""
        INSERT INTO {target_table} (password, is_superuser, email, is_staff, is_active)
        VALUES (%s, True, %s, True, True);
        """
        cursor.execute(insert_query, (hashed_password, email))
        conn.commit()
        print("🚀 NEW SUPERUSER ACCOUNT INJECTED SUCCESSFULLY!")
    else:
        # Overwrite the existing row to guarantee permissions and reset the password hash cleanly
        update_query = f"""
        UPDATE {target_table} 
        SET password = %s, is_superuser = True, is_staff = True, is_active = True 
        WHERE email = %s;
        """
        cursor.execute(update_query, (hashed_password, email))
        conn.commit()
        print("🔄 EXISTING USER FORCED TO ACTIVE SUPERUSER WITH NEW PASSWORD!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Database error encountered: {e}")