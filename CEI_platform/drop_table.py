import sqlite3

# Replace with your actual DB file name
conn = sqlite3.connect("your_database_file.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS agent_intelligence;")
conn.commit()

print("Table 'agent_intelligence' dropped.")
conn.close()
