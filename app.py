import streamlit as st
from programs.youtube import show_youtube_data
from programs.analytics import show_analytics
from programs.shortsinpact import show_shortsinpact
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)

# Initialize session state for settings that persist across pages
if 'filter_short_videos' not in st.session_state:
    st.session_state['filter_short_videos'] = False

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a page", ["YouTube Data", "Advanced Analytics", "Shorts Impact"])

# Global filters (applied to both pages)
if page == "Advanced Analytics":
    st.session_state['filter_short_videos'] = st.sidebar.toggle(
        "Filter out shorts", 
        value=st.session_state['filter_short_videos'],
        help="When enabled, videos shorter than 1 minute will be hidden"
    )

# Display selected page
if page == "YouTube Data":
    show_youtube_data()
elif page == "Shorts Impact":
    show_shortsinpact()
else:
    show_analytics()