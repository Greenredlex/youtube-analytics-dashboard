import pandas as pd
import os
import isodate  # For parsing ISO duration
import pytz  # For timezone support

def process_video_data(video_data, csv_file_path):
    """
    Process video data and save to CSV.
    Handles merging with existing data and updating stats for existing videos.
    """
    # Handle empty data case
    if not video_data:
        print("No new video data to process")
        return pd.DataFrame() if not os.path.exists(csv_file_path) else pd.read_csv(csv_file_path)

    # Convert video data to DataFrame
    new_data = pd.DataFrame(video_data)
    
    # Load existing data if file exists
    if os.path.exists(csv_file_path):
        existing_data = pd.read_csv(csv_file_path)
        print(f"Loaded {len(existing_data)} existing videos from CSV")
    else:
        existing_data = pd.DataFrame()
        print("No existing CSV file found, creating new one")

    # Ensure required columns exist in new data
    required_columns = ['video_id', 'video_title', 'channel_id', 'channel_title', 
                        'published_at', 'views', 'likes', 'thumbnail_url', 'duration']
    
    for column in required_columns:
        if column not in new_data.columns:
            if column == 'channel_title' and 'channelTitle' in new_data.columns:
                # Fix common API response naming inconsistency
                new_data['channel_title'] = new_data['channelTitle']
            elif column == 'video_title' and 'title' in new_data.columns:
                # Fix common API response naming inconsistency
                new_data['video_title'] = new_data['title']
            else:
                # Create empty column if missing
                new_data[column] = None

    # Convert ISO 8601 duration to seconds for easier analysis
    if 'duration' in new_data.columns:
        new_data['duration_seconds'] = new_data['duration'].apply(
            lambda x: int(isodate.parse_duration(str(x)).total_seconds()) 
            if x and pd.notna(x) and str(x).startswith('PT') else None
        )

    # Make sure published_at is in datetime format with timezone
    if 'published_at' in new_data.columns:
        new_data['published_at'] = pd.to_datetime(new_data['published_at'], errors='coerce', utc=True)

    # Ensure existing_data has all required columns and proper datetime format
    if not existing_data.empty:
        for column in required_columns:
            if column not in existing_data.columns:
                existing_data[column] = None
        
        if 'duration' in existing_data.columns and 'duration_seconds' not in existing_data.columns:
            # Convert duration to seconds in existing data too
            existing_data['duration_seconds'] = existing_data['duration'].apply(
                lambda x: int(isodate.parse_duration(str(x)).total_seconds())
                if x and pd.notna(x) and str(x).startswith('PT') else None
            )
            
        # Make sure published_at is in datetime format with timezone
        if 'published_at' in existing_data.columns:
            existing_data['published_at'] = pd.to_datetime(existing_data['published_at'], errors='coerce', utc=True)
    
    # Check for duplicates based on video ID
    if not existing_data.empty:
        # Filter out videos that already exist in the dataset
        new_videos = new_data[~new_data['video_id'].isin(existing_data['video_id'])]
        
        # For videos that exist in both datasets, update their views/likes
        existing_video_ids = set(existing_data['video_id'])
        updated_videos = new_data[new_data['video_id'].isin(existing_video_ids)]
        
        if not updated_videos.empty:
            print(f"Updating details for {len(updated_videos)} existing videos")
            for _, row in updated_videos.iterrows():
                video_id = row['video_id']
                # Find the index in existing data
                idx = existing_data.index[existing_data['video_id'] == video_id].tolist()[0]
                
                # Update view count and likes
                if 'views' in row and pd.notna(row['views']):
                    existing_data.at[idx, 'views'] = row['views']
                if 'likes' in row and pd.notna(row['likes']):
                    existing_data.at[idx, 'likes'] = row['likes']
        
        print(f"Found {len(new_videos)} new videos to add")
        # Combine existing data with new videos
        updated_data = pd.concat([existing_data, new_videos], ignore_index=True)
    else:
        updated_data = new_data
        print(f"Adding {len(new_data)} videos to new dataset")

    # Save updated data to CSV
    updated_data.to_csv(csv_file_path, index=False)
    print(f"Saved {len(updated_data)} videos to CSV")
    
    return updated_data

def convert_date_str(date_str):
    """
    Convert a date string from the format '2024-04-15T09:04:24Z'
    to '2024-04-15 09:04:24+00:00'. If the date string is already in
    the target format, return it as-is.
    """
    from datetime import datetime
    try:
        dt = datetime.strptime(str(date_str), '%Y-%m-%dT%H:%M:%SZ')
        return dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
    except ValueError:
        # If conversion fails (e.g. the date is already converted), return it unchanged.
        return date_str
