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

    # Add a slider to filter distance range
    min_distance, max_distance = st.slider(
        "Select Distance Range (m):",
        min_value=int(df['distance'].min()),
        max_value=int(df['distance'].max()),
        value=(int(df['distance'].min()), int(df['distance'].max()))
    )

# Filter the dataframe based on the selected distance range
filtered_df = df[(df['distance'] >= min_distance) & (df['distance'] <= max_distance)]

# 데이터 준비 클래스 정의
class StationDataProcessor:
    def __init__(self, df):
        """
        주어진 CSV 데이터프레임을 초기화합니다.
        """
        self.data_frame = df
        self.codes = self.data_frame['code'].values
        self.stations = self.data_frame['station'].values
        self.station_distances = self.data_frame['station distance'].values
        self.distances = self.data_frame['distance'].values
        self.dBs = self.data_frame['dB'].values
        self.speeds = self.data_frame['speed'].values

    def get_filtered_data(self, min_speed):
        """
        속도 기준으로 데이터를 필터링하는 메서드
        """
        filtered_data = self.data_frame[self.data_frame['speed'] >= min_speed]
        return filtered_data

# Streamlit 애플리케이션
st.title("Noise Monitoring Dashboard")

# 데이터 프로세싱
processor = StationDataProcessor(df)

# 최소 속도를 사용자 입력으로 받음
min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=300, value=70)

# 필터링된 데이터 가져오기
filtered_data = processor.get_filtered_data(min_speed)

# Dashboard Main Panel
col = st.columns((2, 1), gap='medium')  # 순서를 바꿔서 1열이 막대그래프, 2열이 라인차트
with col[0]:
    # 그래프 생성
    fig = go.Figure()

    # 기존 막대그래프 코드...
    
    st.plotly_chart(fig, use_container_width=True)

    # Line chart below the bar chart with Distance vs dB
    line_fig = go.Figure()

    # 라인 차트 (distance vs dB)
    line_fig.add_trace(go.Scatter(
        x=filtered_data['distance'],
        y=filtered_data['dB'],
        mode='lines+markers',
        name='Noise Level (dBA)',
        line=dict(color='blue'),
        marker=dict(color='blue')
    ))

    line_fig.update_layout(
        title="Noise Level vs Distance",
        xaxis_title="Distance (m)",
        yaxis_title="Noise Level (dBA)",
        showlegend=True
    )
    
    st.plotly_chart(line_fig, use_container_width=True)

# About section
with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Adjust filters to explore specific ranges of data.")
        st.write("3. Analyze the graphs for insights on noise levels and speed.")
