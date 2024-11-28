# Streamlit 애플리케이션
st.title("Noise Monitoring Dashboard")

# 최소 속도를 사용자 입력으로 받음
st.markdown("### Minimum Speed (km/h):")
min_speed = st.number_input("Minimum Speed (km/h):", min_value=0, max_value=100, value=50)

# 데이터 프로세싱
processor = StationDataProcessor(df)

# min_speed를 기준으로 필터링된 데이터 가져오기
filtered_data = processor.get_filtered_data(min_speed)
station_intervals_df = processor.get_station_intervals(filtered_data)

# Dashboard Main Panel
col = st.columns((2, 1), gap='medium')  # 1열은 막대그래프, 2열은 라인차트
with col[0]:
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

    st.plotly_chart(fig, use_container_width=True)

    # 라인 차트 (distance vs dB)
    line_fig = go.Figure()

    # Plot Noise Level (dB)
    line_fig.add_trace(go.Scatter(
        x=filtered_data['distance'],
        y=filtered_data['dB'],
        mode='lines',
        name='Noise Level (dB)',
        yaxis="y1"
    ))

    # Plot Speed (km/h)
    line_fig.add_trace(go.Scatter(
        x=filtered_data['distance'],
        y=filtered_data['speed'],
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

# About section
with col[1]:
    with st.expander('About', expanded=True):
        st.write("1. Use the sidebar to select a CSV file.")
        st.write("2. Adjust filters to explore specific ranges of data.")
        st.write("3. Analyze the graphs for insights on noise levels and speed.")
