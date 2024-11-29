import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import subprocess
from geopy.distance import geodesic
from pyproj import Proj

# GitHub에서 CSV 파일을 읽기 위한 URL 설정
csv_file_paths = {
    '19_M1_S25_9002.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/noise.app/19_M1_S25_9002.csv.gpg',
    '20_Northing_avg.csv.gpg': 'https://github.com/mugissi/noise_dashboard_app/raw/noise.app/20_Northing_avg.csv.gpg',
    'ip_coordinate.csv': 'https://github.com/mugissi/noise_dashboard_app/raw/main/ip%2Ccoordinate.csv'  # GPG 복호화 없이 .csv 파일을 읽음
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

    # CSV 파일을 직접 다운로드하여 읽기 (coordinate.csv만 복호화 없이 읽기)
    if selected_csv_name == 'ip_coordinate.csv':  # coordinate.csv는 복호화 없이 읽기
        df = pd.read_csv(selected_csv_url)
    else:
        # 암호화된 파일을 다운로드 후 GPG 복호화 실행
        encrypted_file = selected_csv_name
        decrypted_file = f"/tmp/decrypted_{selected_csv_name.replace('.gpg', '.csv')}"  # 복호화된 파일 이름 설정

        # GPG 복호화 명령 실행
        command = f"echo {gpg_password} | gpg --batch --yes --passphrase-fd 0 -o {decrypted_file} -d {encrypted_file}"
        subprocess.run(command, shell=True, check=True)

        # 복호화된 CSV 파일 읽기
        df = pd.read_csv(decrypted_file)

# MRTMap 클래스
class MRTMap:
    def __init__(self, coord_df, noise_df):
        self.df = coord_df
        self.noise_data = noise_df
        self.lat_lon_coords = []  # 위도/경도 좌표를 저장할 리스트
        self.station_names = []  # 역 이름을 저장할 리스트
        self.total_distance = 0  # 전체 거리 초기화
        self.station_noise_statistics_df = noise_df
        self.split_coords = []  # 분할된 좌표를 저장할 리스트

    def utm_to_latlon(self, easting, northing, zone_number=48, northern=False):
        """
        UTM 좌표를 위도/경도로 변환.
        """
        proj_utm = Proj(proj="utm", zone=zone_number, ellps="WGS84", south=not northern)
        lon, lat = proj_utm(easting, northing, inverse=True)
        return lat, lon

    def process_coordinates(self, coord_df):
        """
        UTM 좌표를 위도/경도로 변환하여 저장.
        """
        for index, row in coord_df.iterrows():
            if pd.notnull(row['Easting/X (m)']) and pd.notnull(row['Northing/Y (m)']):
                easting = row['Easting/X (m)']
                northing = row['Northing/Y (m)']
                lat_lon = self.utm_to_latlon(easting, northing)  # 변환 수행
                self.lat_lon_coords.append(lat_lon)  # 변환된 좌표 저장

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
        latitudes = [lat for lat, _ in self.lat_lon_coords]
        longitudes = [lon for _, lon in self.lat_lon_coords]

        fig = px.scatter_mapbox(
            lat=latitudes,
            lon=longitudes,
            zoom=10,
            height=800,
            width=400,
            title="MRTJ Line with Noise Levels",
            labels={'lat': 'Latitude', 'lon': 'Longitude'},
        )

        fig.update_layout(
            mapbox_style="carto-positron",
            plot_bgcolor='lightgray',
            paper_bgcolor='lightgray',
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )

        fig.add_scattermapbox(
            lat=latitudes,
            lon=longitudes,
            mode='markers',
            marker=dict(size=10, color='red', opacity=0.8),
            text=self.station_names
        )

        return fig


# 데이터프레임을 적절히 처리한 후, UTM 좌표 변환을 수행하고, 맵을 생성하는 코드입니다.
# station_intervals_df 데이터프레임 준비
station_intervals_df = df  # 예시로 df와 동일하게 설정

# MRTMap 인스턴스 생성 후 처리
mrt_map = MRTMap(df, station_intervals_df)
mrt_map.process_coordinates(df)  # UTM 좌표 변환
mrt_map.calculate_split_coords()  # 좌표 분할 계산

# 맵 생성
mapped_noise_data = mrt_map.map_noise_data()  # 변환된 좌표에 대한 소음 데이터 매핑

# 맵 표시
st.plotly_chart(mrt_map.create_map(mapped_noise_data))
