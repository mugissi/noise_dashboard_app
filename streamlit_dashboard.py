import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import subprocess
import requests
from io import StringIO
import os

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

    try:
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

    except Exception as e:
        st.error(f"Error during decryption or CSV loading: {e}")
        df = pd.DataFrame()  # 에러 발생 시 빈 데이터프레임 생성

# Filter the dataframe based on the selected distance range
if not df.empty:
    filtered_df = df[(df['distance'] >= min_distance) & (df['distance'] <= max_distance)]
else:
    filtered_df = pd.DataFrame()  # df가 비어있으면 빈 데이터프레임 생성

# 데이터 준비 클래스 정의
class StationDataProcessor:
    def __init__(self, file_url):
        """
        GitHub에서 CSV 파일을 다운로드하고 역 코드 및 거리 데이터를 초기화합니다.
        """
        # GitHub에서 파일 다운로드
        response = requests.get(file_url)
        if response.status_code != 200:
            raise Exception(f"Failed to download file: {file_url}")

        content = response.text  # CSV 파일의 텍스트 내용

        # CSV 데이터 프레임으로 변환
        self.data_frame = pd.read_csv(StringIO(content))
        self.codes = self.data_frame['code'].values
        self.stations = self.data_frame['station'].values
        self.station_distances = self.data_frame['station distance'].values
        self.distances = self.data_frame['distance'].values
        self.dBs = self.data_frame['dB'].values
        self.speeds = self.data_frame['speed'].values

        # 역 쌍 생성
        self.station_pairs = []  # 역 쌍 리스트
        self.station_btw_distance = []  # 역 거리 리스트
        self.create_station_pairs()

    def create_station_pairs(self):
        """
        역 쌍을 생성하는 메서드입니다.
        NaN 값을 건너뛰고, 역 쌍 및 거리 값을 저장합니다.
        """
        for i in range(len(self.codes) - 1):
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"  # 역 코드로 쌍 만들기
            distance_pair = (self.station_distances[i], self.station_distances[i + 1])  # 해당 역쌍의 거리 값
            self.station_pairs.append(pair)
            self.station_btw_distance.append(distance_pair)

    def get_filtered_data(self, df, min_speed):
        """
        속도 기준으로 데이터를 필터링하는 메서드
        """
        filtered_data = df[df['speed'] >= min_speed]
        return filtered_data

    def get_station_intervals(self, filtered_data):
        """
        역쌍에 대해 평균 소음과 최대 소음을 계산하는 메서드
        """
        station_intervals = []  # 역 구간 정보를 저장할 리스트 초기화
        for pair, (start_distance, end_distance) in zip(self.station_pairs, self.station_btw_distance):
            # 역 쌍에 맞는 데이터 필터링
            main_line_between = filtered_data[(filtered_data['distance'] >= start_distance) & (filtered_data['distance'] <= end_distance)]
            if not main_line_between.empty:  # 필터링된 데이터가 비어 있지 않으면
                average_noise = main_line_between['dB'].mean()  # 평균 소음 계산
                maximum_noise = main_line_between['dB'].max()  # 최대 소음 계산
            else:  # 데이터가 비어 있으면
                average_noise = 0  # 평균 소음 0으로 설정
                maximum_noise = 0  # 최대 소음 0으로 설정
            station_intervals.append({  # 역 구간 정보를 리스트에 추가
                'Station Pair': pair,  # 역 쌍
                'Average Noise (dBA)': average_noise,  # 평균 소음
                'Maximum Noise (dBA)': maximum_noise  # 최대 소음
            })
        return pd.DataFrame(station_intervals)

# Dashboard Main Panel
col = st.columns((2, 1), gap='medium')  # 순서를 바꿔서 1열이 막대그래프, 2열이 라인차트

with col[0]:
    try:
        # 최소 속도를 사용자 입력으로 받음
        min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=300, value=70)

        # 필터링된 데이터와 역 구간 데이터를 가져오기
        processor = StationDataProcessor(selected_csv_url)  # GitHub URL을 사용하여 데이터 로딩
        filtered_data = processor.get_filtered_data(df, min_speed)
        station_intervals_df = processor.get_station_intervals(filtered_data)

        # 그래프 생성
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

        # Streamlit에서 그래프 표시
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Adjust filters to explore specific ranges of data.")
        st.write("3. Analyze the graphs for insights on noise levels and speed.")
