import numpy as np
import pandas as pd
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

    # Add a slider to filter distance range
    min_distance, max_distance = st.slider(
        "Select Distance Range (m):",
        min_value=int(df['distance'].min()),
        max_value=int(df['distance'].max()),
        value=(int(df['distance'].min()), int(df['distance'].max()))
    )

# Filter the dataframe based on the selected distance range
filtered_df = df[(df['distance'] >= min_distance) & (df['distance'] <= max_distance)]

# 역 구간 데이터 생성
class StationDataProcessor:
    def __init__(self, file_path):
        self.data_frame = pd.read_csv(file_path)
        self.codes = self.data_frame['code'].values
        self.station_distances = self.data_frame['station distance'].values
        self.station_pairs = []  # 초기화
        self.station_btw_distance = []  # 초기화

    def create_station_pairs(self):
        station_pairs = []
        station_btw_distance = []

        for i in range(len(self.codes) - 1):
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"
            distance_pair = (self.station_distances[i], self.station_distances[i + 1])
            station_pairs.append(pair)
            station_btw_distance.append(distance_pair)

        # 생성한 데이터를 인스턴스 속성으로 저장
        self.station_pairs = station_pairs
        self.station_btw_distance = station_btw_distance

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

# 데이터 프로세싱
processor = StationDataProcessor(decrypted_file)
station_pairs, station_btw_distance = processor.create_station_pairs()
station_intervals_df = processor.get_station_intervals(filtered_df)

# Dashboard Main Panel
col = st.columns((2, 1), gap='medium')  # 순서를 바꿔서 1열이 막대그래프, 2열이 라인차트

with col[0]:
    # 수정된 막대그래프 구현
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
        title="Average and Maximum Noise Levels",
        xaxis_title="Station Pair",
        yaxis_title="Noise Level (dBA)",
        barmode='overlay',
        height=600  # Adjusted height
    )
    st.plotly_chart(fig, use_container_width=True)

with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Adjust filters to explore specific ranges of data.")
        st.write("3. Analyze the graphs for insights on noise levels and speed.")

# 선형 차트 추가
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=filtered_df['distance'],
    y=filtered_df['dB'],
    mode='lines',
    name='Noise Level (dB)',
    yaxis="y1"
))
fig.add_trace(go.Scatter(
    x=filtered_df['distance'],
    y=filtered_df['speed'],
    mode='lines',
    name='Speed (km/h)',
    yaxis="y2"
))
fig.update_layout(
    title="Noise Levels and Speed Over Distance",
    xaxis=dict(title="Distance (m)"),
    yaxis=dict(title="Noise Level (dB)", side="left"),
    yaxis2=dict(title="Speed (km/h)", overlaying="y", side="right"),
    height=600
)
st.plotly_chart(fig, use_container_width=True)
