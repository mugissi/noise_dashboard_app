###########최종완성본###########
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import subprocess



stationdata = {
    "station": [
        "Lebakbulus", "Fatmawati", "Cipeteraya", "Haji Nawi", "Blok A",
        "Blok M", "ASEAN", "Senayan", "Istora", "Bendunganhilir",
        "Setiabudi", "Dukuh Atas", "Bundaran HI"
    ],
    "code": [
        "LBB", "FTW", "CPR", "HJN", "BLA", "BLM", "ASN", "SNY", "IST",
        "BNH", "SET", "DKA", "BHI"
    ],
    "station distance": [
        329, 2347, 4158, 5456, 6672, 7843, 8570, 10089, 10903,
        12218, 13001, 13917, 14983
    ]
}

station_df = pd.DataFrame(stationdata)

# Page configuration
st.set_page_config(
    page_title="Noise Monitoring Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GitHub에서 CSV 파일을 읽기 위한 URL 설정
csv_file_paths = {

    '18_M1_S25_9002.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/main/18.M1_S25_9002.csv.gpg',
    '19_M1_S25_9002.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/main/19_M1_S25_9002.csv.gpg',
    '20_Northing.1.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/main/20_Northing.1.csv.gpg'
}

# Streamlit Secrets에서 비밀번호 가져오기
gpg_password = st.secrets["general"]["GPG_PASSWORD"]

# Sidebar
with st.sidebar:
    st.header("Noise Monitoring Dashboard")

    # Use a selectbox to display the file options more clearly
    selected_csv_name = st.sidebar.selectbox(
        'Select CSV file:', ['18_M1_S25_9002.csv.gpg', '19_M1_S25_9002.csv.gpg', '20_Northing.1.csv.gpg']
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
    def __init__(self, data):
        """
        역 데이터를 처리하는 클래스입니다.
        """
        self.data_frame = pd.DataFrame(data)
        self.codes = self.data_frame['code'].values
        self.stations = self.data_frame['station'].values
        self.station_distances = self.data_frame['station distance'].values

        self.station_pairs = []  # 역 쌍 리스트
        self.station_btw_distance = []  # 역 거리 리스트
        self.create_station_pairs()

    def create_station_pairs(self):
        """
        역 쌍을 생성합니다.
        """
        for i in range(len(self.codes) - 1):
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"
            distance_pair = (self.station_distances[i], self.station_distances[i + 1])
            self.station_pairs.append(pair)
            self.station_btw_distance.append(distance_pair)


class NoiseDataProcessor:
    def __init__(self, data, station_processor):
        """
        소음 데이터를 처리하는 클래스입니다.
        """
        self.data_frame = data  # CSV에서 읽은 데이터 프레임
        self.station_processor = station_processor  # StationDataProcessor 인스턴스
        self.station_pairs = station_processor.station_pairs
        self.station_btw_distance = station_processor.station_btw_distance

    def get_filtered_data(self, min_speed):
        """
        속도 기준으로 데이터를 필터링합니다.
        """
        filtered_data = self.data_frame[self.data_frame['speed'] >= min_speed]
        return filtered_data

    def get_station_intervals(self, filtered_data):
        """
        역 구간별 평균 소음과 최대 소음을 계산합니다.
        """
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

# Streamlit 애플리케이션
st.title("Noise Monitoring Dashboard")

# 데이터 프로세싱: 역 데이터와 CSV 데이터를 각각 처리
station_processor = StationDataProcessor(stationdata)  # 역 정보 처리
noise_processor = NoiseDataProcessor(df, station_processor)  # 소음 데이터 처리

# Dashboard Layout
col1, col2 = st.columns([1, 3])  # 첫 번째 칼럼을 좁게 설정

with col1:
    # 최소 속도 입력 필드
    min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=100, value=50, key="speed_input", help="Set the minimum speed to filter data.")

with col2:

    # 소음 데이터 필터링 및 구간별 소음 분석
    filtered_data = noise_processor.get_filtered_data(min_speed)
    station_intervals_df = noise_processor.get_station_intervals(filtered_data)

# Dashboard Main Panel
col = st.columns((3, 1), gap='medium')  # 순서를 바꿔서 1열이 막대그래프, 2열이 라인차트
with col[0]:
    # 그래프 생성
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=station_intervals_df['Station Pair'],
        y=station_intervals_df['Maximum Noise (dBA)'],
        name='Maximum Noise (dBA)',
        marker_color='#1e90ff'
    ))
    fig.add_trace(go.Bar(
        x=station_intervals_df['Station Pair'],
        y=station_intervals_df['Average Noise (dBA)'],
        name='Average Noise (dBA)',
        marker_color='#4682b4'
    ))
    fig.update_layout(
        title=f"Average and Maximum Noise Levels at Speed Above {min_speed} km/h",
        xaxis_title="Station",
        yaxis_title="Noise Level (dBA)",
        barmode='overlay'
    )

    st.plotly_chart(fig, use_container_width=True)

       # 라인 차트 생성
    line_fig = go.Figure()

    # Plot Noise Level (dB)
    line_fig.add_trace(go.Scatter(
        x=df['distance'],
        y=df['dB'],
        mode='lines',
        name='Noise Level (dB)',
        yaxis="y1"
    ))

    # Plot Speed (km/h)
    line_fig.add_trace(go.Scatter(
        x=df['distance'],
        y=df['speed'],
        mode='lines',
        name='Speed (km/h)',
        yaxis="y2"
    ))

    # Update layout with dual y-axes
    line_fig.update_layout(
        title="Noise Levels and Speed Over Distance",
        xaxis=dict(title="Distance (m)"),
        yaxis=dict(title="Noise Level (dB)", side="left"),
        yaxis2=dict(title="Speed (km/h)", overlaying="y", side="right"),
        height=600
    )

    st.plotly_chart(line_fig, use_container_width=True)


# CSS 스타일 추가
st.markdown("""
    <style>
        .big-title {
            font-size: 24px;
            font-weight: bold;
        }
        .section-title {
            font-size: 20px;
            font-weight: bold;
        }
        .content {
            font-size: 16px;
        }
    </style>
""", unsafe_allow_html=True)

# 대시보드 사용법
with st.expander('How to Use the Dashboard for Decision-Making', expanded=True):
    st.markdown("""
    <div class="big-title">How to Use the Dashboard for Decision-Making</div>

    <div class="section-title">1. Sidebar</div>
    <div class="content">You can select a saved CSV file to visualize and check noise data for a specific year. Currently, the noise data for MRTJ from 2018, 2019, and 2020 are available.</div>

    <div class="section-title">2. Bar Chart</div>
    <div class="content">View the average and maximum noise levels for station pairs. You can also use the minimum speed label to filter and check noise data above a specific speed.</div>

    <div class="section-title">3. Line Chart</div>
    <div class="content">Observe the noise and speed data as line charts based on distance. This allows you to easily identify the correlation between the two indicators.</div>
    """, unsafe_allow_html=True)

# 각 기능의 이점 및 의사결정 연결점
with st.expander('Benefits of Each Feature and Its Connection to Decision-Making', expanded=True):
    st.markdown("""
    <div class="big-title">Benefits of Each Feature and Its Connection to Decision-Making</div>

    <div class="section-title">1. Sidebar</div>
    <div class="content"><b>Benefit:</b> Allows for customized data analysis, making it easy to explore data by year.</div>
    <div class="content"><b>Decision-Making Connection:</b> Comparing data by year helps identify specific noise issues during certain periods and determine when maintenance plans may be necessary.</div>

    <div class="section-title">2. Bar Chart</div>
    <div class="content"><b>Benefit:</b> Displays the average and maximum values clearly, allowing for intuitive identification of noise issues in specific sections. The minimum speed filter helps focus on noise data occurring in high-speed areas.</div>
    <div class="content"><b>Decision-Making Connection:</b> Helps assess whether noise issues in high-speed sections between specific stations are critical, guiding decisions on facility inspections and track maintenance needs.</div>

    <div class="section-title">3. Line Chart</div>
    <div class="content"><b>Benefit:</b> Provides a visual representation of the relationship between noise and speed based on distance.</div>
    <div class="content"><b>Decision-Making Connection:</b> Helps identify whether noise increases at specific speeds or distances, allowing for adjustments to train speeds and the development of noise management strategies for each section.</div>
    """, unsafe_allow_html=True)
