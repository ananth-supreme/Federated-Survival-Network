import sqlite3
conn = sqlite3.connect('fsn_mission.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM command_queue WHERE status='PENDING';")
rows = cursor.fetchall()
print(rows)
conn.close()
