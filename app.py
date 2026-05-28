import streamlit as st
import psycopg2
import bcrypt
import os
import PyPDF2
import docx
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
.job-card { background: white; border-radius: 15px; padding: 20px; margin: 10px 0; transition: transform 0.3s; }
.job-card:hover { transform: translateY(-5px); }
.loading-spinner { text-align: center; padding: 50px; }
</style>
""", unsafe_allow_html=True)

# Database connection
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

# Extract text from uploaded files
def extract_text_from_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return ""
    
    file_type = uploaded_file.type
    try:
        if file_type == "text/plain":
            return uploaded_file.read().decode("utf-8")
        elif file_type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        else:
            return ""
    except Exception as e:
        st.warning(f"Could not extract text from file: {e}")
        return ""

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            skills TEXT,
            cv_text TEXT,
            cv_filename TEXT,
            created_at TIMESTAMP
        )
    """)
    
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
    
    cur.execute("SELECT COUNT(*) FROM jobs")
    if cur.fetchone()[0] == 0:
        sample_jobs = [
            ("Administrative Officer", "Home Affairs", "communication management excel organization", "N$180,000 - N$240,000", "Windhoek", "Mid-Level", "Manage administrative tasks and coordinate office operations"),
            ("IT Support Technician", "Technology", "computer networking troubleshooting windows linux", "N$200,000 - N$300,000", "Windhoek", "Entry-Level", "Provide technical support and maintain computer systems"),
            ("Policy Analyst", "Justice", "research writing analysis policy critical thinking", "N$250,000 - N$350,000", "Windhoek", "Senior-Level", "Develop policies and conduct research"),
            ("Finance Assistant", "Finance", "accounting excel budgeting reporting bookkeeping", "N$160,000 - N$220,000", "Windhoek", "Entry-Level", "Process financial transactions and prepare reports"),
            ("Social Worker", "Health", "counseling case management outreach empathy", "N$190,000 - N$260,000", "Various", "Mid-Level", "Provide social services and community support"),
            ("HR Officer", "Public Service", "recruitment training employee relations payroll", "N$200,000 - N$280,000", "Windhoek", "Mid-Level", "Manage recruitment and HR administration"),
            ("Data Analyst", "Planning", "data analysis statistics excel reporting python", "N$220,000 - N$320,000", "Windhoek", "Mid-Level", "Analyze data and create reports for decision making"),
        ]
        for job in sample_jobs:
            cur.execute("INSERT INTO jobs (title, department, keywords, salary, location, level, description) VALUES (%s,%s,%s,%s,%s,%s,%s)", job)
    
    conn.commit()
    cur.close()
    conn.close()

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
                with st.spinner("Logging in..."):
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
                            st.success("✅ Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid email or password")
                    except Exception as e:
                        st.error(f"Login error: {e}")
        
        with tab2:
            name = st.text_input("Full Name", key="signup_name")
            email2 = st.text_input("Email", key="signup_email")
            pwd = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
            skills = st.text_area("Your Skills (comma separated)", key="signup_skills", placeholder="e.g., communication, management, excel, research")
            cv_file = st.file_uploader("Upload your CV (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"], key="signup_cv")
            
            if st.button("Create Account", key="signup_btn"):
                if pwd != confirm:
                    st.error("❌ Passwords don't match")
                elif not name or not email2:
                    st.error("❌ Please fill all required fields")
                else:
                    with st.spinner("Creating account..."):
                        cv_text = extract_text_from_uploaded_file(cv_file)
                        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("INSERT INTO users (email, password, full_name, skills, cv_text, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                                       (email2, hashed.decode(), name, skills, cv_text, datetime.now()))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success("✅ Account created! Please login above.")
                        except Exception as e:
                            st.error("❌ Email already exists or error occurred")
        
        st.markdown("</div>", unsafe_allow_html=True)

# MAIN APP
else:
    with st.sidebar:
        st.image("https://flagcdn.com/w320/na.png", width=100)
        st.markdown(f"### 👋 Welcome, {st.session_state.user_name}!")
        st.markdown("---")
        
        menu = st.radio("📋 Navigation", ["🏠 Dashboard", "💼 Vacancies", "📝 My Applications", "👤 Profile", "🚪 Logout"], key="menu")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s", (st.session_state.user_id,))
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            st.metric("📄 Applications", count)
        except:
            st.metric("📄 Applications", 0)
    
    # Dashboard
    if menu == "🏠 Dashboard":
        st.header("📊 Your Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Upload Your CV")
            uploaded_cv = st.file_uploader("Choose file (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"], key="dashboard_cv")
            
            if uploaded_cv:
                with st.spinner("Processing your CV..."):
                    cv_text = extract_text_from_uploaded_file(uploaded_cv)
                    if cv_text:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("UPDATE users SET cv_text=%s, cv_filename=%s WHERE id=%s", 
                                       (cv_text, uploaded_cv.name, st.session_state.user_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.user_cv = cv_text
                            st.success(f"✅ CV '{uploaded_cv.name}' uploaded and analyzed successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving CV: {e}")
                    else:
                        st.error("Could not extract text from file. Please paste text below.")
            
            st.caption("Or paste your CV text below:")
            cv_text_input = st.text_area("CV Text", value=st.session_state.user_cv, height=150, key="cv_input")
            if st.button("💾 Save CV Text", key="save_cv"):
                st.session_state.user_cv = cv_text_input
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET cv_text=%s WHERE id=%s", (cv_text_input, st.session_state.user_id))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("✅ CV text saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col2:
            st.subheader("📊 Your Statistics")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM applications WHERE user_id=%s", (st.session_state.user_id,))
                app_count = cur.fetchone()[0]
                cur.execute("SELECT AVG(match_score) FROM applications WHERE user_id=%s", (st.session_state.user_id,))
                avg_score = cur.fetchone()[0] or 0
                cur.close()
                conn.close()
                
                st.metric("Total Applications", app_count)
                st.metric("Average Match Score", f"{int(avg_score)}%")
            except:
                st.metric("Total Applications", 0)
                st.metric("Average Match Score", "0%")
        
        if st.session_state.user_cv:
            st.markdown("---")
            st.subheader("🎯 AI-Powered Job Recommendations")
            st.caption("Based on your CV and skills, here are jobs that match your profile:")
            
            with st.spinner("Analyzing your CV..."):
                try:
                    conn = get_db_connection()
                    jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
                    conn.close()
                    
                    for _, job in jobs.iterrows():
                        score = match_score(st.session_state.user_cv, job['keywords'])
                        
                        if score >= 70:
                            badge = "🟢 High Match - Strongly Recommended"
                            color = "green"
                        elif score >= 40:
                            badge = "🟡 Medium Match - Consider Applying"
                            color = "orange"
                        else:
                            badge = "🔴 Low Match - Build Skills First"
                            color = "red"
                        
                        st.markdown(f"""
                        <div class='job-card'>
                            <h3>{job['title']}</h3>
                            <p><strong>🏢 Department:</strong> {job['department']}</p>
                            <p><strong>💰 Salary:</strong> {job['salary']}</p>
                            <p><strong>📍 Location:</strong> {job['location']}</p>
                            <p><strong>📊 AI Match Score:</strong> <span style='color:{color};'>{score}%</span> {badge}</p>
                            <div style="background: #e0e0e0; border-radius: 10px; height: 10px;">
                                <div style="background: linear-gradient(95deg, #667eea, #764ba2); width: {score}%; height: 10px; border-radius: 10px;"></div>
                            </div>
                            <p><strong>🔑 Required Skills:</strong> {job['keywords']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_btn1, col_btn2, col_btn3 = st.columns([2,1,2])
                        with col_btn2:
                            if st.button(f"Apply Now", key=f"dash_apply_{job['id']}"):
                                with st.spinner("Submitting application..."):
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
                                            st.success(f"✅ Successfully applied for {job['title']}!")
                                        else:
                                            st.warning("⚠️ You already applied for this job")
                                        cur.close()
                                        conn.close()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                except Exception as e:
                    st.error(f"Error loading jobs: {e}")
        else:
            st.info("💡 **Get Started:** Upload your CV above to receive personalized job recommendations!")
    
    # Vacancies
    elif menu == "💼 Vacancies":
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
                    <p><strong>🏢 Department:</strong> {job['department']}</p>
                    <p><strong>💰 Salary:</strong> {job['salary']}</p>
                    <p><strong>📍 Location:</strong> {job['location']}</p>
                    <p><strong>📈 Level:</strong> {job['level']}</p>
                    <p><strong>📝 Description:</strong> {job['description']}</p>
                    <p><strong>🔑 Required Skills:</strong> {job['keywords']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Apply for this position", key=f"vac_apply_{job['id']}"):
                    with st.spinner("Submitting application..."):
                        try:
                            score = match_score(st.session_state.user_cv, job['keywords']) if st.session_state.user_cv else 50
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
                                st.warning("⚠️ You already applied for this job")
                            cur.close()
                            conn.close()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error loading vacancies: {e}")
    
    # My Applications
    elif menu == "📝 My Applications":
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
                        status_icon = "⏳ Pending Review"
                        status_color = "orange"
                    elif app['status'] == "Approved":
                        status_icon = "✅ Approved"
                        status_color = "green"
                    else:
                        status_icon = "❌ Not Selected"
                        status_color = "red"
                    
                    st.markdown(f"""
                    <div class='job-card'>
                        <h3>{app['title']}</h3>
                        <p><strong>🏢 Department:</strong> {app['department']}</p>
                        <p><strong>📅 Applied:</strong> {app['applied_date'][:10]}</p>
                        <p><strong>📊 AI Match Score:</strong> {app['match_score']}%</p>
                        <p><strong>📌 Status:</strong> <span style='color:{status_color};'>{status_icon}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading applications: {e}")
    
    # Profile
    elif menu == "👤 Profile":
        st.header("👤 Your Profile")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT full_name, email, skills, cv_filename FROM users WHERE id=%s", (st.session_state.user_id,))
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Personal Information")
                new_name = st.text_input("Full Name", value=user_data[0], key="profile_name")
                st.info(f"📧 Email: {user_data[1]}")
                new_skills = st.text_area("Your Skills", value=user_data[2] or "", height=100, key="profile_skills")
                
                if st.button("💾 Update Profile", key="update_profile"):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("UPDATE users SET full_name=%s, skills=%s WHERE id=%s",
                                   (new_name, new_skills, st.session_state.user_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.session_state.user_name = new_name
                        st.success("✅ Profile updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            with col2:
                st.subheader("Upload New CV")
                st.caption(f"Current CV: {user_data[3] or 'Not uploaded'}")
                new_cv = st.file_uploader("Choose file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], key="profile_cv")
                if new_cv:
                    with st.spinner("Processing CV..."):
                        cv_text = extract_text_from_uploaded_file(new_cv)
                        if cv_text:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("UPDATE users SET cv_text=%s, cv_filename=%s WHERE id=%s", 
                                           (cv_text, new_cv.name, st.session_state.user_id))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.session_state.user_cv = cv_text
                                st.success(f"✅ CV '{new_cv.name}' uploaded!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error loading profile: {e}")
    
    # Logout
    elif menu == "🚪 Logout":
        for key in ['logged_in', 'user_id', 'user_name', 'user_cv']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()