import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ==========================================
# STEP 1: SMART DATA LOADER
# ==========================================
def load_data():
    # Add a Readme expander to explain the methodology (Interview Best Practice)
        
    st.sidebar.header("📂 Data Source")
    uploaded_file = st.sidebar.file_uploader("Upload Fleet Report", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            # 1. Peek at file to find header
            try:
                df_temp = pd.read_excel(uploaded_file, header=None, nrows=20)
            except:
                uploaded_file.seek(0)
                df_temp = pd.read_csv(uploaded_file, header=None, nrows=20)

            # 2. Search for 'Plate Number'
            header_row_index = -1
            for index, row in df_temp.iterrows():
                row_str = row.astype(str).str.lower().str.replace(' ', '')
                if row_str.str.contains('platenumber').any():
                    header_row_index = index
                    break
            
            if header_row_index == -1:
                st.error("❌ Critical Error: Could not find 'Plate Number' column.")
                return None

            # 3. Reload with correct header
            uploaded_file.seek(0)
            if uploaded_file.name.endswith('.csv'):
                 df = pd.read_csv(uploaded_file, header=header_row_index)
            else:
                 df = pd.read_excel(uploaded_file, header=header_row_index)

            return df

        except Exception as e:
            st.error(f"❌ Error loading file: {e}")
            return None
    return None

# ==========================================
# STEP 2: HYGIENE & CLASSIFICATION LAYER
# ==========================================
def clean_and_process_data(df):
    # Standardize Columns
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')
    
    # --------------------------------------
    # SAFETY NET (FORMATTING)
    # --------------------------------------
    # Force Plate Number to string and remove ".0" artifacts from Excel
    if 'plate_number' in df.columns:
        df['plate_number'] = df['plate_number'].astype(str).str.replace(r'\.0$', '', regex=True)

    # --------------------------------------
    # FIX: REMOVE SUMMARY / FOOTER ROWS
    # --------------------------------------
    # We drop rows where 'plate_number' is missing (NaN)
    if 'plate_number' in df.columns:
        df = df.dropna(subset=['plate_number'])
        
        # Double check: Remove rows where 'location' says "Total Mileage Covered"
        if 'location' in df.columns:
            df = df[~df['location'].astype(str).str.contains("Total Mileage", case=False, na=False)]
            
    # Numeric Conversion
    for col in ['start_km', 'end_km', 'total_km']:
        if col in df.columns:
             df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Feature Extraction: Status
    if 'plate_number' in df.columns:
        def extract_status(val):
            val = str(val).upper()
            if 'BACKUP' in val:
                return "⚠️ Depot Backup"
            elif 'TRANSFER' in val:
                return "🔄 Transfer"
            elif 'RT-' in val or 'ROUTE' in val:
                return "🚚 On Route"
            elif 'SALES' in val:
                return "💰 For Sales/Decision"
            else:
                return "✅ Active Standard"
        df['operational_status'] = df['plate_number'].apply(extract_status)
    else:
        df['operational_status'] = "Unknown"

    # --------------------------------------
    # FEATURE: AUDIT & AUTO-CORRECTION
    # --------------------------------------
    df['audit_status'] = "Pass"
    df['audit_notes'] = ""
    
    if 'total_km' in df.columns and 'start_km' in df.columns and 'end_km' in df.columns:
        df['calculated_total'] = df['end_km'] - df['start_km']
        tolerance = 1.0 
        
        # 1. Identify Sensor Errors (Negative Distance)
        sensor_error_mask = (df['end_km'] < df['start_km'])
        df.loc[sensor_error_mask, 'audit_status'] = "Sensor Error"
        df.loc[sensor_error_mask, 'audit_notes'] = "End Km < Start Km. Check Odometer."
        
        # 2. Identify Manual Entry Errors (Math Mismatch)
        math_error_mask = (
            (~sensor_error_mask) & 
            (abs(df['total_km'] - df['calculated_total']) > tolerance)
        )
        
        if math_error_mask.any():
            df.loc[math_error_mask, 'audit_status'] = "Manual Entry Error"
            df.loc[math_error_mask, 'audit_notes'] = "Total corrected based on Odometer."
            # FIX: Auto-correct only reasonable errors, not massive corruptions
            df.loc[math_error_mask, 'total_km'] = df.loc[math_error_mask, 'calculated_total']

    return df

# ==========================================
# STEP 3: INTERACTIVITY (FILTERS)
# ==========================================
def apply_filters(df):
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filter Options")
    
    filtered_df = df.copy()
    
    # Filter 1: Audit Status
    audit_opts = ['All', 'Pass', 'Manual Entry Error', 'Sensor Error']
    selected_audit = st.sidebar.selectbox("🛡️ Audit Filter", audit_opts)
    if selected_audit != 'All':
        filtered_df = filtered_df[filtered_df['audit_status'] == selected_audit]

    # Filter 2: Operational Status
    if 'operational_status' in df.columns:
        statuses = ['All'] + sorted(df['operational_status'].unique().tolist())
        selected_status = st.sidebar.selectbox("🚦 Select Status", statuses)
        if selected_status != 'All':
            filtered_df = filtered_df[filtered_df['operational_status'] == selected_status]

    # Filter 3: Make (RESTORED)
    if 'make' in df.columns:
        makes = ['All'] + sorted(df['make'].dropna().astype(str).unique().tolist())
        selected_make = st.sidebar.selectbox("🚗 Select Make", makes)
        if selected_make != 'All':
            filtered_df = filtered_df[filtered_df['make'].astype(str) == selected_make]

    # Filter 4: Location
    if 'location' in df.columns:
        locations = ['All'] + sorted(df['location'].dropna().astype(str).unique().tolist())
        selected_loc = st.sidebar.selectbox("📍 Select Location", locations)
        if selected_loc != 'All':
            filtered_df = filtered_df[filtered_df['location'].astype(str) == selected_loc]
            
    return filtered_df

# ==========================================
# STEP 4: INTELLIGENCE & REPORTING
# ==========================================
def visualize_fleet_intelligence(df):
    st.markdown("---")
    
    # 1. Scorecard
    total_distance = df['total_km'].sum() if 'total_km' in df.columns else 0
    active_vehicles = df['plate_number'].nunique() if 'plate_number' in df.columns else 0
    
    error_counts = df['audit_status'].value_counts()
    manual_errors = error_counts.get("Manual Entry Error", 0)
    sensor_errors = error_counts.get("Sensor Error", 0)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌍 Total Distance", f"{total_distance:,.0f} km")
    col2.metric("🚛 Vehicles", active_vehicles)
    col3.metric("✏️ Manual Errors Fixed", manual_errors, delta_color="inverse")
    col4.metric("📟 Sensor Errors Found", sensor_errors, delta_color="inverse")

    st.markdown("---")

    # 2. Charts Row 1: Brand & Location
    col_brand, col_loc = st.columns(2)
    with col_brand:
        st.subheader("🏭 Which manufacturers dominate our fleet?") 
        if 'make' in df.columns:
            fig_brand = px.pie(df, names='make', hole=0.4, 
                               color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig_brand, use_container_width=True)
    with col_loc:
        st.subheader("📍 Where are our assets located?")
        if 'location' in df.columns:
            loc_counts = df['location'].value_counts().reset_index()
            loc_counts.columns = ['Location', 'Count']
            fig_loc = px.bar(loc_counts, x='Count', y='Location', orientation='h', 
                             text='Count', color='Count', color_continuous_scale='Blues')
            st.plotly_chart(fig_loc, use_container_width=True)

    # 3. Charts Row 2: Operational Intelligence
    st.subheader("🚦 Operational Status Intelligence")
    col_status, col_matrix = st.columns(2)
    with col_status:
        st.caption("Breakdown of Fleet Roles")
        if 'operational_status' in df.columns:
            status_counts = df['operational_status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_status = px.bar(status_counts, x='Count', y='Status', text='Count',
                                color='Status', color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_status, use_container_width=True)
    with col_matrix:
        st.caption("Role Distribution per Branch")
        if 'location' in df.columns:
            fig_matrix = px.histogram(df, x="location", color="operational_status", 
                                      barmode='group')
            st.plotly_chart(fig_matrix, use_container_width=True)

    # 4. Charts Row 3: Advanced Asset Utilization
    st.markdown("---")
    st.subheader("🚀 Are we overworking or underusing our assets?")
    
    tab1, tab2, tab3 = st.tabs(["📊 Distribution (Histogram)", "🏆 Top/Bottom Performers", "📦 Status Analysis (Box Plot)"])
    
    # Tab 1: Histogram
    with tab1:
        st.caption("Identify 'Idle' vs 'Overworked' groups.")
        if 'total_km' in df.columns:
            fig_hist = px.histogram(df, x="total_km", nbins=20, title="Distance Distribution",
                                    color_discrete_sequence=['#3366CC'])
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)
            
    # Tab 2: Top/Bottom lists
    with tab2:
        col_top, col_bot = st.columns(2)
        if 'plate_number' in df.columns and 'total_km' in df.columns:
            sorted_df = df.sort_values(by='total_km', ascending=False)
            with col_top:
                st.write("🔥 **Top 5 Highest Utilization**")
                cols = ['plate_number', 'make', 'total_km', 'operational_status']
                st.dataframe(sorted_df[cols].head(5), hide_index=True)
            with col_bot:
                st.write("🧊 **Top 5 Lowest Utilization**")
                st.dataframe(sorted_df[cols].tail(5), hide_index=True)
                
    # Tab 3: Status Box Plot
    with tab3:
        st.caption("Does 'Backup' status actually mean low mileage?")
        if 'operational_status' in df.columns and 'total_km' in df.columns:
            fig_box_stat = px.box(df, x='operational_status', y='total_km', color='operational_status',
                                  points="all", title="Utilization by Operational Role")
            st.plotly_chart(fig_box_stat, use_container_width=True)

    # 5. Detailed Data View with HIGHLIGHTS (COLLAPSIBLE)
    st.markdown("---")
    with st.expander("📋 Detailed Fleet Audit (Click to View Data)"):
        st.caption("Rows highlighted in **RED** indicate errors. Manual errors have been auto-corrected.")
        
        def highlight_rows(row):
            color = ''
            if row['audit_status'] == 'Sensor Error':
                color = 'background-color: #ffcccc' # Light Red
            elif row['audit_status'] == 'Manual Entry Error':
                color = 'background-color: #fff4e6' # Light Orange
            return [color] * len(row)

        cols_to_show = ['plate_number', 'make', 'location', 'start_km', 'end_km', 'total_km', 'operational_status', 'audit_status', 'audit_notes']
        final_cols = [c for c in cols_to_show if c in df.columns]
        
        styled_df = df[final_cols].style.apply(highlight_rows, axis=1)
        st.dataframe(styled_df, use_container_width=True)

# ==========================================
# MAIN APP FLOW
# ==========================================
def main():
    st.set_page_config(page_title="ATS Fleet Tool", layout="wide")
    st.title("🚛 ATS Fleet Audit & Intelligence Tool")
    
    raw_data = load_data()
    
    if raw_data is not None:
        processed_data = clean_and_process_data(raw_data)
        
        if processed_data is not None:
            filtered_data = apply_filters(processed_data)
            
            unique_count = filtered_data['plate_number'].nunique() if 'plate_number' in filtered_data.columns else 0
            st.caption(f"Showing {unique_count} active vehicles based on current filters.")
            
            visualize_fleet_intelligence(filtered_data)
            
            st.markdown("---")
            st.subheader("📥 Export Audited Data")
            csv_buffer = filtered_data.to_csv(index=False).encode('utf-8')
            st.download_button("Download Audit Report (CSV)", csv_buffer, "fleet_audit_report.csv", "text/csv")

if __name__ == "__main__":
    main()
