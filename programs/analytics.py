import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config.settings import CSV_FILE_PATH, CHANNEL_COLORS
from utils.data_processor import convert_date_str

# Add this function at the top of your file:

def display_weekly_videos(df, week_data):
    """Display videos for the selected week"""
    year_week = week_data['points'][0]['x']
    
    # Extract week number and year from the year_week string
    year, week_num = year_week.split('-W')
    year = int(year)
    week_num = int(week_num)
    
    # Filter videos for this week
    week_videos = df[
        (df['published_at'].dt.isocalendar().year == year) & 
        (df['published_at'].dt.isocalendar().week == week_num)
    ].sort_values('views', ascending=False)
    
    if week_videos.empty:
        st.warning(f"No videos found for week {year_week}")
        return
        
    st.subheader(f"Videos from {year_week}")
    st.write(f"{len(week_videos)} videos published this week")
    
    # Format the data for display
    display_df = week_videos.copy()
    display_df['published_at'] = display_df['published_at'].dt.strftime('%Y-%m-%d')
    display_df['views'] = display_df['views'].apply(lambda x: f"{int(x):,}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    if 'likes' in display_df.columns:
        display_df['likes'] = display_df['likes'].apply(lambda x: f"{int(x):,}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) else "Unknown")
    
    # Create columns for videos display with thumbnails if available
    for i, (_, row) in enumerate(display_df.iterrows()):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if 'thumbnail_url' in row and pd.notna(row['thumbnail_url']):
                try:
                    st.image(row['thumbnail_url'], width=200)
                except:
                    st.write("No thumbnail")
        
        with col2:
            st.markdown(f"**{row['video_title']}**")
            st.write(f"Channel: **{row['channel_title']}**")
            minutes = int(row['duration_seconds'] // 60)
            seconds = int(row['duration_seconds'] % 60)
            st.write(f"Published: {row['published_at']} (•) Views: {row['views']} (•)  Duration: {minutes}:{seconds:02d}")


def show_analytics():
    st.title("Advanced YouTube Analytics")
    
    # Load data
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        if df.empty:
            st.warning("No data available. Please generate YouTube data first.")
            return
    except FileNotFoundError:
        st.error("Data file not found. Please generate YouTube data first.")
        return
    
    # Check if required columns exist
    required_columns = ['video_id', 'video_title', 'channel_title', 'published_at', 'views']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns in data: {', '.join(missing_columns)}")
        return

    # Convert published_at to datetime and ensure it's timezone aware
    df['published_at'] = df['published_at'].apply(convert_date_str)
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)

    # Handle NaT values if any conversion failed
    df = df.dropna(subset=['published_at'])
    
    # Apply short video filter if enabled
    if st.session_state.get('filter_short_videos', False) and 'duration_seconds' in df.columns:
        original_count = len(df)
        df = df[df['duration_seconds'] >= 61]
        filtered_count = len(df)

    
    # Add filters
    st.sidebar.header("Filters")
    
    # YouTuber filter
    youtubers = sorted(df['channel_title'].unique())
    

    
    def colorize_multiselect_options(colors: list[str]) -> None:
        rules = ""
        n_colors = len(colors)

        for i, color in enumerate(colors):
            rules += f""".stMultiSelect div[data-baseweb="select"] span[data-baseweb="tag"]:nth-child({n_colors}n+{i+1}){{background-color: {color};}}"""

        st.markdown(f"<style>{rules}</style>", unsafe_allow_html=True)
    

    selected_youtubers = st.sidebar.multiselect(
        "Select YouTubers",
        options=youtubers,
        default=youtubers[:3] if len(youtubers) > 3 else youtubers
    )

    colorize_multiselect_options([CHANNEL_COLORS[pg] for pg in selected_youtubers])

    if not selected_youtubers:  # If nothing selected, use all
        selected_youtubers = youtubers
    # Date range filter - Fix for the validation error
    try:
        min_date = df['published_at'].min().date()
        max_date = df['published_at'].max().date()
        
        # Ensure we have valid dates
        if pd.isna(min_date) or pd.isna(max_date):
            min_date = datetime.now().date() - timedelta(days=365)
            max_date = datetime.now().date()
        
        # Ensure min_date is not greater than max_date
        if min_date > max_date:
            temp = min_date
            min_date = max_date
            max_date = temp
            
        default_range = (min_date, max_date)
        
        # Initialize session state properly with valid range
        if 'date_range' not in st.session_state:
            st.session_state['date_range'] = default_range
        else:
            # Validate existing session_state date range against current min/max
            stored_start, stored_end = st.session_state['date_range']
            if stored_start < min_date or stored_end > max_date:
                # Reset to valid range if current selection is invalid
                st.session_state['date_range'] = default_range
        
        # Add button to reset date range
        if st.sidebar.button("Reset to Full Date Range"):
            st.session_state['date_range'] = default_range
            st.rerun()  # Force rerun to update UI immediately
        
        # Always show date input with current value from session state
        date_input = st.sidebar.date_input(
            "Date Range",
            value=st.session_state['date_range'],
            min_value=min_date,
            max_value=max_date
        )
        
        # Update session state if user changes the date
        if len(date_input) == 2 and date_input != st.session_state['date_range']:
            # Ensure the new date range is valid
            if date_input[0] >= min_date and date_input[1] <= max_date:
                st.session_state['date_range'] = date_input
    
    except Exception as e:
        st.error(f"Error setting up date filter: {e}")
        # Fallback to simple date range without session state
        try:
            # If date calculation fails, use a safe default range
            today = datetime.now().date()
            one_year_ago = today - timedelta(days=365)
            date_input = st.sidebar.date_input(
                "Date Range",
                value=(one_year_ago, today)
            )
        except Exception as e2:
            st.error(f"Could not create date input: {e2}")
            date_input = []
    
    # Filter data based on selections
    filtered_df = df[df['channel_title'].isin(selected_youtubers)].copy()  # Create a copy to avoid SettingWithCopyWarning
    
    if len(date_input) == 2:
        try:
            start_date, end_date = date_input
            filtered_df = filtered_df[
                (filtered_df['published_at'].dt.date >= start_date) & 
                (filtered_df['published_at'].dt.date <= end_date)
            ]
        except Exception as e:
            st.error(f"Error applying date filter: {e}")
    
    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return
    
    # Create a color map for the currently selected YouTubers
    color_discrete_map = {}
    for channel in selected_youtubers:
        color_discrete_map[channel] = CHANNEL_COLORS.get(channel, "#808080")  # Default to gray if not found
    
    # Display analytics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Channel Comparison")
        channel_stats = filtered_df.groupby('channel_title').agg(
            total_videos=('video_id', 'count'),
            avg_views=('views', 'mean'),
            total_views=('views', 'sum')
        ).reset_index()
        
        # Format numbers for better display
        channel_stats['avg_views'] = channel_stats['avg_views'].round(0).astype(int)
        
        # Sort by total views for better visualization
        channel_stats = channel_stats.sort_values('total_views', ascending=False)
        
        fig1 = px.bar(
            channel_stats, 
            x='channel_title', 
            y='total_views',
            color='channel_title',
            title="Total Views by Channel",
            color_discrete_map=color_discrete_map,
            text='total_views'  # Show values on bars
        )
        
        # Improve layout
        fig1.update_layout(
            xaxis_title="Channel",
            yaxis_title="Total Views",
            legend_title="Channel",
            uniformtext_minsize=10,
            uniformtext_mode='hide',
            yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
        )
        
        # Format the text on bars to show millions/thousands
        fig1.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside'
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # Format numbers for display in the dataframe
        display_stats = channel_stats.copy()
        display_stats['total_views'] = display_stats['total_views'].apply(lambda x: f"{int(x):,}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        display_stats['avg_views'] = display_stats['avg_views'].apply(lambda x: f"{int(x):,}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.dataframe(display_stats)
            # Format the published_at column for better display
        display_top = filtered_df.sort_values('views', ascending=False).head(10).copy()
        display_top['published_at'] = display_top['published_at'].dt.strftime('%Y-%m-%d')
        display_top['views'] = display_top['views'].apply(lambda x: f"{int(x):,}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Display as table
        st.dataframe(
            display_top[['video_title', 'channel_title', 'published_at', 'views']]
        )

    with col2:
        st.subheader("Performance Trends")
        # Process date information for visualization
        processed_df = filtered_df.copy()  # Create another copy for further processing
        
        # Create a numeric representation of year-week for proper sorting
        processed_df['year_week_num'] = processed_df['published_at'].dt.year * 100 + processed_df['published_at'].dt.isocalendar().week
        
        # Create the display version of year-week
        processed_df['week'] = processed_df['published_at'].dt.isocalendar().week
        processed_df['year'] = processed_df['published_at'].dt.year
        processed_df['year_week'] = processed_df['year'].astype(str) + "-W" + processed_df['week'].astype(str).str.zfill(2)
        
        # Sort by date for proper chronological order
        processed_df = processed_df.sort_values('year_week_num')
        
        # Group by week and channel
        weekly_data = processed_df.groupby(['year_week', 'year_week_num', 'channel_title']).agg(
            avg_views=('views', 'mean')
        ).reset_index()
        
        # Round average views to integers
        weekly_data['avg_views'] = weekly_data['avg_views'].round(0).astype(int)
        
        # Ensure chronological order of weeks by sorting
        weekly_data = weekly_data.sort_values('year_week_num')
        
        # Get list of all youtubers
        all_channels = filtered_df['channel_title'].unique()
        
        # Get list of all year-weeks in order
        all_year_weeks = weekly_data[['year_week', 'year_week_num']].drop_duplicates().sort_values('year_week_num')
        all_weeks = all_year_weeks['year_week'].tolist()
        
        # Create a complete grid of all channel/week combinations
        complete_grid = []
        for channel in all_channels:
            for i, week in enumerate(all_weeks):
                week_num = all_year_weeks.iloc[i]['year_week_num']
                complete_grid.append({
                    'year_week': week,
                    'year_week_num': week_num,
                    'channel_title': channel
                })
        
        # Convert to dataframe and merge with actual data
        complete_df = pd.DataFrame(complete_grid)
        weekly_data = pd.merge(
            complete_df, 
            weekly_data, 
            on=['year_week', 'year_week_num', 'channel_title'],
            how='left'
        )
        
        # Fill missing values with 0
        weekly_data['avg_views'] = weekly_data['avg_views'].fillna(0)
        
        # Sort by year_week_num to ensure proper chronological order
        weekly_data = weekly_data.sort_values(['channel_title', 'year_week_num'])
        
        # Use graph_objects for more control over the visualization
        fig2 = go.Figure()
        
        # Add a line for each channel
        for channel in all_channels:
            channel_data = weekly_data[weekly_data['channel_title'] == channel]
            
            # Only add the channel if it has data
            if not channel_data.empty and channel_data['avg_views'].sum() > 0:
                # Use the channel color from the color map
                color = color_discrete_map.get(channel, "#808080")
                
                fig2.add_trace(go.Scatter(
                    x=channel_data['year_week'],
                    y=channel_data['avg_views'],
                    mode='lines+markers',
                    name=channel,
                    line=dict(color=color, width=2),
                    marker=dict(color=color, size=6),
                    connectgaps=True,  # Connect across weeks with no data
                    hovertemplate="<b>%{x}</b><br>" +
                                "Channel: " + channel + "<br>" +
                                "Avg Views: %{y:,.0f}<br>" +
                                "<extra></extra>"  # Hide trace name in hover
                ))
        
        if 'selected_week' not in st.session_state:
            st.session_state['selected_week'] = None

        # Add custom events to the figure
        fig2.update_layout(
            title='Average Views per Week (Click on a week to see videos)',
            xaxis_title='Week',
            yaxis_title='Average Views',
            legend_title='Channel',
            hovermode='closest',  # Changed to closest for better click interaction
            xaxis=dict(
                tickmode='array',
                # Show fewer ticks for readability
                tickvals=all_weeks[::max(1, len(all_weeks) // 10)],
                # Ensure the order matches the numeric order
                categoryorder='array',
                categoryarray=all_weeks
            ),
            yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
            clickmode='event+select'  # Enable click events
        )
        
        # Display the chart
        st.plotly_chart(fig2, use_container_width=True)
        
        # Add a clickable week selector as a backup method
        st.subheader("Select a week to view videos:")
        selected_week = st.selectbox("Choose week:", all_weeks, index=0 if all_weeks else None)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Videos for Selected Week"):
                st.session_state['selected_week'] = selected_week
        with col2:
            if st.button("Clear Selected Week"):
                st.session_state['selected_week'] = None
        
        # Create a container for weekly videos
        weekly_videos_container = st.container()
        
        # Display videos for the selected week
        if st.session_state['selected_week']:
            week_data = {
                'points': [{'x': st.session_state['selected_week']}]
            }
            with weekly_videos_container:
                display_weekly_videos(filtered_df, week_data)
        
    # Top videos with consistent channel coloring
    st.subheader("Top Videos")
    top_videos = filtered_df.sort_values('views', ascending=False).head(10)
    
    # Create a bar chart for top videos
    fig3 = px.bar(
        top_videos,
        x='video_title',
        y='views',
        color='channel_title',
        title="Top 10 Videos by Views",
        color_discrete_map=color_discrete_map,
        text='views'  # Show values on bars
    )
    
    # Improve layout
    fig3.update_layout(
        xaxis_title="",
        yaxis_title="Views",
        legend_title="Channel",
        xaxis_tickangle=-45,  # Angle labels for better readability
        yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
        height=500  # Make the chart taller to accommodate labels
    )
    
    # Format the text on bars to show millions/thousands
    fig3.update_traces(
        texttemplate='%{text:,.0f}',
        textposition='outside'
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    # Additional visualization: Views distribution by channel
    st.subheader("Views Distribution by Channel")
    
    fig4 = px.box(
        filtered_df,
        x='channel_title',
        y='views',
        color='channel_title',
        title="Views Distribution by Channel",
        color_discrete_map=color_discrete_map,
        points="all"  # Show all points for small datasets
    )
    
    fig4.update_layout(
        xaxis_title="Channel",
        yaxis_title="Views",
        showlegend=False,  # Hide legend as it's redundant with x-axis
        yaxis=dict(tickformat=',d')  # Format y-axis with comma as thousand separator
    )
    
    st.plotly_chart(fig4, use_container_width=True)
    st.container()
if __name__ == "__main__":
    show_analytics()