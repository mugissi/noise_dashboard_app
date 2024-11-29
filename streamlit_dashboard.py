import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import subprocess
from geopy.distance import geodesic

# 페이지 설정
st.set_page_config(
    page_title="Noise Monitoring Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GitHub에서 CSV 파일을 읽기 위한 URL 설정
csv_file_paths = {
    '19_M1_S25_9002.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/noise.app/19_M1_S25_9002.csv.gpg',
    '20_Northing_avg.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/noise.app/20_Northing_avg.csv.gpg',
    'ip_coordinate.csv.gpg' : 'https://github.com/mugissi/noise_dashboard_app/raw/main/ip%2Ccoordinate.csv.gpg'
}

# Streamlit Secrets에서 비밀번호 가져오기
gpg_password = st.secrets["general"]["GPG_PASSWORD"]

# 사이드바 설정
with st.sidebar:
    st.header("Noise Monitoring Dashboard")

    # 파일 선택 박스
    selected_csv_name = st.sidebar.selectbox(
        'Select an Encrypted CSV file:', ['19_M1_S25_9002.csv.gpg', '20_Northing_avg.csv.gpg']
    )
    selected_csv_url = csv_file_paths[selected_csv_name]  # 선택한 파일 URL

    # 복호화된 파일 이름 설정
    encrypted_file = selected_csv_name
    decrypted_file = f"decrypted_{selected_csv_name.replace('.gpg', '.csv')}"  # 복호화된 파일 이름

    # GPG 복호화 명령 실행
    command = f"echo {gpg_password} | gpg --batch --yes --passphrase-fd 0 -o {decrypted_file} -d {encrypted_file}"
    subprocess.run(command, shell=True, check=True)

    # 복호화된 CSV 파일 읽기
    df = pd.read_csv(decrypted_file)

# 데이터 처리 클래스 정의
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
        filtered_data = self.data_frame[self.data_frame['speed'] >= min_speed]
        return filtered_data

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

# Streamlit 애플리케이션
st.title("Noise Monitoring Dashboard")

# 데이터 프로세싱
processor = StationDataProcessor(df)

# 사이드바에서 필터링할 속도 값 설정
min_speed = st.sidebar.number_input("Minimum Speed (km/h):", min_value=0, max_value=100, value=50, key="speed_input", help="Set the minimum speed to filter data.")

# 필터링된 데이터 및 그에 맞는 station intervals 계산
filtered_data = processor.get_filtered_data(min_speed)
station_intervals_df = processor.get_station_intervals(filtered_data)

# 메인 화면
col1, col2 = st.columns([1, 3])

with col1:
    # 최대 소음과 평균 소음에 대한 바 차트 생성
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
        title=f"Average and Maximum Noise Levels at Speed Above {min_speed} km/h",
        xaxis_title="Station",
        yaxis_title="Noise Level (dBA)",
        barmode='overlay'
    )
    st.plotly_chart(fig, use_container_width=True)

    # 소음 레벨과 속도에 따른 라인 차트 생성
    line_fig = go.Figure()
    line_fig.add_trace(go.Scatter(
        x=df['distance'],
        y=df['dB'],
        mode='lines',
        name='Noise Level (dB)',
        yaxis="y1"
    ))
    line_fig.add_trace(go.Scatter(
        x=df['distance'],
        y=df['speed'],
        mode='lines',
        name='Speed (km/h)',
        yaxis="y2"
    ))
    line_fig.update_layout(
        title="Noise Levels and Speed Over Distance",
        xaxis=dict(title="Distance (m)"),
        yaxis=dict(title="Noise Level (dB)", side="left"),
        yaxis2=dict(title="Speed (km/h)", overlaying="y", side="right"),
        height=600
    )
    st.plotly_chart(line_fig, use_container_width=True)

with col2:
    # 지도 관련 클래스 설정 (기본적으로 지도 표시만)
    class MRTMap:
        def __init__(self, coord_df, noise_df):
            self.df = coord_df
            self.noise_data = noise_df
            self.lat_lon_coords = []  # 좌표 추출
            self.station_names = []  # 역 이름 추출
            self.station_noise_statistics_df = noise_df
            self.split_coords = []

        def calculate_distance(self, coord1, coord2):
            return geodesic(coord1, coord2).meters

        def split_line(self, start, end, num_points):
            latitudes = np.linspace(start[0], end[0], num_points)
            longitudes = np.linspace(start[1], end[1], num_points)
            return list(zip(latitudes, longitudes))

        def calculate_split_coords(self):
            for i in range(len(self.lat_lon_coords) - 1):
                start = self.lat_lon_coords[i]
                end = self.lat_lon_coords[i + 1]
                distance = self.calculate_distance(start, end)
                num_points = int(distance) + 1
                self.split_coords.extend(self.split_line(start, end, num_points))

        def map_noise_data(self):
            avg_noise = self.noise_data['dB'].mean()
            mapped_noise_data = []
            for i, (split_coord, distance) in enumerate(zip(self.split_coords, self.station_distances)):
                tolerance = 5
                if abs(distance - self.station_distances[i]) > tolerance:
                    distance = self.station_distances[i]
                noise = self.noise_data.get(distance, avg_noise)
                mapped_noise_data.append({
                    'coord': split_coord,
                    'distance': distance,
                    'noise': noise
                })
            return mapped_noise_data

        def create_map(self, mapped_noise_data):
            latitudes = [lat for lat, lon in mapped_noise_data]
            longitudes = [lon for lat, lon in mapped_noise_data]
            noise_values = [data['noise'] for data in mapped_noise_data]

            fig = px.scatter_mapbox(
                lat=latitudes,
                lon=longitudes,
                color=noise_values,
                size_max=10,
                color_continuous_scale='Viridis',
                labels={'color': 'Noise Level (dBA)'},
                title="Noise Levels along the MRT"
            )
            fig.update_layout(mapbox_style="carto-positron")
            st.plotly_chart(fig)

# 결과 매핑 후 지도 시각화
coord_df = pd.read_csv(csv_file_paths["ip_coordinate.csv.gpg"])
mapped_noise_data = MRTMap(coord_df, station_intervals_df).map_noise_data()
MRTMap(coord_df, station_intervals_df).create_map(mapped_noise_data)
