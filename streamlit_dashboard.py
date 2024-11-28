import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 데이터 처리 클래스
class StationDataProcessor:
    def __init__(self, data_frame):
        """
        CSV 데이터를 받아 역 쌍 및 거리 데이터를 초기화합니다.
        """
        self.data_frame = data_frame
        self.codes = data_frame['code'].values
        self.station_distances = data_frame['station distance'].values

        # 역 쌍 생성
        self.station_pairs = []  # 역 쌍 리스트
        self.station_btw_distance = []  # 역 거리 리스트
        self.create_station_pairs()

    def create_station_pairs(self):
        """
        역 쌍과 거리 범위를 생성합니다.
        """
        for i in range(len(self.codes) - 1):
            if pd.isna(self.codes[i]) or pd.isna(self.codes[i + 1]) or pd.isna(self.station_distances[i]) or pd.isna(self.station_distances[i + 1]):
                continue
            pair = f"{self.codes[i]} - {self.codes[i + 1]}"  # 역 코드로 쌍 생성
            self.station_pairs.append(pair)
            self.station_btw_distance.append((self.station_distances[i], self.station_distances[i + 1]))

    def get_station_intervals(self, min_speed):
        """
        역 쌍에 대한 평균 소음과 최대 소음을 계산합니다.
        """
        station_intervals = []  # 역 구간 정보를 저장
        for pair, (start_distance, end_distance) in zip(self.station_pairs, self.station_btw_distance):
            # 구간 데이터 필터링
            segment = self.data_frame[
                (self.data_frame['distance'] >= start_distance) &
                (self.data_frame['distance'] <= end_distance) &
                (self.data_frame['speed'] >= min_speed)
            ]
            # 평균 및 최대 소음 계산
            avg_noise = segment['dB'].mean() if not segment.empty else 0
            max_noise = segment['dB'].max() if not segment.empty else 0
            station_intervals.append({
                'Station Pair': pair,
                'Average Noise (dBA)': avg_noise,
                'Maximum Noise (dBA)': max_noise
            })
        return pd.DataFrame(station_intervals)

# Streamlit 애플리케이션 시작
st.title("Noise Monitoring Dashboard")

# 드롭다운 옵션에 사용할 CSV 파일들
csv_files = {
    "Norting_avg": "https://github.com/mugissi/noise_dashboard_app/blob/main/20_Northing_avg.csv"
}

# 드롭다운 메뉴에서 파일 선택
selected_file = st.selectbox("Select a CSV file:", options=list(csv_files.keys()))

if selected_file:
    try:
        # 선택된 파일 읽기
        file_path = csv_files[selected_file]
        data = pd.read_csv(file_path)

        # 데이터 프로세싱
        processor = StationDataProcessor(data)

        # 최소 속도 입력
        min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=300, value=70)

        # 역 구간 데이터 계산
        station_intervals_df = processor.get_station_intervals(min_speed)

        # 그래프 생성
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=station_intervals_df['Station Pair'],
            y=station_intervals_df['Maximum Noise (dBA)'],
            name='Maximum Noise (dBA)',
            marker_color='darkred'
        ))
        fig.add_trace(go.Bar(
            x=station_intervals_df['Station Pair'],
            y=station_intervals_df['Average Noise (dBA)'],
            name='Average Noise (dBA)',
            marker_color='gray'
        ))
        fig.update_layout(
            title=f"Average and Maximum Noise Levels at Speed Above {min_speed} km/h",
            xaxis_title="Station Pair",
            yaxis_title="Noise Level (dBA)",
            barmode='group'
        )

        # 그래프 출력
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please select a CSV file to display the data.")
