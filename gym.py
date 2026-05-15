import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --- Page Config ---
st.set_page_config(
    page_title="Gym Manager",
    page_icon="💪",
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #0f3460;
        text-align: center;
    }
    .expiry-urgent {
        background-color: #ff4b4b22;
        border-left: 4px solid #ff4b4b;
        padding: 10px;
        border-radius: 4px;
        margin: 5px 0;
    }
    .expiry-soon {
        background-color: #ffa50022;
        border-left: 4px solid #ffa500;
        padding: 10px;
        border-radius: 4px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Load Data from Google Sheets ---
@st.cache_data(ttl=300)  # Refresh every 5 minutes
def load_data():
    SHEET_ID = "1UNM6EI7Al5xOMm-opaWRJ6mIZf1bTRCyX1h49KzEZgM"
    SHEET_NAME = "Sheet1"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    today = pd.Timestamp.now().normalize()
    df['days_remaining'] = (df['end_date'] - today).dt.days
    return df

# --- WhatsApp Message Generator ---
def generate_whatsapp_link(phone, name, days_remaining, end_date):
    if days_remaining < 0:
        message = f"Hi {name}! Your membership at our gym expired on {end_date.strftime('%d %b %Y')}. We miss you! Renew now and get back on track. Call us to continue your fitness journey 💪"
    else:
        message = f"Hi {name}! Just a reminder that your gym membership expires on {end_date.strftime('%d %b %Y')} ({days_remaining} days remaining). Renew early and keep your fitness streak going! 💪"
    
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/91{phone}?text={encoded}"

# --- Load ---
try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load data. Check your Sheet ID and make sure the sheet is public. Error: {e}")
    st.stop()

today = datetime.now()

# --- Header ---
st.markdown("## 💪 Gym Member Dashboard")
gym_name = st.sidebar.text_input("Gym Name", value="GymCity")
st.markdown(f"### {gym_name}")
st.markdown(f"*Last updated: {today.strftime('%d %b %Y, %I:%M %p')}*")
st.divider()

# --- Sidebar ---
st.sidebar.markdown("### Filters")
plan_filter = st.sidebar.multiselect(
    "Membership Plan",
    options=df['plan'].unique(),
    default=df['plan'].unique()
)
show_section = st.sidebar.radio(
    "View",
    ["Overview", "Expiring Members", "All Members"]
)

filtered_df = df[df['plan'].isin(plan_filter)]

# --- KPI Metrics ---
total_members = len(filtered_df)
active_members = len(filtered_df[filtered_df['days_remaining'] >= 0])
expiring_7days = len(filtered_df[(filtered_df['days_remaining'] >= 0) & (filtered_df['days_remaining'] <= 7)])
expired_members = len(filtered_df[filtered_df['days_remaining'] < 0])

plan_prices = {
    "1 Month": 1500,
    "3 Months": 4000,
    "6 Months": 7000
}

filtered_df['revenue'] = filtered_df['plan'].map(plan_prices)

estimated_revenue = filtered_df['revenue'].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Members", total_members)
col2.metric("Active Members", active_members, delta=None)
col3.metric("Expiring in 7 Days", expiring_7days, delta=f"-{expiring_7days} this week" if expiring_7days > 0 else None, delta_color="inverse")
col4.metric("Expired (Lapsed)", expired_members, delta=f"{expired_members} need followup" if expired_members > 0 else None, delta_color="inverse")
col5.metric("Estimated Revenue", f"₹{estimated_revenue:,}")

st.divider()

# --- OVERVIEW SECTION ---
if show_section == "Overview":
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Plan distribution
        plan_counts = filtered_df['plan'].value_counts().reset_index()
        plan_counts.columns = ['Plan', 'Members']
        fig1 = px.pie(
            plan_counts, names='Plan', values='Members',
            title='Members by Plan Type',
            color_discrete_sequence=['#6366f1', '#10b981', '#f59e0b'],
            hole=0.4
        )
        fig1.update_layout(height=300, margin=dict(t=40, b=0))
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_right:
        # Member status breakdown
        status_data = {
            'Status': ['Active Members', 'Expiring This Week', 'Expired Members'],
            'Count': [
                len(filtered_df[filtered_df['days_remaining'] > 7]),
                expiring_7days,
                expired_members
            ]
        }
        fig2 = px.bar(
            pd.DataFrame(status_data),
            x='Status', y='Count',
            title='Member Status Breakdown',
            color='Status',
            color_discrete_sequence=['#10b981', '#f59e0b', '#ef4444', '#6b7280']
        )
        fig2.update_layout(height=300, margin=dict(t=40, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Monthly joins trend
    filtered_df['join_month'] = filtered_df['start_date'].dt.strftime('%b %Y')
    monthly = filtered_df.groupby('join_month').size().reset_index(name='New Members')
    fig3 = px.bar(
        monthly, x='join_month', y='New Members',
        title='New Members by Month',
        color_discrete_sequence=['#6366f1']
    )
    fig3.update_layout(height=280, margin=dict(t=40, b=0))
    st.plotly_chart(fig3, use_container_width=True)

# --- EXPIRING MEMBERS SECTION ---
elif show_section == "Expiring Members":
    
    # Urgent — expiring in 7 days
    urgent = filtered_df[
        (filtered_df['days_remaining'] >= 0) & 
        (filtered_df['days_remaining'] <= 7)
    ].sort_values('days_remaining')
    
    # Soon — expiring in 8-30 days
    soon = filtered_df[
        (filtered_df['days_remaining'] > 7) & 
        (filtered_df['days_remaining'] <= 30)
    ].sort_values('days_remaining')
    
    # Expired
    expired = filtered_df[
        filtered_df['days_remaining'] < 0
    ].sort_values('days_remaining', ascending=False)

    # --- Urgent ---
    st.markdown(f"### 🔴 Expiring This Week ({len(urgent)} members)")
    if len(urgent) == 0:
        st.success("No members expiring this week!")
    else:
        for _, row in urgent.iterrows():
            wa_link = generate_whatsapp_link(
                row['phone'], row['name'], 
                row['days_remaining'], row['end_date']
            )
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            col1.markdown(f"**{row['name']}**")
            col2.markdown(f"📱 {row['phone']}")
            col3.markdown(f"⏳ **{int(row['days_remaining'])} days left**")
            col4.markdown(f"[📲 Send WhatsApp]({wa_link})")
            st.divider()


    # --- Expired ---
    st.markdown(f"### ⚫ Lapsed Members ({len(expired)} members)")
    if len(expired) == 0:
        st.success("No lapsed members!")
    else:
        for _, row in expired.iterrows():
            wa_link = generate_whatsapp_link(
                row['phone'], row['name'],
                row['days_remaining'], row['end_date']
            )
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            col1.markdown(f"**{row['name']}**")
            col2.markdown(f"📱 {row['phone']}")
            col3.markdown(f"❌ Expired {abs(int(row['days_remaining']))} days ago")
            col4.markdown(f"[📲 Send WhatsApp]({wa_link})")
            st.divider()

# --- ALL MEMBERS SECTION ---
elif show_section == "All Members":
    st.markdown("### 📋 All Members")
    
    search = st.text_input("🔍 Search by name or phone")
    
    display_df = filtered_df.copy()
    if search:
        display_df = display_df[
            display_df['name'].str.contains(search, case=False) |
            display_df['phone'].astype(str).str.contains(search)
        ]
    
    display_df['Membership Status'] = display_df['days_remaining'].apply(
        lambda x: "🔴 Expiring Soon" if 0 <= x <= 7 
        else ("🟡 Expiring" if 7 < x <= 30 
        else ("✅ Active" if x > 30 
        else "⚫ Expired"))
    )
    
    display_df['Days Remaining'] = display_df['days_remaining'].apply(
        lambda x: f"{int(x)} days" if x >= 0 else f"Expired {abs(int(x))} days ago"
    )
    
    show_cols = display_df[[
        'member_id', 'name', 'phone', 'plan', 
        'start_date', 'end_date', 'Membership Status', 'Days Remaining'
    ]].copy()
    
    show_cols['start_date'] = show_cols['start_date'].dt.strftime('%d %b %Y')
    show_cols['end_date'] = show_cols['end_date'].dt.strftime('%d %b %Y')
    show_cols.columns = ['ID', 'Name', 'Phone', 'Plan', 'Start Date', 'End Date', 'Status', 'Days Remaining']
    
    st.dataframe(show_cols, use_container_width=True, hide_index=True)

st.divider()
st.caption("Built by [Your Name] · Auto-refreshes every 5 minutes · Data stored in Google Sheets")