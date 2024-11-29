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

# Sidebar
with st.sidebar:
    st.header("Noise Monitoring Dashboard")

    # Use a selectbox to display the file options more clearly
    selected_csv_name = st.sidebar.selectbox(
        'Select an Encrypted CSV file:', ['19_M1_S25_9002.csv.gpg', '20_Northing_avg.csv.gpg']
    )
    selected_csv_url = csv_file_paths[selected_csv_name]  # Get the corresponding file URL

    # 암호화된 파일을 다운로드 후 GPG 복호화 실행
    encrypted_file = selected_csv_name
    decrypted_file = f"decrypted_{selected_csv_name.replace('.gpg', '.csv')}"  # 복호화된 파일 이름 설정

    # GPG 복호화 명령 실행
    command = f"echo {gpg_password} | gpg --batch --yes --passphrase-fd 0 -o {decrypted_file} -d {encrypted_file}"
    subprocess.run(command, shell=True, check=True)

    # 복호화된 CSV 파일 읽기
    df = pd.read_csv(decrypted_file)


# 데이터 준비 클래스 정의
class StationDataProcessor:
    def __init__(self, df):
        self.data_frame = df
        self.codes = self.data_frame['code'].values
        self.stations = self.data_frame['station'].values
        self.station_distances = self.data_frame['station distance'].values
        self.distances = self.data_frame['distance'].values
        self.dBs = self.data_frame['dB'].values
        self.speeds = self.data_frame['speed'].values

        # 역 쌍 생성
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

    def get_station_intervals(self):
        station_intervals = []
        for pair, (start_distance, end_distance) in zip(self.station_pairs, self.station_btw_distance):
            main_line_between = self.data_frame[(self.data_frame['distance'] >= start_distance) & (self.data_frame['distance'] <= end_distance)]
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

# Streamlit 애플리케이션
st.title("Noise Monitoring Dashboard")

# 데이터 프로세싱
processor = StationDataProcessor(df)
station_intervals_df = processor.get_station_intervals()

# Dashboard Layout
col1, col2 = st.columns([1, 3])

# Dashboard Main Panel
col = st.columns((2, 1), gap='medium')
with col[0]:
    # 막대그래프 생성
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
        title="Average and Maximum Noise Levels by Station Pair",
        xaxis_title="Station Pair",
        yaxis_title="Noise Level (dBA)",
        barmode='overlay'
    )

    st.plotly_chart(fig, use_container_width=True)

# About section
with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Analyze the graphs for insights on noise levels and station intervals.")
