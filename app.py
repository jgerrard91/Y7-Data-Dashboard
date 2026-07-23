import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="Year 7 Performance Dashboard", layout="wide")

st.title("🎓 Year 7 Academic Performance & Progress Dashboard")
st.markdown("Filter student cohorts dynamically using the sidebar options.")

# 2. Load Data Function
@st.cache_data
def load_data():
    df = pd.read_csv('Y7 All Data 070726 - FFT20.csv')
    df['% Attendance'] = pd.to_numeric(df['% Attendance'], errors='coerce')
    return df

df = load_data()

# 3. Sidebar Filters
st.sidebar.header("🔍 Cohort Filters")

# Tutor Group Filter
reg_groups = ['All'] + sorted([x for x in df['Reg Group'].dropna().unique()])
selected_reg = st.sidebar.selectbox("Registration Group", reg_groups)

# Pupil Premium Filter
pp_options = ['All', 'Pupil Premium (Y)', 'Non-Pupil Premium (N)']
selected_pp = st.sidebar.selectbox("Pupil Premium Status", pp_options)

# SEN Filter
sen_options = ['All', 'SEN Only', 'Non-SEN']
selected_sen = st.sidebar.selectbox("SEN Status", sen_options)

# Attendance Filter
min_att, max_att = int(df['% Attendance'].min()), int(df['% Attendance'].max())
att_range = st.sidebar.slider("Attendance Range (%)", min_att, max_att, (min_att, max_att))

# 4. Filter Application
filtered_df = df.copy()

if selected_reg != 'All':
    filtered_df = filtered_df[filtered_df['Reg Group'] == selected_reg]

if selected_pp == 'Pupil Premium (Y)':
    filtered_df = filtered_df[filtered_df['Pupil Premium Indicator'] == 'Y']
elif selected_pp == 'Non-Pupil Premium (N)':
    filtered_df = filtered_df[filtered_df['Pupil Premium Indicator'].isna()]

if selected_sen == 'SEN Only':
    filtered_df = filtered_df[filtered_df['SEN Status'].notna() & (filtered_df['SEN Status'] != 'N')]
elif selected_sen == 'Non-SEN':
    filtered_df = filtered_df[filtered_df['SEN Status'].isna() | (filtered_df['SEN Status'] == 'N')]

filtered_df = filtered_df[(filtered_df['% Attendance'] >= att_range[0]) & (filtered_df['% Attendance'] <= att_range[1])]

# 5. Top Key Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Selected Pupils", len(filtered_df))
m2.metric("Mean Attendance", f"{filtered_df['% Attendance'].mean():.1f}%" if len(filtered_df) > 0 else "N/A")

# 6. Subject Calculations
subject_names = ['English', 'Maths', 'Science', 'Drama', 'Art', 'Computing', 'DT', 'MFL', 'Geography', 'History', 'Music', 'PE', 'RE']
cols = list(df.columns)

subjects_info = []
for idx, s in enumerate(subject_names):
    t_col = 10 + idx * 12
    avg_col = 17 + idx * 12
    subjects_info.append({
        'subject': s,
        'target_col': cols[t_col],
        'avg_col': cols[avg_col]
    })

summary_data = []
for s in subjects_info:
    name = s['subject']
    target = pd.to_numeric(filtered_df[s['target_col']], errors='coerce')
    avg = pd.to_numeric(filtered_df[s['avg_col']], errors='coerce')
    diff = avg - target
    
    summary_data.append({
        'Subject': name,
        'Mean Target': round(target.mean(), 2) if len(target.dropna()) > 0 else 0,
        'Mean Attained': round(avg.mean(), 2) if len(avg.dropna()) > 0 else 0,
        'Value Added': round(diff.mean(), 2) if len(diff.dropna()) > 0 else 0,
        '% Meeting Target': round((diff >= 0).mean() * 100, 1) if len(diff.dropna()) > 0 else 0
    })

summary_df = pd.DataFrame(summary_data)

overall_va = summary_df['Value Added'].mean()
m3.metric("Average Value Added", f"{overall_va:+.2f} Grades" if len(filtered_df) > 0 else "N/A")
m4.metric("Avg Target Met", f"{summary_df['% Meeting Target'].mean():.1f}%" if len(filtered_df) > 0 else "N/A")

st.divider()

# 7. Charts Row
col_a, col_b = st.columns(2)

with col_a:
    fig1 = px.bar(
        summary_df, x='Subject', y=['Mean Target', 'Mean Attained'],
        barmode='group', title="Target vs Attained Grade by Subject",
        color_discrete_map={'Mean Target': '#3366CC', 'Mean Attained': '#109618'}
    )
    st.plotly_chart(fig1, width='stretch')

with col_b:
    fig2 = px.bar(
        summary_df.sort_values(by='% Meeting Target'),
        y='Subject', x='% Meeting Target', orientation='h',
        title="% Students Meeting/Exceeding Target",
        color='% Meeting Target', color_continuous_scale='RdYlGn'
    )
    st.plotly_chart(fig2, width='stretch')

# 8. Interactive Heatmap Section
st.divider()
st.subheader("🔥 Student vs Subject Performance Heatmap")
st.markdown("Easily spot subject performance patterns across pupils. Filter by Pupil Premium in the sidebar to isolate PP students.")

if len(filtered_df) > 0:
    # Prepare heatmap data matrix
    heatmap_df = filtered_df[['Full Name']].copy()
    for s in subjects_info:
        heatmap_df[s['subject']] = pd.to_numeric(filtered_df[s['avg_col']], errors='coerce')
    
    heatmap_df = heatmap_df.dropna(subset=['Full Name']).sort_values('Full Name').set_index('Full Name')
    
    # Calculate responsive chart height based on filtered students (minimum 400px)
    dynamic_height = max(400, len(heatmap_df) * 22)
    
    fig_heatmap = px.imshow(
        heatmap_df,
        labels=dict(x="Subject", y="Student Name", color="Grade"),
        x=heatmap_df.columns,
        y=heatmap_df.index,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        title="Attained Grades Matrix (Red = Low Grade, Green = High Grade)"
    )
    
    fig_heatmap.update_layout(
        height=dynamic_height,
        xaxis_title="Subject",
        yaxis_title="Student Name",
        margin=dict(l=150, r=20, t=50, b=50)
    )
    
    st.plotly_chart(fig_heatmap, width='stretch')
else:
    st.info("No students match the current filter selection.")

# 9. Scatter Plot Row
st.divider()
filtered_df['Core_Avg_Grade'] = filtered_df[[cols[17], cols[29], cols[41]]].apply(pd.to_numeric, errors='coerce').mean(axis=1)

fig3 = px.scatter(
    filtered_df, x='% Attendance', y='Core_Avg_Grade',
    color='Reg Group', hover_name='Full Name',
    trendline="ols", title="Attendance vs Core Academic Grade (English, Maths, Science)"
)
st.plotly_chart(fig3, width='stretch')
