# YouTube Analytics Dashboard

This project is a Streamlit application that utilizes the YouTube API to retrieve and visualize video data from the top 10 largest tech YouTubers over the last year. The application allows users to view insights on video performance and trends.

## Project Structure

```
youtube-analytics-dashboard
├── app.py                # Main entry point for the Streamlit application
├── programs                 # Contains different pages of the application
│   ├── youtube.py        # Logic for retrieving video data from the YouTube API
│   └── analytics.py      # Visualizations of video data using Plotly
├── utils                 # Utility functions for API interaction, data processing, and visualization
│   ├── api_client.py     # Functions to interact with the YouTube API
│   ├── data_processor.py  # Processes video data and updates the CSV file
├── data                  # Directory for storing data files
│   └── videos.csv        # CSV file storing video data retrieved from the YouTube API
├── config                # Configuration settings for the application
│   └── settings.py       # Contains API keys and other constants
├── requirements.txt      # Lists dependencies required for the project
├── .env.example          # Template for environment variables
└── README.md             # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd youtube-analytics-dashboard
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   - Copy `.env.example` to `.env` and fill in your API keys and other sensitive information.

5. Run the application:
   ```
   streamlit run app.py
   ```

## Usage

- Navigate to the YouTube page to retrieve and store video data.
- The analytics page provides visualizations of views per week per YouTuber and the top 10 videos over time.

## Features

- Fetches video data from the YouTube API for the top 10 tech YouTubers.
- Updates the CSV file with new videos upon page refresh.
- Visualizes video performance trends using Plotly.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.