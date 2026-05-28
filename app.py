import streamlit as st
import psycopg2
import bcrypt
import os
from datetime import datetime
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Page config
st.set_page_config(page_title="Namibia Gov Jobs", page_icon="🇳🇦", layout="wide")

# Custom CSS
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
.login-box { background: white; border-radius: 20px; padding: 30px; }
.job-card { background: white; border-radius: 15px; padding: 20px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# Database connection
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            skills TEXT,
            cv_text TEXT,
            created_at TIMESTAMP
        )
    """)
    
    # Jobs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            title TEXT,
            department TEXT,
            keywords TEXT,
            salary TEXT,
            location TEXT,
            level TEXT,
            description TEXT
        )
    """)
    
    # Applications table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            job_id INTEGER,
            applied_date TIMESTAMP,
            status TEXT,
            match_score REAL
        )
    """)
    
    # Insert sample jobs
    cur.execute("SELECT COUNT(*) FROM jobs")
    if cur.fetchone()[0] == 0:
        sample_jobs = [
            ("Administrative Officer", "Home Affairs", "communication,management,excel,organization", "N$180k-N$240k", "Windhoek", "Mid", "Admin tasks"),
            ("IT Technician", "Technology", "computer,networking,troubleshooting,windows", "N$200k-N$300k", "Windhoek", "Entry", "Technical support"),
            ("Policy Analyst", "Justice", "research,writing,analysis,policy", "N$250k-N$350k", "Windhoek", "Senior", "Policy development"),
            ("Finance Assistant", "Finance", "accounting,excel,budgeting,reporting", "N$160k-N$220k", "Windhoek", "Entry", "Financial processing"),
        ]
        for job in sample_jobs:
            cur.execute("INSERT INTO jobs (title, department, keywords, salary, location, level, description) VALUES (%s,%s,%s,%s,%s,%s,%s)", job)
    
    conn.commit()
    cur.close()
    conn.close()

# Helper function
def match_score(cv, keywords):
    if not cv:
        return 50
    try:
        vectorizer = CountVectorizer()
        vectors = vectorizer.fit_transform([cv.lower(), keywords.lower()])
        return round(cosine_similarity(vectors[0], vectors[1])[0][0] * 100, 1)
    except:
        return 50

# Initialize
init_db()

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Header
st.markdown("<h1 style='text-align:center; color:white;'>🇳🇦 Namibia Government Job Portal</h1>", unsafe_allow_html=True)

# Login/Signup
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, email, password, full_name, cv_text FROM users WHERE email=%s", (email,))
                user = cur.fetchone()
                cur.close()
                conn.close()
                if user and bcrypt.checkpw(password.encode(), user[2].encode()):
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = user[3]
                    st.session_state.user_cv = user[4] or ""
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            skills = st.text_area("Your Skills")
            if st.button("Sign Up"):
                if pwd != confirm:
                    st.error("Passwords don't match")
                elif name and email:
                    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO users (email, password, full_name, skills, created_at) VALUES (%s,%s,%s,%s,%s)",
                                   (email, hashed.decode(), name, skills, datetime.now()))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Account created! Please login.")
                    except:
                        st.error("Email already exists")
        
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # Sidebar
    with st.sidebar:
        st.image("https://flagcdn.com/w320/na.png", width=100)
        st.write(f"Welcome **{st.session_state.user_name}**")
        menu = st.radio("Menu", ["Dashboard", "Vacancies", "My Apps", "Logout"])
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s", (st.session_state.user_id,))
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        st.metric("Applications", count)
    
    if menu == "Dashboard":
        st.header("📊 Dashboard")
        
        st.subheader("Upload Your CV")
        cv = st.text_area("Paste your CV text here", value=st.session_state.user_cv, height=150)
        if st.button("Save CV"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE users SET cv_text=%s WHERE id=%s", (cv, st.session_state.user_id))
            conn.commit()
            cur.close()
            conn.close()
            st.session_state.user_cv = cv
            st.success("CV saved!")
            st.rerun()
        
        if st.session_state.user_cv:
            st.subheader("🎯 AI Recommendations")
            conn = get_db_connection()
            jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
            conn.close()
            
            for _, job in jobs.iterrows():
                score = match_score(st.session_state.user_cv, job['keywords'])
                st.markdown(f"""
                <div class='job-card'>
                    <h3>{job['title']}</h3>
                    <p><strong>Department:</strong> {job['department']}</p>
                    <p><strong>Salary:</strong> {job['salary']}</p>
                    <p><strong>Match Score:</strong> {score}%</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Apply", key=f"dash_{job['id']}"):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s AND job_id=%s", 
                               (st.session_state.user_id, job['id']))
                    if cur.fetchone()[0] == 0:
                        cur.execute("INSERT INTO applications (user_id, job_id, applied_date, status, match_score) VALUES (%s,%s,%s,%s,%s)",
                                   (st.session_state.user_id, job['id'], datetime.now(), "Pending", score))
                        conn.commit()
                        st.balloons()
                        st.success(f"Applied for {job['title']}!")
                    else:
                        st.warning("Already applied")
                    cur.close()
                    conn.close()
                    st.rerun()
    
    elif menu == "Vacancies":
        st.header("💼 All Vacancies")
        conn = get_db_connection()
        jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
        conn.close()
        
        search = st.text_input("Search")
        for _, job in jobs.iterrows():
            if search and search.lower() not in job['title'].lower():
                continue
            st.markdown(f"""
            <div class='job-card'>
                <h3>{job['title']}</h3>
                <p><strong>Department:</strong> {job['department']}</p>
                <p><strong>Salary:</strong> {job['salary']}</p>
                <p><strong>Location:</strong> {job['location']}</p>
                <p><strong>Skills:</strong> {job['keywords']}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Apply", key=f"vac_{job['id']}"):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO applications (user_id, job_id, applied_date, status, match_score) VALUES (%s,%s,%s,%s,%s)",
                           (st.session_state.user_id, job['id'], datetime.now(), "Pending", 50))
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"Applied for {job['title']}!")
                st.rerun()
    
    elif menu == "My Apps":
        st.header("📝 Your Applications")
        conn = get_db_connection()
        apps = pd.read_sql_query("""
            SELECT j.title, j.department, a.applied_date, a.status, a.match_score 
            FROM applications a JOIN jobs j ON a.job_id=j.id 
            WHERE a.user_id=%s
        """, conn, params=(st.session_state.user_id,))
        conn.close()
        
        if len(apps) == 0:
            st.info("No applications yet")
        else:
            for _, app in apps.iterrows():
                st.markdown(f"""
                <div class='job-card'>
                    <h3>{app['title']}</h3>
                    <p><strong>Department:</strong> {app['department']}</p>
                    <p><strong>Applied:</strong> {app['applied_date'][:10]}</p>
                    <p><strong>Status:</strong> {app['status']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    elif menu == "Logout":
        for key in ['logged_in', 'user_id', 'user_name', 'user_cv']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()