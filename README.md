# 🚛 ATS Fleet Audit & Intelligence Dashboard

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Built%20With-Streamlit-red)
![Plotly](https://img.shields.io/badge/Visualization-Plotly-green)
![Status](https://img.shields.io/badge/Status-Internship%20Submission-orange)

### 📊 Executive Summary
The **ATS Fleet Audit & Intelligence Tool** is a specialized analytics dashboard designed to transform raw, inconsistent fleet telematics data into actionable business intelligence. 

Unlike standard reporting tools, this application features a robust **Audit & Hygiene Layer** that proactively detects data corruption, sensor errors, and manual entry typos before generating visualizations. This ensures that fleet managers base their decisions on verified data, not spreadsheet artifacts.


### 🧠 The Problem & The Solution

**The Challenge:**
Raw fleet data often contains:
* **Mixed Data Types:** Numeric columns containing text (e.g., "Total Mileage Covered").
* **Manual Entry Errors:** Typographical errors where the entered 'Total Km' does not match the Odometer readings (`End` - `Start`).
* **Sensor Glitches:** Negative distance readings (End Km < Start Km).
* **Operational Noise:** Backup vehicles mixing with active fleet data, skewing utilization averages.

**The Solution:**
This dashboard implements a **"Quarantine Protocol"**:
1.  **Sanitize:** Automatically removes footer rows and text artifacts from numeric columns.
2.  **Audit:** Validates every trip against odometer readings.
3.  **Correct:** Auto-corrects minor manual math errors while flagging them for review.
4.  **Visualize:** Generates decision-focused charts strictly on *clean* data, while isolating errors in a detailed Audit Log.

---

### 🛠️ Key Technical Features

#### 1. Smart Hygiene Layer
The app distinguishes between data corruption and human error:
* **Sensor Errors (Critical):** Rows where `End Km < Start Km` are flagged in **Red** and excluded from analytics to prevent skewing.
* **Manual Entry Errors (Fixable):** If `Total Km` differs from (`End` - `Start`), the system trusts the Odometer reading, auto-corrects the total, and flags it in **Orange**.

#### 2. Advanced Outlier Protection
The system automatically detects summary rows (e.g., Row 96 in standard reports) that contain massive totals (e.g., 300,000+ km) and removes them. This prevents single-row artifacts from flattening the entire utilization histogram.

#### 3. Operational Context Filtering
Vehicles are not treated equally. The dashboard parses Plate Numbers to categorize assets:
* ✅ **Active Standard:** Regular fleet.
* ⚠️ **Depot Backup:** Spare vehicles (Expected low utilization).
* 🔄 **Transfer:** Vehicles in transit.

---

### 🚀 Installation & Usage

**Prerequisites**
* Python 3.8 or higher

**Step 1: Clone the Repository**
```bash
git clone https://github.com/YOUR_USERNAME/ATS-Fleet-Intelligence-Dashboard.git
cd ATS-Fleet-Intelligence-Dashboard
