# VisionSort - AI-Powered Material Sorting System

VisionSort is a real-time, high-speed sorting line contamination control system. It integrates a custom PyTorch Convolutional Neural Network (CNN) classification model, a multi-threaded FastAPI pipeline, and a stunning responsive glassmorphic industrial control panel dashboard.

## System Features
* **AI Object Classifier**: Custom PyTorch CNN model performing object classification on 64x64 cropped frames across four material categories (Plastics, Metals, Biological/Organic, Paper).
* **Multi-threaded Streamer**: Simulated conveyor belt rendering frames at 10 FPS, overlaying real-time object tracking, classification labels, confidence values, and bounding boxes.
* **Smart Database Layer**: Motor-driven MongoDB integration with an automatic fallback to local SQLite (`visionsort_fallback.db`) if the MongoDB instance is unreachable.
* **Control Console UI**: Sleek, glassmorphic industrial control panel featuring:
  * HTML5 Canvas drawing the conveyor camera feed.
  * Real-time sliders for speed control (item rate velocity).
  * Interactive target stream selection.
  * System fault/warning logs tracking contamination events.
  * Chart.js telemetry tracking hourly sorted material volume and precision metrics.

## Quick Start

### 1. Requirements Installation
Install Python dependencies (Python 3.8+ recommended):
```bash
pip install -r requirements.txt
```

### 2. Train the CNN Model
Generate the synthetic dataset and train the model weights (`ml/model.pth`):
```bash
python ml/train.py --epochs 3
```

### 3. Run the Server
Launch the FastAPI uvicorn server:
```bash
python -m uvicorn backend.main:app --reload
```

Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**.
