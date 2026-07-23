import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="Year 7 Key Group Attainment Dashboard", layout="wide")

st.title("🎓 Year 7 Key Group Attainment Dashboard")
st.markdown("Filter key cohorts dynamically to explore academic attainment and equity gaps.")

# 2. Load Data Function
@st.cache_data
def load_data():
    df = pd.read_csv('Y7 All Data 070726 - FFT20.csv')
    df['% Attendance'] = pd.to_numeric(df['% Attendance'], errors='coerce')
    return df

df = load_data()

# Subject Column Mapping
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

# 3. Sidebar Filters
st.sidebar.header("🔍 Controls & Filters")

metric_view = st.sidebar.radio("View Metric", ["Mean Attained Grade", "% Meeting/Exceeding Target"])

cohort_focus = st.sidebar.selectbox("Cohort Focus", ["All Cohorts", "Vulnerable Cohorts (PP & SEN)", "Gender (Boys vs Girls)"])

selected_reg = st.sidebar.selectbox("Registration Group", ['All'] + sorted([x for x in df['Reg Group'].dropna().unique()]))

# Filter application
filtered_df = df.copy()
if selected_reg != 'All':
    filtered_df = filtered_df[filtered_df['Reg Group'] == selected_reg]

# 4. Cohort Calculations
cohorts = {
    "All Pupils": filtered_df,
    "Boys": filtered_df[filtered_df['Sex'] == 'M'],
    "Girls": filtered_df[filtered_df['Sex'] == 'F'],
    "Pupil Premium": filtered_df[filtered_df['Pupil Premium Indicator'] == 'Y'],
    "Not Pupil Premium": filtered_df[filtered_df['Pupil Premium Indicator'].isna()],
    "Pupils with SEN": filtered_df[filtered_df['SEN Status'].notna() & (filtered_df['SEN Status'] != 'N')],
    "Pupils without SEN": filtered_df[filtered_df['SEN Status'].isna() | (filtered_df['SEN Status'] == 'N')]
}

if cohort_focus == "Vulnerable Cohorts (PP & SEN)":
    selected_cohort_keys = ["All Pupils", "Pupil Premium", "Not Pupil Premium", "Pupils with SEN", "Pupils without SEN"]
elif cohort_focus == "Gender (Boys vs Girls)":
    selected_cohort_keys = ["All Pupils", "Boys", "Girls"]
else:
    selected_cohort_keys = list(cohorts.keys())

# Build Attainment Matrix
matrix_data = []
for c_name in selected_cohort_keys:
    c_df = cohorts[c_name]
    row = {'Cohort Group': c_name}
    for s_info in subjects_info:
        s_name = s_info['subject']
        target = pd.to_numeric(c_df[s_info['target_col']], errors='coerce')
        avg = pd.to_numeric(c_df[s_info['avg_col']], errors='coerce')
        
        if metric_view == "Mean Attained Grade":
            val = avg.mean()
            row[s_name] = round(val, 2) if pd.notna(val) else 0.0
        else:
            diff = avg - target
            pct = (diff >= 0).mean() * 100
            row[s_name] = round(pct, 1) if pd.notna(pct) else 0.0
            
    matrix_data.append(row)

matrix_df = pd.DataFrame(matrix_data).set_index('Cohort Group')

# 5. Dashboard Summary Cards
m1, m2, m3, m4 = st.columns(4)
m1.metric("Selected Cohort Count", len(filtered_df))
m2.metric("Mean Attendance", f"{filtered_df['% Attendance'].mean():.1f}%" if len(filtered_df) > 0 else "N/A")

all_pupils_avg = matrix_df.loc['All Pupils'].mean() if 'All Pupils' in matrix_df.index else 0
if metric_view == "Mean Attained Grade":
    m3.metric("Overall Cohort Grade", f"{all_pupils_avg:.2f}")
    pp_gap = matrix_df.loc['Pupil Premium'].mean() - matrix_df.loc['Not Pupil Premium'].mean() if 'Pupil Premium' in matrix_df.index else 0
    m4.metric("PP vs Non-PP Gap", f"{pp_gap:+.2f} Grades")
else:
    m3.metric("Avg Target Met %", f"{all_pupils_avg:.1f}%")
    pp_gap = matrix_df.loc['Pupil Premium'].mean() - matrix_df.loc['Not Pupil Premium'].mean() if 'Pupil Premium' in matrix_df.index else 0
    m4.metric("PP vs Non-PP Gap", f"{pp_gap:+.1f}% Points")

st.divider()

# 6. Heatmap View using School Palette (#542A3A Burgundy -> #A3935D Gold -> #4A777A Teal)
st.subheader("🔥 Key Group Attainment Heatmap Matrix")
st.caption(f"Displaying **{metric_view}** across selected key groups.")

school_colorscale = [
    [0.0, "#542A3A"],  # Burgundy (Low)
    [0.5, "#A3935D"],  # Gold (Mid)
    [1.0, "#4A777A"]   # Teal (High)
]

fig_heatmap = px.imshow(
    matrix_df,
    labels=dict(x="Subject", y="Cohort Group", color="Value"),
    x=matrix_df.columns,
    y=matrix_df.index,
    color_continuous_scale=school_colorscale,
    aspect="auto",
    text_auto=True
)

fig_heatmap.update_layout(
    height=400,
    margin=dict(l=150, r=20, t=30, b=40),
    xaxis_title="",
    yaxis_title=""
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# 7. Vulnerable Groups Gap Matrix Table
st.divider()
st.subheader("⚖️ Equity Gap Analysis Matrix")
st.caption("Difference between vulnerable cohorts and peer baselines across key subjects (negative values indicate attainment gaps).")

gap_subjects = ['English', 'Maths', 'Science', 'Geography', 'History', 'MFL']

def calculate_gap(vulnerable_key, peer_key):
    gap_row = {}
    v_df = cohorts[vulnerable_key]
    p_df = cohorts[peer_key]
    
    for s in gap_subjects:
        s_info = next(item for item in subjects_info if item['subject'] == s)
        v_val = pd.to_numeric(v_df[s_info['avg_col']], errors='coerce').mean()
        p_val = pd.to_numeric(p_df[s_info['avg_col']], errors='coerce').mean()
        gap_row[s] = round(v_val - p_val, 2)
    
    gap_row['Average Gap'] = round(np.mean(list(gap_row.values())), 2)
    return gap_row

gap_data = {
    "Pupil Premium Gap (PP vs Non-PP)": calculate_gap("Pupil Premium", "Not Pupil Premium"),
    "SEND Opportunity Gap (SEN vs Non-SEN)": calculate_gap("Pupils with SEN", "Pupils without SEN"),
    "Gender Gap (Boys vs Girls)": calculate_gap("Boys", "Girls")
}

gap_df = pd.DataFrame(gap_data).T
st.dataframe(gap_df.style.background_gradient(cmap='RdYlGn', axis=None, vmin=-0.8, vmax=0.2), use_container_width=True)
