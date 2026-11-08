def find_user(conn, name):
    cur = conn.execute("SELECT name FROM users WHERE name = ?", (name,))
    return [r[0] for r in cur.fetchall()]
