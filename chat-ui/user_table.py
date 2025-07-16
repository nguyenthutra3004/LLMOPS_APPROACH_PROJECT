import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL using credentials from your .env file
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    user="postgres",
    password="12345678",
    database="postgres"
)

conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

# Create User table for Auth.js
cursor.execute("""
DROP TABLE IF EXISTS "User";
""")

cursor.close()
conn.close()

print("Auth.js tables created successfully!")