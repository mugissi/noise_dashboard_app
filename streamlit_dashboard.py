import subprocess
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# Streamlit 페이지 설정
st.set_page_config(
    page_title="Noise Monitoring Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit Secrets에서 GPG 비밀번호 불러오기
gpg_password = st.secrets["general"]["GPG_PASSWORD"]

# 암호화된 파일 경로 및 복호화된 출력 파일 경로 설정
encrypted_file_paths = {
    '19_M1_S25_9002.csv': 'https://path_to_encrypted_file/19_M1_S25_9002.csv.gpg',
    '20_Northing_avg.csv': 'https://path_to_encrypted_file/20_Northing_avg.csv.gpg'
}

# 사이드바 설정
with st.sidebar:
    st.header("Noise Monitoring Dashboard")

    # 드롭다운 메뉴로 암호화된 CSV 파일 선택
    selected_encrypted_file = st.selectbox(
        'Select an Encrypted CSV file:', list(encrypted_file_paths.keys())
    )
    
    # 선택된 암호화된 파일 경로
    encrypted_file_url = encrypted_file_paths[selected_encrypted_file]
    decrypted_file = f"decrypted_{selected_encrypted_file}"

    # GPG 복호화 명령 실행
    command = f"echo {gpg_password} | gpg --batch --yes --passphrase-fd 0 -o {decrypted_file} -d {encrypted_file_url}"
    
    try:
        # GPG 복호화 실행
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        st.write("Decryption successful.")
        st.write(result.stdout)  # stdout 출력 확인
    except subprocess.CalledProcessError as e:
        st.error(f"GPG command failed: {e}")
        st.write(f"stderr: {e.stderr}")
        st.write(f"stdout: {e.stdout}")
        st.stop()  # 오류 발생 시 실행 중지

    # 복호화된 CSV 파일 읽기
    df = pd.read_csv(decrypted_file)

    # 거리 범위 필터 슬라이더
    min_distance, max_distance = st.slider(
        "Select Distance Range (m):",
        min_value=int(df['distance'].min()),
        max_value=int(df['distance'].max()),
        value=(int(df['distance'].min()), int(df['distance'].max()))
    )

# 선택된 거리 범위에 맞춰 데이터 필터링
filtered_df = df[(df['distance'] >= min_distance) & (df['distance'] <= max_distance)]

# StationDataProcessor 클래스 정의
class StationDataProcessor:
    def __init__(self, file_path):
        """
        CSV 파일을 로드하고 역 코드 및 거리 데이터를 초기화합니다.
        """
        self.data_frame = pd.read_csv(file_path)
        self.codes = self.data_frame['code'].values
        self.station_distances = self.data_frame['station distance'].values

    def create_station_pairs(self):
        """
        역 쌍을 생성하고 NaN 값을 건너뛰어 역 쌍과 거리를 반환합니다.
        """
        station_pairs = []
        station_btw_distance = []
        
        for i in range(len(self.codes) - 1):
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"
            distance_pair = (self.station_distances[i], self.station_distances[i + 1])
            station_pairs.append(pair)
            station_btw_distance.append(distance_pair)

        return station_pairs, station_btw_distance

    def get_matching_data(self, station_pairs, station_btw_distance, df):
        """
        역 쌍에 맞는 거리 범위에서의 'distance', 'dB', 'speed' 데이터를 필터링하여
        'Station Pair'와 함께 반환합니다.
        """
        matched_distances = []
        
        for pair, (start_distance, end_distance) in zip(station_pairs, station_btw_distance):
            matching_data = df[(df['distance'] >= start_distance) & (df['distance'] <= end_distance)]
            matched_distances.append({
                'Station Pair': pair,
                'Matching Distances': matching_data[['distance', 'dB', 'speed']].values,
                'Average dB': np.mean(matching_data['dB']),
                'Max dB': np.max(matching_data['dB'])
            })
        
        return matched_distances

# 데이터 처리
processor = StationDataProcessor(decrypted_file)
station_pairs, station_btw_distance = processor.create_station_pairs()
matched_distances = processor.get_matching_data(station_pairs, station_btw_distance, df)

# 평균 dB 및 역 쌍 데이터를 DataFrame으로 변환
graph_data = pd.DataFrame({
    "Station Pair": [item['Station Pair'] for item in matched_distances],
    "Average dB": [item['Average dB'] for item in matched_distances]
})

# 대시보드 메인 화면
col = st.columns((2, 1), gap='medium')

with col[0]:
    # 필터링된 데이터로 그래프 그리기
    if 'df' in locals() and df is not None:
        fig = go.Figure()
        
        # Noise Level (dB) 그래프
        fig.add_trace(go.Scatter(
            x=filtered_df['distance'],
            y=filtered_df['dB'],
            mode='lines',
            name='Noise Level (dB)',
            yaxis="y1"
        ))
        
        # Speed (km/h) 그래프
        fig.add_trace(go.Scatter(
            x=filtered_df['distance'],
            y=filtered_df['speed'],
            mode='lines',
            name='Speed (km/h)',
            yaxis="y2"
        ))
        
        # 그래프 레이아웃 설정
        fig.update_layout(
            title="Noise Levels and Speed Over Distance",
            xaxis=dict(title="Distance (m)"),
            yaxis=dict(title="Noise Level (dB)", side="left"),
            yaxis2=dict(title="Speed (km/h)", overlaying="y", side="right"),
            height=600
        )
        
        st.title("Noise Levels and Speed Dashboard")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Insights:")
        st.write("Analyze the relationship between noise levels and speed across distances.")
    else:
        st.info("No data available. Please select a CSV file.")

# 막대 그래프 표시
st.bar_chart(graph_data.set_index("Station Pair"))

# 오른쪽 패널 (대시보드 정보)
with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Adjust filters to explore specific ranges of data.")
        st.write("3. Analyze the graphs for insights on noise levels and speed.")
