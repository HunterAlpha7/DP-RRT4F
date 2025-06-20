import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import IsolationForest
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import pdfplumber
import base64
import random
import plotly.io as pio

# Fix for Kaleido
pio.kaleido.scope.mathjax = None

# App Configuration
st.set_page_config(
    page_title="WiFi Guardian 🛡️",
    page_icon="📶",
    layout="wide"
)

# Custom CSS for a polished interface
st.markdown("""
<style>
    .st-emotion-cache-1kyxreq {
        display: flex;
        flex-flow: wrap;
        gap: 2rem;
    }
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2e3b4e, #1a2639);
    }
    .stButton>button {
        width: 100%;
        margin: 5px 0;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.05);
    }
    .summary-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #2e3b4e;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Motivational Quotes
QUOTES = [
    "🛡️ Cybersecurity is not a product, but a process!",
    "🔒 Better safe than hacked!",
    "📶 A secure network is a happy network!",
    "🤖 AI guards while you sleep!",
    "🚨 Detect before you regret!",
    "💻 Security is always worth the investment!",
    "🔍 Stay vigilant, stay secure!"
]

def show_quote():
    st.markdown(f"<h3 style='text-align: center; color: #4CAF50;'>{random.choice(QUOTES)}</h3>", 
                unsafe_allow_html=True)

# Main App Function
def main():
    # Initialize session state variables
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'file_uploaded' not in st.session_state:
        st.session_state.file_uploaded = False
    if 'df' not in st.session_state:
        st.session_state.df = None

    # Sidebar Navigation
    with st.sidebar:
        st.title("🔍 Navigation")
        st.markdown("---")
        
        if st.button("📤 1. Upload File", help="Upload your network logs"):
            st.session_state.current_step = 1
        if st.button("📊 2. Data Visualization", disabled=not st.session_state.file_uploaded):
            st.session_state.current_step = 2
        if st.button("📈 3. Statistics Analysis", disabled=not st.session_state.file_uploaded):
            st.session_state.current_step = 3
        if st.button("📥 4. Download Report", disabled=not st.session_state.file_uploaded):
            st.session_state.current_step = 4

    # Main Content Area
    if st.session_state.current_step == 1:
        upload_file_section()
    elif st.session_state.current_step == 2:
        visualization_section()
    elif st.session_state.current_step == 3:
        statistics_section()
    elif st.session_state.current_step == 4:
        download_section()

def upload_file_section():
    st.title("📤 Upload Network Logs")
    st.markdown("---")
    
    if not st.session_state.file_uploaded:
        show_quote()
        st.markdown("""
        ### Welcome to WiFi Guardian! 🤖
        **Protect your network with AI-powered anomaly detection**
        1. Upload network logs 📤
        2. Visualize patterns 📊
        3. Generate reports 📄
        """)
    
    uploaded_file = st.file_uploader(
        "Choose network logs (CSV/TXT/PDF)",
        type=["csv", "txt", "pdf"],
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        try:
            process_file(uploaded_file)
            st.session_state.file_uploaded = True
            st.success("✅ File processed successfully!")
            
            # Show file summary
            st.subheader("📋 Upload Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(st.session_state.df))
            with col2:
                anomalies = sum(st.session_state.df['anomaly'] == -1)
                st.metric("Anomalies Detected", f"{anomalies} ({anomalies/len(st.session_state.df)*100:.1f}%)")
            with col3:
                st.metric("Max Traffic", f"{st.session_state.df['traffic'].max():.2f} Mbps")

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

def visualization_section():
    st.title("📊 Data Visualization")
    st.markdown("---")
    
    # 2D Visualization
    st.subheader("2D Traffic Analysis 🌐")
    # Use 'timestamp' if available; if not, generate a dummy one
    df = st.session_state.df.copy()
    if 'timestamp' not in df.columns:
        df['timestamp'] = pd.date_range(start="2021-01-01", periods=len(df), freq="T")
    fig2d = px.scatter(
        df,
        x='timestamp',
        y='traffic',
        color='anomaly',
        color_discrete_map={-1: 'orange', 1: 'blue'},
        title="2D Traffic Analysis"
    )
    st.plotly_chart(fig2d, use_container_width=True)
    
    # 3D Visualization
    st.subheader("3D Network Health 🌍")
    fig3d = px.scatter_3d(
        df,
        x='latency',
        y='packet_loss',
        z='traffic',
        color='anomaly',
        color_discrete_map={-1: 'orange', 1: 'blue'},
        title="3D Network Analysis"
    )
    st.plotly_chart(fig3d, use_container_width=True)

def statistics_section():
    st.title("📈 Statistical Analysis")
    st.markdown("---")
    
    st.subheader("Data Summary 📝")
    st.dataframe(st.session_state.df.describe(), use_container_width=True)
    
    st.subheader("Anomaly Distribution 📊")
    anomaly_counts = st.session_state.df['anomaly'].value_counts()
    fig = px.pie(
        names=['Normal', 'Anomaly'],
        values=[anomaly_counts.get(1, 0), anomaly_counts.get(-1, 0)],
        hole=0.4,
        color_discrete_sequence=['blue', 'orange'],
        title="Anomaly Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

def download_section():
    st.title("📥 Download Report")
    st.markdown("---")
    
    if st.button("🖨️ Generate Full Report"):
        with st.spinner("Generating PDF report..."):
            generate_pdf_report()
            st.success("Report generated successfully!")
            
    if 'pdf_report' in st.session_state:
        st.markdown("---")
        b64 = base64.b64encode(st.session_state.pdf_report).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="wifi_report.pdf">📥 Download Full Report</a>'
        st.markdown(href, unsafe_allow_html=True)

def process_file(uploaded_file):
    try:
        # Process CSV files
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        # Process TXT files
        elif uploaded_file.name.endswith('.txt'):
            lines = [line.decode().strip().split(',') for line in uploaded_file.readlines()]
            df = pd.DataFrame(lines[1:], columns=lines[0])
        # Process PDF files using pdfplumber
        elif uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                text = '\n'.join([page.extract_text() for page in pdf.pages])
            lines = [line.split(',') for line in text.split('\n') if line]
            df = pd.DataFrame(lines[1:], columns=lines[0])
        else:
            raise ValueError("Unsupported file type.")
        
        # Ensure required numeric columns exist and convert them
        numeric_cols = ['traffic', 'latency', 'packet_loss']
        for col in numeric_cols:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in data.")
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Run anomaly detection using IsolationForest with 40% contamination
        clf = IsolationForest(contamination=0.4, random_state=42)
        df['anomaly'] = clf.fit_predict(df[numeric_cols])
        
        st.session_state.df = df

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        raise

def generate_pdf_report():
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom Title Style
        title_style = ParagraphStyle(
            name='Title',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=14
        )
        
        # Add Title
        elements.append(Paragraph("WiFi Network Anomaly Detection", title_style))
        elements.append(Spacer(1, 12))
        
        # Add Summary Section
        elements.append(Paragraph("<b>Detection Summary:</b>", styles['Heading2']))
        summary_text = f"""
        • Total Data Points: {len(st.session_state.df)}<br/>
        • Anomalies Detected: {sum(st.session_state.df['anomaly'] == -1)}<br/>
        • Maximum Traffic: {st.session_state.df['traffic'].max():.2f} Mbps<br/>
        • Average Latency: {st.session_state.df['latency'].mean():.2f} ms<br/>
        • Peak Packet Loss: {st.session_state.df['packet_loss'].max():.2f}%<br/>
        """
        elements.append(Paragraph(summary_text, styles['BodyText']))
        elements.append(PageBreak())
        
        # Generate and embed plots in memory using BytesIO
        
        # 2D Plot
        df = st.session_state.df.copy()
        if 'timestamp' not in df.columns:
            df['timestamp'] = pd.date_range(start="2021-01-01", periods=len(df), freq="T")
        fig2d = px.scatter(df, x='timestamp', y='traffic', 
                           color='anomaly', title="2D Traffic Analysis",
                           color_discrete_map={-1: 'orange', 1: 'blue'})
        img_bytes_2d = fig2d.to_image(format="png", engine="kaleido")
        img2d_io = BytesIO(img_bytes_2d)
        
        # 3D Plot
        fig3d = px.scatter_3d(df, x='latency', y='packet_loss',
                              z='traffic', color='anomaly', title="3D Network Analysis",
                              color_discrete_map={-1: 'orange', 1: 'blue'})
        img_bytes_3d = fig3d.to_image(format="png", engine="kaleido")
        img3d_io = BytesIO(img_bytes_3d)
        
        # Add 2D Plot
        elements.append(Paragraph("<b>2D Traffic Analysis</b>", styles['Heading2']))
        elements.append(Image(img2d_io, width=6*inch, height=4*inch))
        elements.append(Spacer(1, 12))
        
        # Add 3D Plot
        elements.append(Paragraph("<b>3D Network Analysis</b>", styles['Heading2']))
        elements.append(Image(img3d_io, width=6*inch, height=4*inch))
        elements.append(PageBreak())
        
        # Add Statistics Section
        elements.append(Paragraph("<b>Statistical Report</b>", styles['Heading1']))
        stats = st.session_state.df.describe()
        for col in ['traffic', 'latency', 'packet_loss']:
            elements.append(Paragraph(f"<b>{col.capitalize()} Statistics:</b>", styles['Heading3']))
            stats_text = f"""
            • Mean: {stats[col]['mean']:.2f}<br/>
            • Std Dev: {stats[col]['std']:.2f}<br/>
            • Min: {stats[col]['min']:.2f}<br/>
            • 25%: {stats[col]['25%']:.2f}<br/>
            • 50%: {stats[col]['50%']:.2f}<br/>
            • 75%: {stats[col]['75%']:.2f}<br/>
            • Max: {stats[col]['max']:.2f}<br/>
            """
            elements.append(Paragraph(stats_text, styles['BodyText']))
            elements.append(Spacer(1, 12))
        
        doc.build(elements)
        st.session_state.pdf_report = buffer.getvalue()

    except Exception as e:
        st.error(f"Error generating report: {str(e)}")

if __name__ == "__main__":
    main()
