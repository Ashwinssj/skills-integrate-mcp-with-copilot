"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sqlite3
from pathlib import Path
from typing import Dict, List

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = Path(__file__).parent.parent / "data.db"

# Seed data used on first run to populate the database
INITIAL_ACTIVITIES: Dict[str, Dict] = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed initial data if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT,
            schedule TEXT,
            max_participants INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_name TEXT,
            email TEXT,
            UNIQUE(activity_name, email)
        )
        """
    )

    # Seed if empty
    cur.execute("SELECT COUNT(1) as c FROM activities")
    row = cur.fetchone()
    if row and row[0] == 0:
        for name, data in INITIAL_ACTIVITIES.items():
            cur.execute(
                "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                (name, data["description"], data["schedule"], data["max_participants"]),
            )
            for email in data.get("participants", []):
                try:
                    cur.execute(
                        "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
                        (name, email),
                    )
                except sqlite3.IntegrityError:
                    pass

    conn.commit()
    conn.close()


def get_all_activities() -> Dict[str, Dict]:
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities")
    activities: Dict[str, Dict] = {}
    rows = cur.fetchall()
    for r in rows:
        cur.execute("SELECT email FROM participants WHERE activity_name = ?", (r["name"],))
        participants = [p[0] for p in cur.fetchall()]
        activities[r["name"]] = {
            "description": r["description"],
            "schedule": r["schedule"],
            "max_participants": r["max_participants"],
            "participants": participants,
        }
    conn.close()
    return activities


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


# Initialize database and seed data
init_db()


@app.get("/activities")
def get_activities():
    return get_all_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities WHERE name = ?", (activity_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if already signed up
    cur.execute("SELECT 1 FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Student is already signed up")

    # Enforce capacity
    cur.execute("SELECT COUNT(1) FROM participants WHERE activity_name = ?", (activity_name,))
    count = cur.fetchone()[0]
    if count >= row["max_participants"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Activity is full")

    try:
        cur.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (activity_name, email))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Student already registered")
    conn.close()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities WHERE name = ?", (activity_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    cur.execute("SELECT id FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    found = cur.fetchone()
    if not found:
        conn.close()
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    cur.execute("DELETE FROM participants WHERE id = ?", (found[0],))
    conn.commit()
    conn.close()
    return {"message": f"Unregistered {email} from {activity_name}"}
