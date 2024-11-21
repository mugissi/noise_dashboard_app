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
        역 쌍을 생성하는 메서드입니다.
        NaN 값을 건너뜁니다.
        """
        station_pairs = []  # 역 쌍을 저장할 리스트
        station_btw_distance = []  # 역 거리 값을 저장할 리스트
        
        for i in range(len(self.codes) - 1):
            # NaN 또는 빈 값이 있는 경우 건너뜁니다.
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"  # 역 코드로 쌍 만들기
            distance_pair = (self.station_distances[i], self.station_distances[i + 1])  # 해당 역쌍의 거리 값
            station_pairs.append(pair)
            station_btw_distance.append(distance_pair)

        return station_pairs, station_btw_distance  # 역 쌍 및 거리 반환
    
    def get_matching_data(self, station_pairs, station_btw_distance, df):
        """
        역 쌍에 해당하는 거리 범위에 맞는 거리, dB, speed 데이터를 필터링하여
        'Station Pair'와 함께 반환합니다.
        """
        matched_distances = []  # 최종 결과를 저장할 리스트
        
        for pair, (start_distance, end_distance) in zip(station_pairs, station_btw_distance):
            # 해당 역쌍의 거리 범위에 맞는 데이터 필터링
            matching_data = df[(df['distance'] >= start_distance) & (df['distance'] <= end_distance)]
            
            # 필터링된 'distance', 'dB', 'speed' 데이터를 리스트에 추가
            matched_distances.append({
                'Station Pair': pair,
                'Matching Distances': matching_data[['distance', 'dB', 'speed']].values,
                'Average dB': np.mean(matching_data['dB']),  # 평균 dB
                'Max dB': np.max(matching_data['dB'])  # 최댓값 dB
            })
        
        return matched_distances

# 데이터 프로세싱
processor = StationDataProcessor(decrypted_file)
station_pairs, station_btw_distance = processor.create_station_pairs()
matched_distances = processor.get_matching_data(station_pairs, station_btw_distance, df)

# `matched_distances`에서 Station Pair와 Average dB 데이터 추출
graph_data = pd.DataFrame({
    "Station Pair": [item['Station Pair'] for item in matched_distances],
    "Average dB": [item['Average dB'] for item in matched_distances]
})

# Station Pair의 순서를 맞추기 위해 Categorical 사용
graph_data['Station Pair'] = pd.Categorical(graph_data['Station Pair'], categories=graph_data['Station Pair'], ordered=True)

# Dashboard Main Panel
col = st.columns((2, 1), gap='medium')  # 순서를 바꿔서 1열이 막대그래프, 2열이 라인차트

with col[0]:
    # 막대그래프 그리기
    st.bar_chart(graph_data.set_index("Station Pair"))
    

    if 'df' in locals() and df is not None:
        fig = go.Figure()
        
        # Plot Noise Level (dB)
        fig.add_trace(go.Scatter(
            x=filtered_df['distance'],
            y=filtered_df['dB'],
            mode='lines',
            name='Noise Level (dB)',
            yaxis="y1"
        ))
        
        # Plot Speed (km/h)
        fig.add_trace(go.Scatter(
            x=filtered_df['distance'],
            y=filtered_df['speed'],
            mode='lines',
            name='Speed (km/h)',
            yaxis="y2"
        ))
        
        # Update layout with dual y-axes
        fig.update_layout(
            title="Noise Levels and Speed Over Distance",
            xaxis=dict(title="Distance (m)"),
            yaxis=dict(title="Noise Level (dB)", side="left"),
            yaxis2=dict(title="Speed (km/h)", overlaying="y", side="right"),
            height=600  # width removed
        )
        
        st.title("Noise Levels and Speed Dashboard")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Insights:")
        st.write("Analyze the relationship between noise levels and speed across distances.")
    else:
        st.info("No data available. Please select a CSV file.")
with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Adjust filters to explore specific ranges of data.")
        st.write("3. Analyze the graphs for insights on noise levels and speed.")
