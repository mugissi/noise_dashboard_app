import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# 데이터 준비 클래스 정의
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
        NaN 값을 건너뛰고, 역 쌍 및 거리 값을 저장합니다.
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
                'Average dB': np.mean(matching_data['dB']),  # 평균 dB
                'Max dB': np.max(matching_data['dB'])  # 최댓값 dB
            })

        return matched_distances

# Streamlit 애플리케이션
st.title("Noise Monitoring Dashboard")
file_path = st.text_input("Enter CSV File Path:", "/content/drive/MyDrive/mrt/data extraction/20_Northing_avg.csv")

if file_path:
    try:
        # 데이터 프로세싱
        processor = StationDataProcessor(file_path)

        # 역 쌍 생성
        station_pairs, station_btw_distance = processor.create_station_pairs()

        # 데이터 로드 (CSV 파일)
        df = pd.read_csv(file_path)

        # 역쌍에 해당하는 거리, dB, speed 데이터를 가져옵니다.
        matched_distances = processor.get_matching_data(station_pairs, station_btw_distance, df)

        # `matched_distances`에서 Station Pair와 Average dB 데이터 추출
        graph_data = pd.DataFrame({
            "Station Pair": [item['Station Pair'] for item in matched_distances],
            "Average Noise (dBA)": [item['Average dB'] for item in matched_distances],
            "Maximum Noise (dBA)": [item['Max dB'] for item in matched_distances],
        })

        # 최소 속도를 사용자 입력으로 받음
        min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=300, value=70)

        # 그래프 생성
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=graph_data['Station Pair'],
            y=graph_data['Maximum Noise (dBA)'],
            name='Maximum Noise (dBA)',
            marker_color='#808080'
        ))
        fig.add_trace(go.Bar(
            x=graph_data['Station Pair'],
            y=graph_data['Average Noise (dBA)'],
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
else:
    st.info("Enter a valid CSV file path to start.")
