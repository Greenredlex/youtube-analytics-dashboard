import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import re
import isodate
import pytz  # Add this import for timezone support
from utils.api_client import fetch_top_youtubers_videos, fetch_video_views_and_details
from utils.data_processor import process_video_data, convert_date_str
from config.settings import CHANNEL_IDS, CSV_FILE_PATH

def show_youtube_data():
    st.title("YouTube Analytics Dashboard")

    # Check if data file exists
    file_exists = os.path.exists(CSV_FILE_PATH)
    
    # Add a refresh button
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.subheader("YouTube Video Data")
    with col2:
        refresh = st.button("Refresh Data")

    # Show smart fetching status
    if file_exists:
        try:
            df = pd.read_csv(CSV_FILE_PATH)
            if 'published_at' in df.columns:
                # Use more flexible date parsing with errors='coerce' and make timezone aware
                df['published_at'] = df['published_at'].apply(convert_date_str)
                df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
                # Drop rows with invalid dates
                df = df.dropna(subset=['published_at'])
                
                if not df.empty:
                    latest_date = df['published_at'].max()
                    # Make now timezone-aware to match latest_date
                    now = datetime.now(pytz.UTC)
                    days_since_latest = (now - latest_date).days
                    
                    st.info(f"Database contains {len(df)} videos. Most recent video: {latest_date.strftime('%Y-%m-%d')} ({days_since_latest} days ago)")
                    
                    if days_since_latest <= 1:
                        st.success("Data is up to date (last video from today)")
        except Exception as e:
            st.error(f"Error reading existing data: {str(e)}")

    # Fetch new data if refresh is clicked or if the file doesn't exist
    if refresh or not file_exists:
        with st.spinner("Fetching latest video data from YouTube..."):
            # Set date for one year ago if forced refresh, otherwise use smart fetching
            # Make sure it's in a format compatible with the YouTube API
            one_year_ago = (datetime.now(pytz.UTC) - timedelta(days=365)).isoformat().split('.')[0] + 'Z'
            
            # Fetch video data from YouTube API (with forced refresh or smart fetching)
            videos_df = fetch_top_youtubers_videos(CHANNEL_IDS)
            
            if not videos_df.empty:
                st.success(f"Found {len(videos_df)} new videos")
                
                # Get views, likes and duration for each video
                video_ids = videos_df['video_id'].tolist()
                video_details = fetch_video_views_and_details(video_ids)
                
                # Add details to the dataframe
                for video_id in video_ids:
                    if video_id in video_details:
                        details = video_details[video_id]
                        index = videos_df.index[videos_df['video_id'] == video_id].tolist()[0]
                        
                        for key, value in details.items():
                            videos_df.at[index, key] = value
                
                # Process and save video data
                process_video_data(videos_df.to_dict('records'), CSV_FILE_PATH)
                st.success("Data updated successfully!")
            elif file_exists:
                st.info("No new videos found or up to date. Using existing data.")
            else:
                st.error("No videos found and no existing data. Check API key and channel IDs.")
                return
    
    # Load the video data from CSV
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        if df.empty:
            st.error("The data file exists but contains no data.")
            return
            
        # Clean up the published_at dates - make sure they're all timezone aware
        if 'published_at' in df.columns:
            df['published_at'] = df['published_at'].apply(convert_date_str)
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
            # Remove rows where date parsing completely failed
            if df['published_at'].isna().any():
                original_count = len(df)
                df = df.dropna(subset=['published_at'])
                if len(df) < original_count:
                    st.warning(f"Removed {original_count - len(df)} rows with invalid dates")
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Format and display data
    # Apply short video filter if enabled
    if st.session_state.get('filter_short_videos', False) and 'duration_seconds' in df.columns:
        original_count = len(df)
        df = df[df['duration_seconds'] >= 61]
        filtered_count = len(df)
        if filtered_count < original_count:
            st.info(f"Filtered out {original_count - filtered_count} videos under 60 seconds")
    
    # Function to format duration in a readable way
    def format_duration(seconds):
        if pd.isna(seconds):
            return "Unknown"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        
        if minutes > 0:
            return f"{minutes}:{remaining_seconds:02d}"
        else:
            return f"{remaining_seconds}s"

    # Display basic stats
    st.subheader("Channel Statistics")
    
    # Group by channel
    try:
        channel_stats = df.groupby('channel_title').agg(
            videos=('video_id', 'count'),
            total_views=('views', 'sum'),
            avg_views=('views', 'mean')
        ).reset_index()
        
        # Format the numbers for better readability
        channel_stats['total_views'] = channel_stats['total_views'].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "Unknown"
        )
        channel_stats['avg_views'] = channel_stats['avg_views'].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "Unknown"
        )
        
        st.dataframe(channel_stats)
    except Exception as e:
        st.error(f"Error generating channel statistics: {str(e)}")
    
    # Display the video data
    st.subheader("Video List")
    
    # Choose columns to display based on what's available
    available_cols = ['video_title', 'channel_title', 'published_at', 'views', 'likes']
    display_cols = [col for col in available_cols if col in df.columns]
    
    # Add duration column if any duration info is available
    if 'duration_seconds' in df.columns:
        df['duration_formatted'] = df['duration_seconds'].apply(format_duration)
        display_cols.append('duration_formatted')
    elif 'duration' in df.columns:
        # Try to extract duration in a readable format directly from the ISO duration
        df['duration_formatted'] = df['duration'].apply(
            lambda x: re.sub(r'PT|H|M|S', ' ', str(x)).strip().replace('  ', ':') if pd.notna(x) else "Unknown"
        )
        display_cols.append('duration_formatted')
    
    # Prepare dataframe for display
    try:
        if display_cols:
            display_df = df[display_cols].copy()
            
            # Format numbers
            if 'views' in display_df.columns:
                display_df['views'] = display_df['views'].apply(
                    lambda x: f"{int(x):,}" if pd.notna(x) else "Unknown"
                )
            if 'likes' in display_df.columns:
                display_df['likes'] = display_df['likes'].apply(
                    lambda x: f"{int(x):,}" if pd.notna(x) else "Unknown"
                )
                
            st.dataframe(display_df.sort_values('published_at', ascending=False))
        else:
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error displaying video list: {str(e)}")


if __name__ == "__main__":
    show_youtube_data()