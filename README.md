# 🛡️ WiFi Guardian: AI-Powered Network Security

> **Anomaly Detection System for Public WiFi Networks**

![Demo](https://img.shields.io/badge/Demo-Live_Prototype-success?style=for-the-badge&logo=huggingface) ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

<p align="center">
  <img src="https://media.giphy.com/media/26n6WywJyh39n1pBu/giphy.gif" width="300">
</p>

## 🌟 Overview
WiFi Guardian is an AI-powered security solution designed to detect suspicious patterns in public WiFi networks. It helps prevent potential threats by using:

✅ **Machine Learning for anomaly detection**  
✅ **3D Data Visualizations**  
✅ **Automated PDF Reporting**  
✅ **Real-Time Alerts for Suspicious Activity**  

---

## 🔑 Key Features
- 📤 **Multi-Format Log Upload** (CSV, TXT, PDF)
- 📊 **Dynamic Dashboard with 3D Graphs**
- 🔮 **Predictive Analysis with Isolation Forest Algorithm**
- 📄 **Professional PDF Reports for Admins**
- 🚨 **Proactive Alerts to Prevent Attacks**

---

## ⚙️ Installation
### 1️⃣ Clone the Repository
```bash
git clone https://github.com/SUNBALSHEHZADI/wifi-guardian.git
cd wifi-guardian
```

### 2️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Run the Application
```bash
streamlit run app.py
```

---

## 🚀 How to Use
### 📥 Upload Network Logs
- Supports `.csv`, `.txt`, `.pdf`
- Use the [generate_test_data.py](#) script to create sample data

### 📊 Visualize Data Trends
```python
# Sample dataset format
timestamp,traffic,latency,packet_loss
2024-01-01 00:00:00,162.34,28.45,0.82
```

### 📈 Analyze and Generate Reports
- Real-time **Anomaly Distribution**
- Export insights in **PDF Format**

### ⚡ Get Instant Alerts
- Detects threats **before failures occur**
- Keeps networks **secure and stable**

---

## 🛠️ Tech Stack
- 🎈 **Frontend:** Streamlit
- 🤖 **Machine Learning:** scikit-learn
- 📊 **Visualization:** Plotly
- 📄 **Reporting:** ReportLab
- 🐍 **Runtime:** Python 3.10

---

## 📁 Data Format
```csv
timestamp,traffic,latency,packet_loss
2024-01-01 00:00:00,150.2,25.1,0.5
2024-01-01 00:01:00,480.6,160.8,12.3
```

**Generate sample data:**
```bash
python generate_test_data.py --samples 1000 --anomaly 0.4
```

---

## 🤝 Contributing
💡 **Have ideas?** Submit feature requests  
🐛 **Found a bug?** Report issues on GitHub  
👩💻 **Want to contribute?** Submit pull requests to the `dev` branch  

---

## 📜 License
This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<p align="center">
  🚀 Built with passion by SUNBALSHEHZADI | 🔐 Secure your network today!
</p>
