import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import os
from config.settings import API_KEY, CSV_FILE_PATH

def get_fetch_strategy():
    """
    Determine the fetch strategy based on existing data.
    Returns:
    - fetch_needed: Boolean indicating if fetch is needed
    - from_date: The date from which to fetch videos
    - max_results: Maximum number of results to fetch per channel
    """
    # Default strategy (full fetch)
    fetch_needed = True
    from_date = (datetime.now() - timedelta(days=365)).isoformat() + 'Z'  # One year ago
    max_results = 250  # Maximum allowed by YouTube API
    
    # Check if data file exists
    if not os.path.exists(CSV_FILE_PATH):
        return fetch_needed, from_date, max_results
    
    try:
        # Load existing data
        df = pd.read_csv(CSV_FILE_PATH)
        
        # If no data or missing required columns, do a full fetch
        if df.empty or 'published_at' not in df.columns or 'channel_id' not in df.columns:
            return fetch_needed, from_date, max_results
        
        # Convert published_at to datetime (use utc=True to ensure timezone aware)
        df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
        
        # Drop rows with invalid dates
        df = df.dropna(subset=['published_at'])
        
        if df.empty:
            return fetch_needed, from_date, max_results
            
        # Get the most recent video date
        latest_date = df['published_at'].max()
        
        # Ensure today is timezone-aware to match latest_date
        today = datetime.now(latest_date.tzinfo)
        
        # Calculate days since the most recent video
        days_since_latest = (today - latest_date).days
        print(f"Latest video date: {latest_date}, Days since: {days_since_latest}")
        
        # Strategy based on recency of data
        if days_since_latest <= 1:
            # If we have data from today, no need to fetch
            fetch_needed = False
            return fetch_needed, None, None
            
        elif days_since_latest <= 7:
            # If data is within the last week, just get recent videos
            from_date = (today - timedelta(days=14)).isoformat()  # 2 weeks ago for overlap
            # Remove microseconds and add Z for UTC
            from_date = from_date.split('.')[0] + 'Z'
            max_results = 10  # Reduced number to save quota
            
        elif days_since_latest <= 30:
            # If data is within a month, get videos from the last month
            from_date = (today - timedelta(days=45)).isoformat()  # 1.5 months for overlap
            # Remove microseconds and add Z for UTC
            from_date = from_date.split('.')[0] + 'Z'
            max_results = 25  # Medium number to balance coverage and quota
        else:
            # Full fetch but adjust the date based on the oldest video we have
            from_date = (today - timedelta(days=365)).isoformat()  # One year ago
            # Remove microseconds and add Z for UTC
            from_date = from_date.split('.')[0] + 'Z'
            
        print(f"Strategy: days_since_latest={days_since_latest}, fetch_needed={fetch_needed}, from_date={from_date}, max_results={max_results}")
        return fetch_needed, from_date, max_results
        
    except Exception as e:
        print(f"Error determining fetch strategy: {str(e)}")
        # If any error occurs, fall back to full fetch
        return fetch_needed, from_date, max_results

def fetch_top_youtubers_videos(channel_ids, published_after=None, max_results=5, max_pages=3):
    """
    Fetch videos from a list of YouTube channels published after the specified date.
    Returns additional data including video_id, channel_id, thumbnail_url and more.
    
    Parameters:
    - channel_ids: List of YouTube channel IDs
    - published_after: Date filter for videos
    - max_results: Maximum results per page (YouTube limits to 50)
    - max_pages: Maximum number of pages to fetch per channel
    """
    # Check if we need to fetch based on existing data
    fetch_needed, from_date, results_per_channel = get_fetch_strategy()
    
    if not fetch_needed:
        print("Skipping API fetch as data is up to date")
        return pd.DataFrame()  # Return empty DataFrame to indicate no new data needed
        
    # Use provided params or ones from strategy
    published_after = published_after if published_after else from_date
    max_results_per_page = min(50, results_per_channel if results_per_channel else max_results)
    total_max_results = results_per_channel
    
    print(f"Fetching videos from {published_after} with max_results={total_max_results} per channel")
    
    videos = []
    api_errors = []
    
    for channel_id in channel_ids:
        videos_fetched = 0
        next_page_token = None
        page_count = 0
        
        # Continue fetching pages until we hit limits
        while (videos_fetched < total_max_results and 
               page_count < max_pages and 
               (page_count == 0 or next_page_token is not None)):
            try:
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "key": API_KEY,
                    "channelId": channel_id,
                    "part": "snippet",
                    "order": "date",
                    "maxResults": max_results_per_page,
                    "publishedAfter": published_after,
                    "type": "video"
                }
                
                # Add page token for pagination if it exists
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Get next page token if available
                next_page_token = data.get("nextPageToken")
                
                if 'items' in data and data['items']:
                    items_count = len(data['items'])
                    videos_fetched += items_count
                    page_count += 1
                    
                    print(f"Found {items_count} videos for channel {channel_id} (page {page_count}, total {videos_fetched})")
                    
                    for item in data['items']:
                        video = {
                            'video_id': item['id']['videoId'],
                            'channel_id': channel_id,
                            'video_title': item['snippet']['title'],
                            'channel_title': item['snippet']['channelTitle'],
                            'published_at': item['snippet']['publishedAt'],
                            'description': item['snippet']['description'],
                            'thumbnail_url': item['snippet']['thumbnails']['high']['url'] if 'high' in item['snippet']['thumbnails'] else item['snippet']['thumbnails']['default']['url']
                        }
                        videos.append(video)
                    
                    # If no next page token, we've reached the end
                    if not next_page_token:
                        print(f"No more pages available for channel {channel_id}")
                        break
                        
                    # If we've reached our desired number of videos, stop
                    if videos_fetched >= total_max_results:
                        print(f"Reached maximum videos limit ({total_max_results}) for channel {channel_id}")
                        break
                else:
                    print(f"No videos found for channel {channel_id} on page {page_count + 1}")
                    if 'error' in data:
                        error_msg = f"API Error for channel {channel_id}: {data['error']['message']}"
                        print(error_msg)
                        api_errors.append(error_msg)
                    break
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed for channel {channel_id} (page {page_count + 1}): {str(e)}"
                print(error_msg)
                api_errors.append(error_msg)
                break
    
    if api_errors:
        st.error("YouTube API Errors:")
        for error in api_errors:
            st.error(error)
    
    return pd.DataFrame(videos) if videos else pd.DataFrame()

def fetch_video_views_and_details(video_ids):
    """
    Fetch view counts, likes, and duration for a list of video IDs.
    Returns a dictionary mapping video IDs to their stats.
    """
    if not video_ids:
        print("No video IDs provided to fetch details")
        return {}
        
    video_details = {}
    api_errors = []
    
    # Process in batches of 50 (API limit)
    for i in range(0, len(video_ids), 50):
        try:
            batch = video_ids[i:i+50]
            id_str = ','.join(batch)
            
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "key": API_KEY,
                "id": id_str,
                "part": "statistics,contentDetails"  # Include contentDetails for duration
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()  # Will raise exception for 4XX/5XX responses
            data = response.json()
            
            if 'items' in data:
                print(f"Fetched details for {len(data['items'])} videos")
                for item in data['items']:
                    video_id = item['id']
                    stats = {}
                    
                    # Get view count and likes
                    if 'statistics' in item:
                        if 'viewCount' in item['statistics']:
                            stats['views'] = int(item['statistics']['viewCount'])
                        else:
                            stats['views'] = 0
                            
                        if 'likeCount' in item['statistics']:
                            stats['likes'] = int(item['statistics']['likeCount'])
                        else:
                            stats['likes'] = 0
                    
                    # Get video duration
                    if 'contentDetails' in item and 'duration' in item['contentDetails']:
                        stats['duration'] = item['contentDetails']['duration']  # ISO 8601 duration format
                    
                    video_details[video_id] = stats
            else:
                print(f"No details found for batch of videos")
                if 'error' in data:
                    error_msg = f"API Error: {data['error']['message']}"
                    print(error_msg)
                    api_errors.append(error_msg)
                    
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed for video details: {str(e)}"
            print(error_msg)
            api_errors.append(error_msg)
    
    if api_errors:
        st.error("YouTube API Errors (video details):")
        for error in api_errors:
            st.error(error)
    
    return video_details