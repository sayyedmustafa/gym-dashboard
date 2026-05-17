import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import urllib.parse

# --- Page Config ---
st.set_page_config(
    page_title="Gym Manager",
    page_icon="💪",
    layout="centered"
)

# --- Custom CSS ---
st.markdown("""
<style>
    /* Clean mobile layout */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Radio buttons horizontal style */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        gap: 8px;
        flex-wrap: wrap;
    }

    div[role="radiogroup"] label {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 6px 16px;
        cursor: pointer;
        font-size: 13px;
    }

    div[role="radiogroup"] label:has(input:checked) {
        background: #6366f1;
        border-color: #6366f1;
        color: white;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px;
    }

    /* Divider spacing */
    hr {
        margin: 0.5rem 0 !important;
    }

    /* Table styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# --- Load Data from Google Sheets ---
@st.cache_data(ttl=300)
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
        message = (
            f"Hi {name}! Your membership at our gym expired on "
            f"{end_date.strftime('%d %b %Y')}. We miss you! "
            f"Renew now and get back on track. Call us to continue your fitness journey 💪"
        )
    else:
        message = (
            f"Hi {name}! Just a reminder that your gym membership expires on "
            f"{end_date.strftime('%d %b %Y')} ({days_remaining} days remaining). "
            f"Renew early and keep your fitness streak going! 💪"
        )
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/91{phone}?text={encoded}"


# --- Load Data ---
try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load data. Make sure the sheet is public. Error: {e}")
    st.stop()

today = datetime.now()

# --- Plan Prices ---
plan_prices = {
    "1 Month": 1500,
    "3 Months": 4000,
    "6 Months": 7000
}
df['revenue'] = df['plan'].map(plan_prices).fillna(0)

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown("## 💪 Gym Member Dashboard")
st.markdown(f"*Last synced: {today.strftime('%d %b %Y, %I:%M %p')}*")
st.divider()

FORM_URL = "https://forms.gle/To1jE3pm65zQh8mM9"

st.link_button(
    "➕ Add New Member",
    FORM_URL,
    use_container_width=True
)

# ─────────────────────────────────────────
# NAVIGATION — replaces sidebar
# ─────────────────────────────────────────
show_section = st.radio(
    "Select View",
    ["📊 Overview", "⚠️ Expiring", "📋 All Members"],
    horizontal=True,
    label_visibility="collapsed"
)

# ─────────────────────────────────────────
# PLAN FILTER
# ─────────────────────────────────────────
with st.expander("🔽 Filter by Plan", expanded=False):
    plan_filter = st.multiselect(
        "Membership Plan",
        options=df['plan'].unique(),
        default=df['plan'].unique(),
        label_visibility="collapsed"
    )

filtered_df = df[df['plan'].isin(plan_filter)] if plan_filter else df.copy()

st.divider()

# ─────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────
total_members = len(filtered_df)
active_members = len(filtered_df[filtered_df['days_remaining'] >= 0])
expiring_7days = len(filtered_df[
    (filtered_df['days_remaining'] >= 0) &
    (filtered_df['days_remaining'] <= 7)
])
expired_members = len(filtered_df[filtered_df['days_remaining'] < 0])
estimated_revenue = filtered_df['revenue'].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total Members", total_members)
col2.metric("Active", active_members)
col3.metric(
    "Expiring This Week",
    expiring_7days,
    delta=f"-{expiring_7days} urgent" if expiring_7days > 0 else None,
    delta_color="inverse"
)

col4, col5 = st.columns(2)
col4.metric(
    "Lapsed Members",
    expired_members,
    delta=f"{expired_members} need followup" if expired_members > 0 else None,
    delta_color="inverse"
)
col5.metric("Membership Value", f"₹{estimated_revenue:,.0f}")

st.divider()

# ─────────────────────────────────────────
# OVERVIEW SECTION
# ─────────────────────────────────────────
if show_section == "📊 Overview":

    # Plan distribution pie
    plan_counts = filtered_df['plan'].value_counts().reset_index()
    plan_counts.columns = ['Plan', 'Members']
    fig1 = px.pie(
        plan_counts, names='Plan', values='Members',
        title='Members by Plan',
        color_discrete_sequence=['#6366f1', '#10b981', '#f59e0b'],
        hole=0.4
    )
    fig1.update_layout(height=280, margin=dict(t=40, b=0))
    st.plotly_chart(fig1, use_container_width=True)

    # Status bar chart
    status_data = pd.DataFrame({
        'Status': ['Active Members', 'Expiring This Week', 'Lapsed Members'],
        'Count': [
            len(filtered_df[filtered_df['days_remaining'] > 7]),
            expiring_7days,
            expired_members
        ]
    })
    fig2 = px.bar(
        status_data, x='Status', y='Count',
        title='Member Status',
        color='Status',
        color_discrete_sequence=['#10b981', '#f59e0b', '#ef4444'],
        text='Count'
    )
    fig2.update_layout(height=260, margin=dict(t=40, b=0), showlegend=False)
    fig2.update_traces(textposition='outside')
    st.plotly_chart(fig2, use_container_width=True)

    # Monthly joins
    filtered_df['join_month'] = filtered_df['start_date'].dt.strftime('%b %Y')
    monthly = filtered_df.groupby('join_month').size().reset_index(name='New Members')
    fig3 = px.bar(
        monthly, x='join_month', y='New Members',
        title='New Members by Month',
        color_discrete_sequence=['#6366f1'],
        text='New Members'
    )
    fig3.update_layout(height=260, margin=dict(t=40, b=0))
    fig3.update_traces(textposition='outside')
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────
# EXPIRING MEMBERS SECTION
# ─────────────────────────────────────────
elif show_section == "⚠️ Expiring":

    urgent = filtered_df[
        (filtered_df['days_remaining'] >= 0) &
        (filtered_df['days_remaining'] <= 7)
    ].sort_values('days_remaining')

    expired = filtered_df[
        filtered_df['days_remaining'] < 0
    ].sort_values('days_remaining', ascending=False)

    # --- Expiring This Week ---
    st.markdown(f"### 🔴 Expiring This Week — {len(urgent)} members")
    if len(urgent) == 0:
        st.success("No members expiring this week!")
    else:
        for _, row in urgent.iterrows():
            wa_link = generate_whatsapp_link(
                row['phone'], row['name'],
                row['days_remaining'], row['end_date']
            )
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"📱 {row['phone']}  ·  ⏳ {int(row['days_remaining'])} days left  ·  📅 {row['end_date'].strftime('%d %b %Y')}")
                with c2:
                    st.link_button("📲 WhatsApp", wa_link, use_container_width=True)
            st.divider()

    # --- Lapsed ---
    st.markdown(f"### ⚫ Lapsed Members — {len(expired)} members")
    if len(expired) == 0:
        st.success("No lapsed members!")
    else:
        for _, row in expired.iterrows():
            wa_link = generate_whatsapp_link(
                row['phone'], row['name'],
                row['days_remaining'], row['end_date']
            )
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"📱 {row['phone']}  ·  ❌ Expired {abs(int(row['days_remaining']))} days ago")
                with c2:
                    st.link_button("📲 WhatsApp", wa_link, use_container_width=True)
            st.divider()

# ─────────────────────────────────────────
# ALL MEMBERS SECTION
# ─────────────────────────────────────────
elif show_section == "📋 All Members":

    st.markdown("### 📋 All Members")
    search = st.text_input("🔍 Search by name or phone", placeholder="Type name or number...")

    display_df = filtered_df.copy()
    if search:
        display_df = display_df[
            display_df['name'].str.contains(search, case=False, na=False) |
            display_df['phone'].astype(str).str.contains(search, na=False)
        ]

    display_df['Status'] = display_df['days_remaining'].apply(
        lambda x: "🔴 Expiring This Week" if 0 <= x <= 7
        else ("✅ Active" if x > 7
        else "⚫ Expired")
    )

    display_df['Days'] = display_df['days_remaining'].apply(
        lambda x: f"{int(x)} days left" if x >= 0 else f"Expired {abs(int(x))}d ago"
    )

    show_cols = display_df[[
        'name', 'phone', 'plan',
        'end_date', 'Status', 'Days'
    ]].copy()

    show_cols['end_date'] = show_cols['end_date'].dt.strftime('%d %b %Y')
    show_cols.columns = ['Name', 'Phone', 'Plan', 'Expiry Date', 'Status', 'Days']

    st.dataframe(show_cols, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────
st.divider()
st.caption("Powered by Rexus Agency · Auto-refreshes every 5 minutes")