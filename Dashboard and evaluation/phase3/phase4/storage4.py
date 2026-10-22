import json, sqlite3, time


class PlanStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS repair_plans(id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT, created_at REAL, status TEXT, selected TEXT, payload TEXT)""")
        self.db.commit()

    def save(self, plan, interaction=None) -> int:
        payload = dict(plan=plan.to_dict(), interaction=interaction.to_dict() if interaction else None)
        cur = self.db.execute("INSERT INTO repair_plans(agent_id,created_at,status,selected,payload) VALUES (?,?,?,?,?)",
                              (plan.agent_id, time.time(), plan.status, json.dumps(plan.selected), json.dumps(payload)))
        self.db.commit()
        return cur.lastrowid

    def get(self, pid):
        r = self.db.execute("SELECT payload FROM repair_plans WHERE id=?", (pid,)).fetchone()
        return json.loads(r[0]) if r else None

    def list(self, agent_id=None):
        q, a = "SELECT id,agent_id,status,selected FROM repair_plans", []
        if agent_id:
            q += " WHERE agent_id=?"; a.append(agent_id)
        return [dict(id=i, agent_id=g, status=s, selected=json.loads(x)) for i, g, s, x in self.db.execute(q + " ORDER BY id DESC", a)]
