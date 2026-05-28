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
            ("Administrative Officer", "Home Affairs", "communication management excel organization", "N$180k-N$240k", "Windhoek", "Mid", "Admin tasks"),
            ("IT Technician", "Technology", "computer networking troubleshooting windows", "N$200k-N$300k", "Windhoek", "Entry", "Technical support"),
            ("Policy Analyst", "Justice", "research writing analysis policy", "N$250k-N$350k", "Windhoek", "Senior", "Policy development"),
            ("Finance Assistant", "Finance", "accounting excel budgeting reporting", "N$160k-N$220k", "Windhoek", "Entry", "Financial processing"),
            ("Social Worker", "Health", "counseling case management outreach", "N$190k-N$260k", "Various", "Mid", "Social services"),
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
            email1 = st.text_input("Email", key="login_email")
            password1 = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_btn"):
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT id, email, password, full_name, cv_text FROM users WHERE email=%s", (email1,))
                    user = cur.fetchone()
                    cur.close()
                    conn.close()
                    if user and bcrypt.checkpw(password1.encode(), user[2].encode()):
                        st.session_state.logged_in = True
                        st.session_state.user_id = user[0]
                        st.session_state.user_name = user[3]
                        st.session_state.user_cv = user[4] or ""
                        st.success("Logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Login error: {e}")
        
        with tab2:
            name = st.text_input("Full Name", key="signup_name")
            email2 = st.text_input("Email", key="signup_email")
            pwd = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
            skills = st.text_area("Your Skills (comma separated)", key="signup_skills")
            
            if st.button("Sign Up", key="signup_btn"):
                if pwd != confirm:
                    st.error("Passwords don't match")
                elif name and email2:
                    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO users (email, password, full_name, skills, created_at) VALUES (%s,%s,%s,%s,%s)",
                                   (email2, hashed.decode(), name, skills, datetime.now()))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Account created! Please login.")
                    except Exception as e:
                        st.error("Email already exists or error occurred")
                else:
                    st.error("Please fill all fields")
        
        st.markdown("</div>", unsafe_allow_html=True)

# MAIN APP (when logged in)
else:
    # Sidebar
    with st.sidebar:
        st.image("https://flagcdn.com/w320/na.png", width=100)
        st.write(f"Welcome **{st.session_state.user_name}**")
        st.markdown("---")
        
        menu = st.radio("Menu", ["Dashboard", "Vacancies", "My Applications", "Logout"], key="menu")
        
        # Get application count
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s", (st.session_state.user_id,))
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            st.metric("Applications", count)
        except:
            st.metric("Applications", 0)
    
    # Dashboard
    if menu == "Dashboard":
        st.header("📊 Your Dashboard")
        
        st.subheader("📄 Upload Your CV for AI Recommendations")
        cv = st.text_area("Paste your CV text here", value=st.session_state.user_cv, height=150, key="cv_input")
        
        if st.button("💾 Save CV", key="save_cv"):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE users SET cv_text=%s WHERE id=%s", (cv, st.session_state.user_id))
                conn.commit()
                cur.close()
                conn.close()
                st.session_state.user_cv = cv
                st.success("CV saved! Getting recommendations...")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving CV: {e}")
        
        if st.session_state.user_cv:
            st.subheader("🎯 AI-Powered Job Recommendations")
            
            try:
                conn = get_db_connection()
                jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
                conn.close()
                
                for _, job in jobs.iterrows():
                    score = match_score(st.session_state.user_cv, job['keywords'])
                    
                    if score >= 70:
                        badge = "🟢 High Match"
                    elif score >= 40:
                        badge = "🟡 Medium Match"
                    else:
                        badge = "🔴 Low Match"
                    
                    st.markdown(f"""
                    <div class='job-card'>
                        <h3>{job['title']}</h3>
                        <p><strong>Department:</strong> {job['department']}</p>
                        <p><strong>Salary:</strong> {job['salary']}</p>
                        <p><strong>Location:</strong> {job['location']}</p>
                        <p><strong>Match Score:</strong> {score}% {badge}</p>
                        <div style="background: #e0e0e0; border-radius: 10px; height: 10px;">
                            <div style="background: linear-gradient(95deg, #667eea, #764ba2); width: {score}%; height: 10px; border-radius: 10px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Apply for {job['title']}", key=f"dash_apply_{job['id']}"):
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s AND job_id=%s", 
                                       (st.session_state.user_id, job['id']))
                            if cur.fetchone()[0] == 0:
                                cur.execute("INSERT INTO applications (user_id, job_id, applied_date, status, match_score) VALUES (%s,%s,%s,%s,%s)",
                                           (st.session_state.user_id, job['id'], datetime.now(), "Under Review", score))
                                conn.commit()
                                st.balloons()
                                st.success(f"✅ Applied for {job['title']}!")
                            else:
                                st.warning("You already applied for this job")
                            cur.close()
                            conn.close()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Application error: {e}")
            except Exception as e:
                st.error(f"Error loading jobs: {e}")
        else:
            st.info("💡 Upload your CV above to get personalized job recommendations!")
    
    # Vacancies
    elif menu == "Vacancies":
        st.header("💼 All Government Vacancies")
        
        try:
            conn = get_db_connection()
            jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
            conn.close()
            
            search = st.text_input("🔍 Search jobs by title or department", key="search")
            
            for _, job in jobs.iterrows():
                if search and search.lower() not in job['title'].lower() and search.lower() not in job['department'].lower():
                    continue
                
                st.markdown(f"""
                <div class='job-card'>
                    <h3>{job['title']}</h3>
                    <p><strong>Department:</strong> {job['department']}</p>
                    <p><strong>Salary:</strong> {job['salary']}</p>
                    <p><strong>Location:</strong> {job['location']}</p>
                    <p><strong>Level:</strong> {job['level']}</p>
                    <p><strong>Required Skills:</strong> {job['keywords']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Apply", key=f"vac_apply_{job['id']}"):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s AND job_id=%s", 
                                   (st.session_state.user_id, job['id']))
                        if cur.fetchone()[0] == 0:
                            cur.execute("INSERT INTO applications (user_id, job_id, applied_date, status, match_score) VALUES (%s,%s,%s,%s,%s)",
                                       (st.session_state.user_id, job['id'], datetime.now(), "Under Review", 50))
                            conn.commit()
                            st.balloons()
                            st.success(f"✅ Applied for {job['title']}!")
                        else:
                            st.warning("You already applied for this job")
                        cur.close()
                        conn.close()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Application error: {e}")
        except Exception as e:
            st.error(f"Error loading vacancies: {e}")
    
    # My Applications
    elif menu == "My Applications":
        st.header("📝 Your Job Applications")
        
        try:
            conn = get_db_connection()
            apps = pd.read_sql_query("""
                SELECT j.title, j.department, a.applied_date, a.status, a.match_score 
                FROM applications a 
                JOIN jobs j ON a.job_id=j.id 
                WHERE a.user_id=%s
                ORDER BY a.applied_date DESC
            """, conn, params=(st.session_state.user_id,))
            conn.close()
            
            if len(apps) == 0:
                st.info("📭 You haven't applied for any jobs yet. Browse vacancies and apply!")
            else:
                for _, app in apps.iterrows():
                    if app['status'] == "Under Review":
                        status_icon = "⏳ Pending"
                    elif app['status'] == "Approved":
                        status_icon = "✅ Approved"
                    else:
                        status_icon = "❌ Rejected"
                    
                    st.markdown(f"""
                    <div class='job-card'>
                        <h3>{app['title']}</h3>
                        <p><strong>Department:</strong> {app['department']}</p>
                        <p><strong>Applied:</strong> {app['applied_date'][:10]}</p>
                        <p><strong>Match Score:</strong> {app['match_score']}%</p>
                        <p><strong>Status:</strong> {status_icon}</p>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading applications: {e}")
    
    # Logout
    elif menu == "Logout":
        for key in ['logged_in', 'user_id', 'user_name', 'user_cv']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()