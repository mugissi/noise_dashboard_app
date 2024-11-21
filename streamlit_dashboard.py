import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import requests

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
                'Matching Distances': matching_data[['distance', 'dB', 'speed']].values,
                'Average dB': np.mean(matching_data['dB']),  # 평균 dB
                'Max dB': np.max(matching_data['dB'])  # 최댓값 dB
            })
        
        return matched_distances

# Streamlit 시작
st.title("Average Noise Levels by Station Pair")

# 암호화된 파일 GitHub URL
ENCRYPTED_FILE_URL = "https://github.com/your-username/your-repo/raw/main/your_data.csv.gpg"
ENCRYPTED_FILE_PATH = "your_data.csv.gpg"
DECRYPTED_FILE_PATH = "your_data.csv"

# 1. GitHub에서 암호화된 파일 다운로드
response = requests.get(ENCRYPTED_FILE_URL)
if response.status_code == 200:
    with open(ENCRYPTED_FILE_PATH, "wb") as file:
        file.write(response.content)
    st.success("Encrypted file downloaded successfully!")
else:
    st.error("Failed to download the encrypted file.")

# 2. 비밀번호로 복호화
password = st.text_input("Enter the decryption password:", type="password")
if password:
    command = [
        "gpg", "--batch", "--yes", "--passphrase", password,
        "--output", DECRYPTED_FILE_PATH, "--decrypt", ENCRYPTED_FILE_PATH
    ]
    try:
        subprocess.run(command, check=True)
        st.success("File decrypted successfully!")
        
        # 3. 복호화된 CSV 파일 읽기
        processor = StationDataProcessor(DECRYPTED_FILE_PATH)
        station_pairs, station_btw_distance = processor.create_station_pairs()
        df = pd.read_csv(DECRYPTED_FILE_PATH)
        matched_distances = processor.get_matching_data(station_pairs, station_btw_distance, df)

        # `matched_distances`에서 Station Pair와 Average dB 데이터 추출
        graph_data = pd.DataFrame({
            "Station Pair": [item['Station Pair'] for item in matched_distances],
            "Average dB": [item['Average dB'] for item in matched_distances]
        })

        # 막대그래프 그리기
        st.bar_chart(graph_data.set_index("Station Pair"))
    except subprocess.CalledProcessError:
        st.error("Decryption failed. Please check your password.")
