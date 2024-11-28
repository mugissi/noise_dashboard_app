import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import subprocess

# Page configuration
st.set_page_config(
    page_title="Noise Monitoring Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GitHub에서 CSV 파일을 읽기 위한 URL 설정
csv_file_paths = {
    '19_M1_S25_9002.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/noise.app/19_M1_S25_9002.csv.gpg',
    '20_Northing_avg.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/noise.app/20_Northing_avg.csv.gpg'
}

# Streamlit Secrets에서 비밀번호 가져오기
gpg_password = st.secrets["general"]["GPG_PASSWORD"]

# Sidebar for file selection
with st.sidebar:
    st.header("Noise Monitoring Dashboard")

    selected_csv_name = st.selectbox(
        'Select an Encrypted CSV file:', ['19_M1_S25_9002.csv.gpg', '20_Northing_avg.csv.gpg']
    )
    selected_csv_url = csv_file_paths[selected_csv_name]  # Corresponding file URL

    # Decrypt the file using GPG
    encrypted_file = selected_csv_name
    decrypted_file = f"decrypted_{selected_csv_name.replace('.gpg', '.csv')}"

    # Run decryption command
    command = f"echo {gpg_password} | gpg --batch --yes --passphrase-fd 0 -o {decrypted_file} -d {encrypted_file}"
    subprocess.run(command, shell=True, check=True)

    # Load the decrypted CSV file
    df = pd.read_csv(decrypted_file)

    # Add a slider to filter distance range
    min_distance, max_distance = st.slider(
        "Select Distance Range (m):",
        min_value=int(df['distance'].min()),
        max_value=int(df['distance'].max()),
        value=(int(df['distance'].min()), int(df['distance'].max()))
    )

# Filter the dataframe based on the selected distance range
filtered_df = df[(df['distance'] >= min_distance) & (df['distance'] <= max_distance)]

# Data Processing Class
class StationDataProcessor:
    def __init__(self, df):
        self.data_frame = df
        self.codes = self.data_frame['code'].values
        self.stations = self.data_frame['station'].values
        self.station_distances = self.data_frame['station distance'].values
        self.distances = self.data_frame['distance'].values
        self.dBs = self.data_frame['dB'].values
        self.speeds = self.data_frame['speed'].values
        self.station_pairs = []
        self.station_btw_distance = []
        self.create_station_pairs()

    def create_station_pairs(self):
        for i in range(len(self.codes) - 1):
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"
            distance_pair = (self.station_distances[i], self.station_distances[i + 1])
            self.station_pairs.append(pair)
            self.station_btw_distance.append(distance_pair)

    def get_filtered_data(self, min_speed):
        return self.data_frame[self.data_frame['speed'] >= min_speed]

    def get_station_intervals(self, filtered_data):
        station_intervals = []
        for pair, (start_distance, end_distance) in zip(self.station_pairs, self.station_btw_distance):
            main_line_between = filtered_data[(filtered_data['distance'] >= start_distance) & (filtered_data['distance'] <= end_distance)]
            if not main_line_between.empty:
                average_noise = main_line_between['dB'].mean()
                maximum_noise = main_line_between['dB'].max()
            else:
                average_noise = 0
                maximum_noise = 0
            station_intervals.append({
                'Station Pair': pair,
                'Average Noise (dBA)': average_noise,
                'Maximum Noise (dBA)': maximum_noise
            })
        return pd.DataFrame(station_intervals)

# Streamlit App Header
st.title("Noise Monitoring Dashboard")

# Process Data
processor = StationDataProcessor(filtered_df)

# Input for Minimum Speed
min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=300, value=70)

# Get filtered data and station intervals
filtered_data = processor.get_filtered_data(min_speed)
station_intervals_df = processor.get_station_intervals(filtered_data)

# Create Plotly Figure
fig = go.Figure()
fig.add_trace(go.Bar(
    x=station_intervals_df['Station Pair'],
    y=station_intervals_df['Maximum Noise (dBA)'],
    name='Maximum Noise (dBA)',
    marker_color='#808080'
))
fig.add_trace(go.Bar(
    x=station_intervals_df['Station Pair'],
    y=station_intervals_df['Average Noise (dBA)'],
    name='Average Noise (dBA)',
    marker_color='#C0C0C0'
))

fig.update_layout(
    title=f"Noise Levels (Avg and Max) at Speed Above {min_speed} km/h",
    xaxis_title="Station Pair",
    yaxis_title="Noise Level (dBA)",
    barmode='stack',  # Changed to stack for better visualization
    height=600
)

# Display Plotly Chart
st.plotly_chart(fig, use_container_width=True)

# Insights Section
st.markdown("### Insights:")
st.write("This graph visualizes the average and maximum noise levels at selected station pairs based on speed and distance filters.")

# About Section
with st.expander('About', expanded=True):
    st.write("1. Select a CSV file from the sidebar.")
    st.write("2. Adjust the filters to explore specific ranges of data.")
    st.write("3. The graphs show insights on noise levels in relation to speed and distance.")
