import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config.settings import CSV_FILE_PATH, CHANNEL_COLORS
from utils.data_processor import convert_date_str
import streamlit as st

def display_weekly_videos(df, week_data, is_shorts=False):
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
        
    title = f"Videos from {year_week}"
    if is_shorts:
        title += " (Shorts Only)"
    else:
        title += " (Regular Videos Only)"
        
    st.subheader(title)
    st.write(f"{len(week_videos)} videos published this week")
    
    # Format the data for display
    display_df = week_videos.copy()
    display_df['published_at'] = display_df['published_at'].dt.strftime('%Y-%m-%d')
    display_df['views'] = display_df['views'].apply(lambda x: f"{int(x):,}")
    if 'likes' in display_df.columns:
        display_df['likes'] = display_df['likes'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "Unknown")
    
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
            if 'likes' in row and pd.notna(row['likes']):
                st.write(f"Likes: {row['likes']}")


def show_shortsinpact():
    st.title("Shorts Impact Analysis")
    
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
    required_columns = ['video_id', 'video_title', 'channel_title', 'published_at', 'views', 'duration_seconds']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns in data: {', '.join(missing_columns)}")
        return
    
    # Convert published_at to datetime and ensure it's timezone aware
    df['published_at'] = df['published_at'].apply(convert_date_str)
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
    
    # Handle NaT values if any conversion failed
    df = df.dropna(subset=['published_at'])
    
    # Create Short vs Regular filters
    shorts_threshold = 60  # Threshold in seconds for what counts as a short
    
    # Create two datasets
    df_shorts = df[df['duration_seconds'] < shorts_threshold].copy()
    df_regular = df[df['duration_seconds'] >= shorts_threshold].copy()
    
    # Display summary metrics
    total_videos = len(df)
    total_shorts = len(df_shorts)
    total_regular = len(df_regular)
    
    st.subheader("Video Distribution Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Videos", f"{total_videos:,}")
    
    with col2:
        st.metric("Short Videos (≤60s)", f"{total_shorts:,} ({total_shorts/total_videos*100:.1f}%)")
    
    with col3:
        st.metric("Regular Videos (>60s)", f"{total_regular:,} ({total_regular/total_videos*100:.1f}%)")
    
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

    if selected_youtubers:
        colorize_multiselect_options([CHANNEL_COLORS.get(pg, "#808080") for pg in selected_youtubers])

    if not selected_youtubers:  # If nothing selected, use all
        selected_youtubers = youtubers
    
    # Date range filter
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
        if 'shorts_date_range' not in st.session_state:
            st.session_state['shorts_date_range'] = default_range
        else:
            # Validate existing session_state date range against current min/max
            stored_start, stored_end = st.session_state['shorts_date_range']
            if stored_start < min_date or stored_end > max_date:
                # Reset to valid range if current selection is invalid
                st.session_state['shorts_date_range'] = default_range
        
        # Add button to reset date range
        if st.sidebar.button("Reset to Full Date Range"):
            st.session_state['shorts_date_range'] = default_range
            st.rerun()  # Force rerun to update UI immediately
        
        # Always show date input with current value from session state
        date_input = st.sidebar.date_input(
            "Date Range",
            value=st.session_state['shorts_date_range'],
            min_value=min_date,
            max_value=max_date
        )
        
        # Update session state if user changes the date
        if len(date_input) == 2 and date_input != st.session_state['shorts_date_range']:
            # Ensure the new date range is valid
            if date_input[0] >= min_date and date_input[1] <= max_date:
                st.session_state['shorts_date_range'] = date_input
    
    except Exception as e:
        st.error(f"Error setting up date filter: {e}")
        date_input = []
    
    # Filter data based on selections
    filtered_shorts = df_shorts[df_shorts['channel_title'].isin(selected_youtubers)].copy()
    filtered_regular = df_regular[df_regular['channel_title'].isin(selected_youtubers)].copy()
    
    if len(date_input) == 2:
        try:
            start_date, end_date = date_input
            filtered_shorts = filtered_shorts[
                (filtered_shorts['published_at'].dt.date >= start_date) & 
                (filtered_shorts['published_at'].dt.date <= end_date)
            ]
            filtered_regular = filtered_regular[
                (filtered_regular['published_at'].dt.date >= start_date) & 
                (filtered_regular['published_at'].dt.date <= end_date)
            ]
        except Exception as e:
            st.error(f"Error applying date filter: {e}")
    
    if filtered_shorts.empty and filtered_regular.empty:
        st.warning("No data available for the selected filters.")
        return
    
    # Create a color map for the currently selected YouTubers
    color_discrete_map = {}
    for channel in selected_youtubers:
        color_discrete_map[channel] = CHANNEL_COLORS.get(channel, "#808080")  # Default to gray if not found
    
    # Total views comparison
    st.text("")
    col1, col2 = st.columns(2)
    
    # Process data for shorts
    shorts_stats = filtered_shorts.groupby('channel_title').agg(
        total_videos=('video_id', 'count'),
        avg_views=('views', 'mean'),
        total_views=('views', 'sum')
    ).reset_index()
    
    # Process data for regular videos
    regular_stats = filtered_regular.groupby('channel_title').agg(
        total_videos=('video_id', 'count'),
        avg_views=('views', 'mean'),
        total_views=('views', 'sum')
    ).reset_index()
    
    with col1:
        st.write("### Shorts (≤60s)")
        
        # Stats table for shorts
        if not shorts_stats.empty:
            # Format numbers for better display
            shorts_stats['avg_views'] = shorts_stats['avg_views'].round(0).astype(int)
            
            # Sort by total views for better visualization
            shorts_stats = shorts_stats.sort_values('total_views', ascending=False)
            
            fig_shorts = px.bar(
                shorts_stats, 
                x='channel_title', 
                y='total_views',
                color='channel_title',
                title="Total Views from Shorts",
                color_discrete_map=color_discrete_map,
                text='total_views'  # Show values on bars
            )
            
            # Improve layout
            fig_shorts.update_layout(
                xaxis_title="Channel",
                yaxis_title="Total Views",
                legend_title="Channel",
                uniformtext_minsize=10,
                uniformtext_mode='hide',
                yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
            )
            
            # Format the text on bars to show millions/thousands
            fig_shorts.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside'
            )
            
            st.plotly_chart(fig_shorts, use_container_width=True)
            
            # Format numbers for display in the dataframe
            display_shorts_stats = shorts_stats.copy()
            display_shorts_stats['total_views'] = display_shorts_stats['total_views'].apply(lambda x: f"{int(x):,}")
            display_shorts_stats['avg_views'] = display_shorts_stats['avg_views'].apply(lambda x: f"{int(x):,}")
            
            st.dataframe(display_shorts_stats)
        else:
            st.info("No short videos available for the selected filters.")
    
    with col2:
        st.write("### Regular Videos (>60s)")
        
        # Stats table for regular videos
        if not regular_stats.empty:
            # Format numbers for better display
            regular_stats['avg_views'] = regular_stats['avg_views'].round(0).astype(int)
            
            # Sort by total views for better visualization
            regular_stats = regular_stats.sort_values('total_views', ascending=False)
            
            fig_regular = px.bar(
                regular_stats, 
                x='channel_title', 
                y='total_views',
                color='channel_title',
                title="Total Views from Regular Videos",
                color_discrete_map=color_discrete_map,
                text='total_views'  # Show values on bars
            )
            
            # Improve layout
            fig_regular.update_layout(
                xaxis_title="Channel",
                yaxis_title="Total Views",
                legend_title="Channel",
                uniformtext_minsize=10,
                uniformtext_mode='hide',
                yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
            )
            
            # Format the text on bars to show millions/thousands
            fig_regular.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside'
            )
            
            st.plotly_chart(fig_regular, use_container_width=True)
            
            # Format numbers for display in the dataframe
            display_regular_stats = regular_stats.copy()
            display_regular_stats['total_views'] = display_regular_stats['total_views'].apply(lambda x: f"{int(x):,}")
            display_regular_stats['avg_views'] = display_regular_stats['avg_views'].apply(lambda x: f"{int(x):,}")
            
            st.dataframe(display_regular_stats)
        else:
            st.info("No regular videos available for the selected filters.")
    
    # Views over time comparison
    st.text("")
    st.subheader("Weekly Views: Shorts vs Regular Videos")
    
    # Initialize session states for week selection if they don't exist
    if 'selected_shorts_week' not in st.session_state:
        st.session_state['selected_shorts_week'] = None
    if 'selected_regular_week' not in st.session_state:
        st.session_state['selected_regular_week'] = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Process shorts data for weekly visualization
        if not filtered_shorts.empty:
            processed_shorts = filtered_shorts.copy()
            processed_shorts['year_week_num'] = processed_shorts['published_at'].dt.year * 100 + processed_shorts['published_at'].dt.isocalendar().week
            processed_shorts['week'] = processed_shorts['published_at'].dt.isocalendar().week
            processed_shorts['year'] = processed_shorts['published_at'].dt.year
            processed_shorts['year_week'] = processed_shorts['year'].astype(str) + "-W" + processed_shorts['week'].astype(str).str.zfill(2)
            
            # Group by week and channel
            weekly_shorts = processed_shorts.groupby(['year_week', 'year_week_num', 'channel_title']).agg(
                avg_views=('views', 'mean')
            ).reset_index()
            
            if not weekly_shorts.empty:
                # Prepare data for visualization
                weekly_shorts['avg_views'] = weekly_shorts['avg_views'].round(0).astype(int)
                weekly_shorts = weekly_shorts.sort_values('year_week_num')
                
                # Get list of youtubers and weeks
                shorts_channels = filtered_shorts['channel_title'].unique()
                all_shorts_weeks = weekly_shorts[['year_week', 'year_week_num']].drop_duplicates().sort_values('year_week_num')
                shorts_weeks = all_shorts_weeks['year_week'].tolist()
                
                # Create complete grid for all combinations
                complete_grid = []
                for channel in shorts_channels:
                    for i, week in enumerate(shorts_weeks):
                        week_num = all_shorts_weeks.iloc[i]['year_week_num']
                        complete_grid.append({
                            'year_week': week,
                            'year_week_num': week_num,
                            'channel_title': channel
                        })
                
                # Merge and fill missing values
                complete_df = pd.DataFrame(complete_grid)
                weekly_shorts = pd.merge(
                    complete_df, 
                    weekly_shorts, 
                    on=['year_week', 'year_week_num', 'channel_title'],
                    how='left'
                )
                weekly_shorts['avg_views'] = weekly_shorts['avg_views'].fillna(0)
                weekly_shorts = weekly_shorts.sort_values(['channel_title', 'year_week_num'])
                
                # Create figure for shorts
                fig_shorts_weekly = go.Figure()
                
                # Add a line for each channel
                for channel in shorts_channels:
                    channel_data = weekly_shorts[weekly_shorts['channel_title'] == channel]
                    
                    if not channel_data.empty and channel_data['avg_views'].sum() > 0:
                        color = color_discrete_map.get(channel, "#808080")
                        
                        fig_shorts_weekly.add_trace(go.Scatter(
                            x=channel_data['year_week'],
                            y=channel_data['avg_views'],
                            mode='lines+markers',
                            name=channel,
                            line=dict(color=color, width=2),
                            marker=dict(color=color, size=6),
                            connectgaps=True,
                            hovertemplate="<b>%{x}</b><br>" +
                                        "Channel: " + channel + "<br>" +
                                        "Avg Views: %{y:,.0f}<br>" +
                                        "<extra></extra>"
                        ))
                
                # Layout
                fig_shorts_weekly.update_layout(
                    title='Weekly Views - Shorts',
                    xaxis_title='Week',
                    yaxis_title='Average Views',
                    legend_title='Channel',
                    hovermode='closest',
                    xaxis=dict(
                        tickmode='array',
                        tickvals=shorts_weeks[::max(1, len(shorts_weeks) // 10)],
                        categoryorder='array',
                        categoryarray=shorts_weeks
                    ),
                    yaxis=dict(tickformat=',d')
                )
                
                st.plotly_chart(fig_shorts_weekly, use_container_width=True)
                
                # Week selector for shorts
                st.write("#### Select a week to view short videos:")
                selected_shorts_week = st.selectbox(
                    "Choose week (Shorts):", 
                    shorts_weeks, 
                    index=0 if shorts_weeks else None,
                    key="shorts_week_selector"
                )
                
                col1a, col2a = st.columns(2)
                with col1a:
                    if st.button("View Shorts for Selected Week"):
                        st.session_state['selected_shorts_week'] = selected_shorts_week
                with col2a:
                    if st.button("Clear Shorts Week"):
                        st.session_state['selected_shorts_week'] = None
                
                # Display shorts for selected week
                if st.session_state['selected_shorts_week']:
                    week_data = {
                        'points': [{'x': st.session_state['selected_shorts_week']}]
                    }
                    display_weekly_videos(filtered_shorts, week_data, is_shorts=True)
            else:
                st.info("Not enough weekly data to visualize shorts performance.")
        else:
            st.info("No short videos available for the selected filters.")
    
    with col2:
        # Process regular videos data for weekly visualization
        if not filtered_regular.empty:
            processed_regular = filtered_regular.copy()
            processed_regular['year_week_num'] = processed_regular['published_at'].dt.year * 100 + processed_regular['published_at'].dt.isocalendar().week
            processed_regular['week'] = processed_regular['published_at'].dt.isocalendar().week
            processed_regular['year'] = processed_regular['published_at'].dt.year
            processed_regular['year_week'] = processed_regular['year'].astype(str) + "-W" + processed_regular['week'].astype(str).str.zfill(2)
            
            # Group by week and channel
            weekly_regular = processed_regular.groupby(['year_week', 'year_week_num', 'channel_title']).agg(
                avg_views=('views', 'mean')
            ).reset_index()
            
            if not weekly_regular.empty:
                # Prepare data for visualization
                weekly_regular['avg_views'] = weekly_regular['avg_views'].round(0).astype(int)
                weekly_regular = weekly_regular.sort_values('year_week_num')
                
                # Get list of youtubers and weeks
                regular_channels = filtered_regular['channel_title'].unique()
                all_regular_weeks = weekly_regular[['year_week', 'year_week_num']].drop_duplicates().sort_values('year_week_num')
                regular_weeks = all_regular_weeks['year_week'].tolist()
                
                # Create complete grid for all combinations
                complete_grid = []
                for channel in regular_channels:
                    for i, week in enumerate(regular_weeks):
                        week_num = all_regular_weeks.iloc[i]['year_week_num']
                        complete_grid.append({
                            'year_week': week,
                            'year_week_num': week_num,
                            'channel_title': channel
                        })
                
                # Merge and fill missing values
                complete_df = pd.DataFrame(complete_grid)
                weekly_regular = pd.merge(
                    complete_df, 
                    weekly_regular, 
                    on=['year_week', 'year_week_num', 'channel_title'],
                    how='left'
                )
                weekly_regular['avg_views'] = weekly_regular['avg_views'].fillna(0)
                weekly_regular = weekly_regular.sort_values(['channel_title', 'year_week_num'])
                
                # Create figure for regular videos
                fig_regular_weekly = go.Figure()
                
                # Add a line for each channel
                for channel in regular_channels:
                    channel_data = weekly_regular[weekly_regular['channel_title'] == channel]
                    
                    if not channel_data.empty and channel_data['avg_views'].sum() > 0:
                        color = color_discrete_map.get(channel, "#808080")
                        
                        fig_regular_weekly.add_trace(go.Scatter(
                            x=channel_data['year_week'],
                            y=channel_data['avg_views'],
                            mode='lines+markers',
                            name=channel,
                            line=dict(color=color, width=2),
                            marker=dict(color=color, size=6),
                            connectgaps=True,
                            hovertemplate="<b>%{x}</b><br>" +
                                        "Channel: " + channel + "<br>" +
                                        "Avg Views: %{y:,.0f}<br>" +
                                        "<extra></extra>"
                        ))
                
                # Layout
                fig_regular_weekly.update_layout(
                    title='Weekly Views - Regular Videos',
                    xaxis_title='Week',
                    yaxis_title='Average Views',
                    legend_title='Channel',
                    hovermode='closest',
                    xaxis=dict(
                        tickmode='array',
                        tickvals=regular_weeks[::max(1, len(regular_weeks) // 10)],
                        categoryorder='array',
                        categoryarray=regular_weeks
                    ),
                    yaxis=dict(tickformat=',d')
                )
                
                st.plotly_chart(fig_regular_weekly, use_container_width=True)
                
                # Week selector for regular videos
                st.write("#### Select a week to view regular videos:")
                selected_regular_week = st.selectbox(
                    "Choose week (Regular):", 
                    regular_weeks, 
                    index=0 if regular_weeks else None,
                    key="regular_week_selector"
                )
                
                col1b, col2b = st.columns(2)
                with col1b:
                    if st.button("View Regular Videos for Selected Week"):
                        st.session_state['selected_regular_week'] = selected_regular_week
                with col2b:
                    if st.button("Clear Regular Week"):
                        st.session_state['selected_regular_week'] = None
                
                # Display regular videos for selected week
                if st.session_state['selected_regular_week']:
                    week_data = {
                        'points': [{'x': st.session_state['selected_regular_week']}]
                    }
                    display_weekly_videos(filtered_regular, week_data, is_shorts=False)
            else:
                st.info("Not enough weekly data to visualize regular video performance.")
        else:
            st.info("No regular videos available for the selected filters.")
    # Add this at the end of your show_shortsinpact function, before any final lines:

    # Top videos comparison
    st.text("")
    st.subheader("Top Videos: Shorts vs Regular Videos")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("#### Top Shorts ≤60s)")
        
        if not filtered_shorts.empty:
            # Get top 10 shorts
            top_shorts = filtered_shorts.sort_values('views', ascending=False).head(10)
            
            # Create a bar chart for top shorts
            fig_top_shorts = px.bar(
                top_shorts,
                x='video_title',
                y='views',
                color='channel_title',
                title="Top 10 Shorts by Views",
                color_discrete_map=color_discrete_map,
                text='views'  # Show values on bars
            )
            
            # Improve layout
            fig_top_shorts.update_layout(
                xaxis_title="",
                yaxis_title="Views",
                legend_title="Channel",
                xaxis_tickangle=-45,  # Angle labels for better readability
                yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
                height=500  # Make the chart taller to accommodate labels
            )
            
            # Format the text on bars to show millions/thousands
            fig_top_shorts.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside'
            )
            
            st.plotly_chart(fig_top_shorts, use_container_width=True)
            
            # Format the published_at column for better display
            display_top_shorts = top_shorts.copy()
            display_top_shorts['published_at'] = display_top_shorts['published_at'].dt.strftime('%Y-%m-%d')
            display_top_shorts['views'] = display_top_shorts['views'].apply(lambda x: f"{int(x):,}")
            display_top_shorts['duration'] = display_top_shorts['duration_seconds'].apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d}" if pd.notna(x) else "Unknown"
            )
            
            # Display as table
            st.dataframe(
                display_top_shorts[['video_title', 'channel_title', 'published_at', 'views', 'duration']]
            )
        else:
            st.info("No short videos available for the selected filters.")
    
    with col2:
        st.write("#### Top Regular Videos (>60s)")
        
        if not filtered_regular.empty:
            # Get top 10 regular videos
            top_regular = filtered_regular.sort_values('views', ascending=False).head(10)
            
            # Create a bar chart for top regular videos
            fig_top_regular = px.bar(
                top_regular,
                x='video_title',
                y='views',
                color='channel_title',
                title="Top 10 Regular Videos by Views",
                color_discrete_map=color_discrete_map,
                text='views'  # Show values on bars
            )
            
            # Improve layout
            fig_top_regular.update_layout(
                xaxis_title="",
                yaxis_title="Views",
                legend_title="Channel",
                xaxis_tickangle=-45,  # Angle labels for better readability
                yaxis=dict(tickformat=',d'),  # Format y-axis with comma as thousand separator
                height=500  # Make the chart taller to accommodate labels
            )
            
            # Format the text on bars to show millions/thousands
            fig_top_regular.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside'
            )
            
            st.plotly_chart(fig_top_regular, use_container_width=True)
            
            # Format the published_at column for better display
            display_top_regular = top_regular.copy()
            display_top_regular['published_at'] = display_top_regular['published_at'].dt.strftime('%Y-%m-%d')
            display_top_regular['views'] = display_top_regular['views'].apply(lambda x: f"{int(x):,}")
            display_top_regular['duration'] = display_top_regular['duration_seconds'].apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d}" if pd.notna(x) else "Unknown"
            )
            
            # Display as table
            st.dataframe(
                display_top_regular[['video_title', 'channel_title', 'published_at', 'views', 'duration']]
            )
        else:
            st.info("No regular videos available for the selected filters.")
    
    # Views distribution comparison
    st.text("")
    st.subheader("Views Distribution: Shorts vs Regular Videos")
    st.text("")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("#### Views Distribution - Shorts")
        
        if not filtered_shorts.empty:
            fig_dist_shorts = px.box(
                filtered_shorts,
                x='channel_title',
                y='views',
                color='channel_title',
                title="Views Distribution - Shorts",
                color_discrete_map=color_discrete_map,
                points="all"  # Show all points for small datasets
            )
            
            fig_dist_shorts.update_layout(
                xaxis_title="Channel",
                yaxis_title="Views",
                showlegend=False,  # Hide legend as it's redundant with x-axis
                yaxis=dict(tickformat=',d')  # Format y-axis with comma as thousand separator
            )
            
            st.plotly_chart(fig_dist_shorts, use_container_width=True)
            
            # Show summary statistics
            shorts_view_stats = filtered_shorts.groupby('channel_title')['views'].describe()[
                ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']
            ].reset_index()
            
            # Format the statistics for display
            shorts_view_stats = shorts_view_stats.round(0)
            for col in ['mean', 'std', 'min', '25%', '50%', '75%', 'max']:
                shorts_view_stats[col] = shorts_view_stats[col].astype(int).apply(lambda x: f"{x:,}")
            
            st.dataframe(shorts_view_stats)
        else:
            st.info("No short videos available for the selected filters.")
    
    with col2:
        st.write("#### Views Distribution - Regular Videos")
        
        if not filtered_regular.empty:
            fig_dist_regular = px.box(
                filtered_regular,
                x='channel_title',
                y='views',
                color='channel_title',
                title="Views Distribution - Regular Videos",
                color_discrete_map=color_discrete_map,
                points="all"  # Show all points for small datasets
            )
            
            fig_dist_regular.update_layout(
                xaxis_title="Channel",
                yaxis_title="Views",
                showlegend=False,  # Hide legend as it's redundant with x-axis
                yaxis=dict(tickformat=',d')  # Format y-axis with comma as thousand separator
            )
            
            st.plotly_chart(fig_dist_regular, use_container_width=True)
            
            # Show summary statistics
            regular_view_stats = filtered_regular.groupby('channel_title')['views'].describe()[
                ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']
            ].reset_index()
            
            # Format the statistics for display
            regular_view_stats = regular_view_stats.round(0)
            for col in ['mean', 'std', 'min', '25%', '50%', '75%', 'max']:
                regular_view_stats[col] = regular_view_stats[col].astype(int).apply(lambda x: f"{x:,}")
            
            st.dataframe(regular_view_stats)
        else:
            st.info("No regular videos available for the selected filters.")
    
    # Add a comparison of overall performance metrics
    st.text("")
    st.subheader("Performance Comparison: Shorts vs Regular Videos")
    
    if not filtered_shorts.empty and not filtered_regular.empty:
        # Calculate overall stats
        avg_views_shorts = filtered_shorts['views'].mean()
        avg_views_regular = filtered_regular['views'].mean()
        
        median_views_shorts = filtered_shorts['views'].median()
        median_views_regular = filtered_regular['views'].median()
        
        total_views_shorts = filtered_shorts['views'].sum()
        total_views_regular = filtered_regular['views'].sum()
        
        # Create comparison metrics
        comparison_data = {
            'Metric': ['Average Views', 'Median Views', 'Total Views', 'Video Count'],
            'Shorts (≤60s)': [
                f"{int(avg_views_shorts):,}",
                f"{int(median_views_shorts):,}",
                f"{int(total_views_shorts):,}",
                f"{len(filtered_shorts):,}"
            ],
            'Regular Videos (>60s)': [
                f"{int(avg_views_regular):,}",
                f"{int(median_views_regular):,}",
                f"{int(total_views_regular):,}",
                f"{len(filtered_regular):,}"
            ],
            'Difference (%)': [
                f"{(avg_views_shorts/avg_views_regular-1)*100:.1f}%" if avg_views_regular > 0 else "N/A",
                f"{(median_views_shorts/median_views_regular-1)*100:.1f}%" if median_views_regular > 0 else "N/A",
                f"{(total_views_shorts/total_views_regular-1)*100:.1f}%" if total_views_regular > 0 else "N/A",
                f"{(len(filtered_shorts)/len(filtered_regular)-1)*100:.1f}%" if len(filtered_regular) > 0 else "N/A"
            ]
        }
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)
        
        # Create a bar chart comparing average views
        fig_comparison = go.Figure()
        
        fig_comparison.add_trace(go.Bar(
            x=['Average Views', 'Median Views'],
            y=[avg_views_shorts, median_views_shorts],
            name='Shorts (≤60s)',
            marker_color='rgba(71, 58, 131, 0.8)'
        ))
        
        fig_comparison.add_trace(go.Bar(
            x=['Average Views', 'Median Views'],
            y=[avg_views_regular, median_views_regular],
            name='Regular Videos (>60s)',
            marker_color='rgba(127, 166, 238, 0.8)'
        ))
        
        fig_comparison.update_layout(
            title="Average & Median Views Comparison",
            xaxis_title="Metric",
            yaxis_title="Views",
            barmode='group',
            yaxis=dict(tickformat=',d')
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
    else:
        st.info("Need both shorts and regular videos to generate comparison metrics.")