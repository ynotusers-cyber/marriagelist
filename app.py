import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

DB = "seeru.db"

# ---------------- DATABASE ---------------- #

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS functions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        date TEXT
    );

    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        place TEXT,
        mobile TEXT
    );

    CREATE TABLE IF NOT EXISTS received(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        function_id INTEGER,
        amount REAL,
        mode TEXT
    );

    CREATE TABLE IF NOT EXISTS given(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        event_name TEXT,
        event_date TEXT,
        amount REAL,
        mode TEXT,
        notes TEXT
    );
    """)

    conn.commit()
    conn.close()


init_db()

# ---------------- SIDEBAR ---------------- #

st.sidebar.title("🎁 Seeru Book")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "People",
        "Add Gift Received",
        "Record Gift Returned",
        "Functions"
    ]
)

# ---------------- DASHBOARD ---------------- #

if page == "Dashboard":

    st.title("📊 Dashboard")

    conn = get_db()

    total_received = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM received"
    ).fetchone()[0]

    total_given = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM given"
    ).fetchone()[0]

    total_contacts = conn.execute(
        "SELECT COUNT(*) FROM contacts"
    ).fetchone()[0]

    returned = conn.execute(
        "SELECT COUNT(DISTINCT contact_id) FROM given"
    ).fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Received", f"₹{total_received:,.0f}")
    c2.metric("Total Returned", f"₹{total_given:,.0f}")
    c3.metric("People", total_contacts)
    c4.metric("Returned Count", returned)

    progress = 0
    if total_contacts > 0:
        progress = returned / total_contacts

    st.progress(progress)

# ---------------- PEOPLE ---------------- #

if page == "People":

    st.title("👥 People")

    conn = get_db()

    rows = conn.execute("""
    SELECT c.id,c.name,c.place,c.mobile,
    COALESCE(SUM(r.amount),0) as received,
    COALESCE((SELECT SUM(g.amount) FROM given g WHERE g.contact_id=c.id),0) as given
    FROM contacts c
    LEFT JOIN received r ON r.contact_id=c.id
    GROUP BY c.id
    ORDER BY c.name
    """).fetchall()

    data = []

    for r in rows:

        balance = r["received"] - r["given"]

        data.append({
            "Name": r["name"],
            "Place": r["place"],
            "Mobile": r["mobile"],
            "Received": r["received"],
            "Returned": r["given"],
            "Balance": balance
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True)

# ---------------- ADD RECEIVED ---------------- #

if page == "Add Gift Received":

    st.title("⬇️ Add Gift Received")

    conn = get_db()

    name = st.text_input("Name")
    place = st.text_input("Place")
    mobile = st.text_input("Mobile")

    functions = conn.execute(
        "SELECT id,title FROM functions ORDER BY date DESC"
    ).fetchall()

    func_map = {f["title"]: f["id"] for f in functions}

    if len(func_map) == 0:
        st.warning("Add a function first.")
    else:

        func_name = st.selectbox(
            "Function",
            list(func_map.keys())
        )

        func_id = func_map[func_name]

        amount = st.number_input("Amount ₹", min_value=1)

        mode = st.selectbox(
            "Mode",
            ["CASH", "GPay", "PhonePe", "NEFT"]
        )

        if st.button("Save Gift"):

            cur = conn.execute(
                "INSERT INTO contacts(name,place,mobile) VALUES (?,?,?)",
                (name, place, mobile)
            )

            cid = cur.lastrowid

            conn.execute("""
            INSERT INTO received(contact_id,function_id,amount,mode)
            VALUES (?,?,?,?)
            """,(cid,func_id,amount,mode))

            conn.commit()

            st.success("Gift saved successfully!")

# ---------------- RETURN GIFT ---------------- #

if page == "Record Gift Returned":

    st.title("⬆️ Record Gift Returned")

    conn = get_db()

    people = conn.execute(
        "SELECT id,name FROM contacts ORDER BY name"
    ).fetchall()

    people_map = {p["name"]: p["id"] for p in people}

    if len(people_map) == 0:

        st.warning("No people available yet.")

    else:

        person_name = st.selectbox(
            "Select Person",
            list(people_map.keys())
        )

        person_id = people_map[person_name]

        totals = conn.execute("""
        SELECT
        COALESCE((SELECT SUM(amount) FROM received WHERE contact_id=?),0),
        COALESCE((SELECT SUM(amount) FROM given WHERE contact_id=?),0)
        """,(person_id,person_id)).fetchone()

        received = totals[0]
        given = totals[1]
        balance = received - given

        c1,c2,c3 = st.columns(3)

        c1.metric("Received",f"₹{received:,.0f}")
        c2.metric("Returned",f"₹{given:,.0f}")
        c3.metric("Balance",f"₹{balance:,.0f}")

        st.subheader("Enter Return")

        event = st.text_input("Their Function")

        event_date = st.date_input("Event Date",date.today())

        amount = st.number_input("Returned Amount ₹",min_value=1)

        mode = st.selectbox("Mode",["CASH","GPay","PhonePe","NEFT"])

        notes = st.text_input("Notes")

        if st.button("Save Return"):

            conn.execute("""
            INSERT INTO given(contact_id,event_name,event_date,amount,mode,notes)
            VALUES (?,?,?,?,?,?)
            """,(person_id,event,event_date,amount,mode,notes))

            conn.commit()

            st.success("Return saved!")

        st.subheader("Return History")

        history = conn.execute("""
        SELECT event_name,event_date,amount,mode
        FROM given
        WHERE contact_id=?
        ORDER BY id DESC
        """,(person_id,)).fetchall()

        for h in history:

            st.write(
                f"₹{h['amount']} — {h['event_name']} ({h['event_date']}) [{h['mode']}]"
            )

# ---------------- FUNCTIONS ---------------- #

if page == "Functions":

    st.title("📅 Functions")

    conn = get_db()

    title = st.text_input("Function Name")

    fdate = st.date_input("Date")

    if st.button("Add Function"):

        conn.execute(
            "INSERT INTO functions(title,date) VALUES (?,?)",
            (title,fdate)
        )

        conn.commit()

        st.success("Function added!")

    st.subheader("Existing Functions")

    funcs = conn.execute(
        "SELECT title,date FROM functions ORDER BY date DESC"
    ).fetchall()

    for f in funcs:
        st.write(f["title"], " — ", f["date"])