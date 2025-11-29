# TorrentGuard

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Prerequisites](#prerequisites)
4. [Installation Guide](#installation-guide)
5. [Usage Instructions](#usage-instructions)
6. [Project Structure](#project-structure)
7. [Technical Deep Dive](#technical-deep-dive)
8. [API Documentation](#api-documentation)
9. [Frontend Interface](#frontend-interface)
10. [Malware Detection Engine](#malware-detection-engine)
11. [Download Workflows](#download-workflows)
12. [Quarantine System](#quarantine-system)
13. [Testing](#testing)
14. [Troubleshooting](#troubleshooting)
15. [Development](#development)

---

## Overview

TorrentGuard is a secure, AI-powered torrent client designed to mitigate the risks associated with peer-to-peer file sharing. Unlike standard clients that download files without inspection, TorrentGuard implements a real-time security layer that scans individual file chunks (pieces) as they are received from peers.

### The Problem
Traditional torrent clients download files in pieces from multiple peers simultaneously. However, these clients typically wait until the entire file is assembled before performing any security checks. This approach poses a risk: a user might execute a malicious file before their antivirus software completes a scan.

### The Solution
TorrentGuard solves this by scanning each piece as it arrives. By leveraging a machine learning model (Random Forest) trained on network traffic patterns and signature-based detection (YARA), the system identifies malicious patterns—such as high entropy indicative of packing or known malware signatures—before the file is fully reassembled on the user's disk.

When a high-risk file is detected, TorrentGuard automatically:
1. Stops the download
2. Moves the partial file to a secure quarantine folder
3. Alerts the user with a detailed risk assessment

The application operates as a full-stack solution: a Python-based backend orchestrates the download and scanning process, while a modern web interface provides real-time visualization of download progress, peer connections, and security risk assessments.

---

## System Architecture

TorrentGuard is composed of three primary layers, each with distinct responsibilities:

### Layer 1: Backend Server (`api_server.py`)
The backend is built on Flask and serves as the core orchestrator of the entire system.

**Key Responsibilities:**
*   **HTTP API**: Provides RESTful endpoints for uploading torrent files, starting downloads, checking status, and managing quarantined files.
*   **WebSocket Communication**: Uses `Flask-SocketIO` to maintain persistent connections with the frontend, enabling real-time push notifications for:
    *   Download progress updates
    *   Piece-level scan results
    *   Risk score changes
    *   Download completion or errors
*   **Download Coordination**: Manages the `TorrentDownloader` class instances, which handle the actual torrent protocol communication.
*   **Quarantine Management**: Implements the logic for moving malicious files to the quarantine folder and maintaining a registry of quarantined items.

**Technology Stack:**
*   Flask 3.0.0 (Web framework)
*   Flask-SocketIO 5.3.6 (WebSocket support)
*   Flask-CORS 4.0.0 (Cross-Origin Resource Sharing)
*   Eventlet 0.33.3 (Asynchronous I/O)

### Layer 2: Malware Detection Engine (`malware_detector.py`)
This is the "brain" of the security system. It combines multiple detection strategies to generate a comprehensive risk assessment.

**Detection Methods:**

1.  **Feature Extraction**: Analyzes raw byte streams from downloaded pieces.
    *   **Shannon Entropy**: Calculates the randomness of byte distribution. High entropy (>7.0) typically indicates encryption or packing, which is common in malware attempting to evade signature-based detection.
    *   **MZ Header Detection**: Checks for the "MZ" magic bytes at the start of a file, which indicates a Windows Portable Executable (PE). Finding an executable in an unexpected file type is a red flag.
    *   **Byte Frequency Analysis**: Creates a histogram of byte values to identify anomalies in data patterns.

2.  **Machine Learning**: Utilizes a `RandomForestClassifier` trained on the NSL-KDD dataset (a network intrusion detection dataset). The model learns to distinguish between normal and malicious network behavior based on features like:
    *   Source/destination bytes
    *   Peer count
    *   Seed count
    *   Protocol type
    *   Service type

3.  **YARA Integration**: Scans files against a set of custom rules defined in `yara_rules/malware_rules.yar`. YARA is a pattern-matching tool used by malware researchers to identify and classify malware families based on textual or binary patterns. TorrentGuard includes rules to detect:
    *   Suspicious strings (e.g., "cmd.exe", "powershell")
    *   Windows PE executables
    *   Suspicious network activity patterns

4.  **PE File Analysis** (via `pefile` library): For Windows executables, performs deeper inspection:
    *   Checks for unusual section names
    *   Analyzes section entropy to detect packing
    *   Validates the PE header structure

**Risk Scoring Algorithm:**
The final risk score is a weighted combination of all detection methods:
```
base_risk = ML_model_probability * 100
if entropy > 6.0:
    base_risk += (entropy - 6.0) * 15
if MZ_header_found:
    base_risk += 40
if YARA_matches > 0:
    base_risk += 30
if PE_high_entropy_section:
    base_risk += 20
final_risk = min(base_risk, 100)
```

**Verdict Thresholds:**
*   **CLEAN**: Risk Score 0-40
*   **SUSPICIOUS**: Risk Score 41-70
*   **MALICIOUS**: Risk Score 71-100

### Layer 3: Torrent Client Integration
TorrentGuard supports two modes of operation:

**Real Mode (`qbittorrent_client.py`)**:
*   Interfaces with a running qBittorrent instance via its Web API.
*   Monitors active downloads in real-time.
*   Maps file pieces to disk locations for byte-level scanning.
*   Can pause or remove torrents if a threat is detected.
*   Requires qBittorrent to be installed and running.

**Mock Mode (`mock_libtorrent.py`)**:
*   A simulation layer that mimics torrent behavior without requiring active network connections.
*   Used for testing, development, and demonstration purposes.
*   Simulates piece downloads with realistic progress updates.

---

## Prerequisites

To run TorrentGuard, your system must meet the following requirements:

*   **Operating System**: Windows 10 or Windows 11 (64-bit)
*   **Python**: Version 3.8 or higher
    *   Python 3.9 or 3.10 recommended for best compatibility
*   **qBittorrent**: Latest version (required for "Real Mode" downloads)
    *   Download from: https://www.qbittorrent.org/download.php
*   **Git** (Optional but recommended): For easy repository cloning
    *   Download from: https://git-scm.com/downloads

**Hardware Recommendations:**
*   **RAM**: Minimum 4GB, 8GB recommended
*   **Storage**: 500MB for the application + space for downloads
*   **Network**: Stable internet connection for torrent downloads

---

## Installation Guide

### Step 1: Install Python

1.  Navigate to https://www.python.org/downloads/
2.  Download the latest Python 3.x installer for Windows (64-bit)
3.  Run the installer
4.  **CRITICAL**: Check the box that says **"Add Python to PATH"** at the bottom of the installer window
    *   This allows you to run Python from any terminal/command prompt
    *   Without this, you'll receive "Python is not recognized" errors
5.  Click "Install Now"
6.  Wait for installation to complete
7.  Verify installation by opening Command Prompt and typing:
    ```bash
    python --version
    ```
    You should see something like: `Python 3.10.x`

### Step 2: Install Git (Optional)

1.  Navigate to https://git-scm.com/downloads
2.  Download the installer for Windows
3.  Run the installer with default settings
4.  Verify installation:
    ```bash
    git --version
    ```

### Step 3: Install qBittorrent

1.  Navigate to https://www.qbittorrent.org/download.php
2.  Download the Windows 64-bit installer
3.  Run the installer with default settings
4.  Launch qBittorrent once to ensure it's working

### Step 4: Download TorrentGuard

**Option A: Using Git (Recommended)**
```bash
git clone https://github.com/burntcookiedough/SecureTorrent.git
cd SecureTorrent
```

**Option B: Download ZIP**
1.  Go to the GitHub repository
2.  Click the green "Code" button
3.  Select "Download ZIP"
4.  Extract the ZIP file to your desired location (e.g., `C:\Users\YourName\Desktop\SecureTorrent`)
5.  Open Command Prompt and navigate to that folder:
    ```bash
    cd C:\Users\YourName\Desktop\SecureTorrent
    ```

### Step 5: Install Python Dependencies

TorrentGuard requires several Python libraries. Install them using:

```bash
pip install -r requirements_loose.txt
```

**What this command does:**
*   `pip` is Python's package installer
*   `requirements_loose.txt` contains a list of required libraries without strict version numbers
*   The installer will download and install:
    *   **Flask**: Web framework for the API server
    *   **flask-cors**: Enables Cross-Origin requests from the frontend
    *   **flask-socketio**: Real-time WebSocket communication
    *   **eventlet**: Asynchronous I/O library for handling concurrent connections
    *   **scikit-learn**: Machine learning library for the Random Forest classifier
    *   **numpy**: Numerical computing library (required by scikit-learn)
    *   **pandas**: Data manipulation library (required for training the model)
    *   **pefile**: Windows PE file analysis
    *   **yara-python**: YARA rule matching engine
    *   **qbittorrent-api**: Python client for qBittorrent's Web API

**If you encounter errors**, try the stricter version file:
```bash
pip install -r requirements.txt
```
This file contains specific version numbers that are known to work together.

---

## Usage Instructions

### Option A: Automatic Launch (Recommended for Beginners)

1.  Open the `SecureTorrent` folder in File Explorer
2.  Double-click `setup_and_run.bat`
3.  A terminal window will open and perform the following:
    *   Check for Python installation
    *   Install dependencies (if not already installed)
    *   Search for qBittorrent in standard installation locations
    *   Launch qBittorrent (if found)
    *   Start the Flask API server
    *   Automatically open your web browser to http://localhost:5000

4.  Wait for the message: `SYSTEM ONLINE`

### Option B: Manual Launch (For Developers)

**Step 1: Start qBittorrent** (Skip if using Mock Mode)
*   Launch qBittorrent manually from your Start menu

**Step 2: Start the API Server**
```bash
python api_server.py
```

You'll see console output like:
```
DEBUG: Starting imports...
DEBUG: Imported Flask
DEBUG: Importing MalwareDetector...
[ML] Loading malware detection model...
[OK] ML Model loaded | Precision: 0.9847
[OK] YARA rules loaded successfully
[OK] qBittorrent available
============================================================
[INFO] Torrent Malware Detection API Server
============================================================
[DIR] Downloads: C:\Users\...\SecureTorrent\downloads
[DIR] Uploads: C:\Users\...\SecureTorrent\uploads
[SEC] Quarantine: C:\Users\...\SecureTorrent\quarantine
[ML] ML Integration: [OK] ACTIVE (Random Forest)
============================================================
Starting server on http://localhost:5000
```

**Step 3: Access the Dashboard**
*   Open your web browser
*   Navigate to: http://localhost:5000

---

## Project Structure

Understanding the project structure is crucial for development and troubleshooting.

```
SecureTorrent/
│
├── api_server.py               # Main backend server (980 lines)
├── malware_detector.py         # ML and YARA detection engine (289 lines)
├── qbittorrent_client.py       # qBittorrent API wrapper (7,192 bytes)
├── mock_libtorrent.py          # Torrent simulation for testing (5,815 bytes)
├── train_model.py              # Script to train/retrain the ML model
│
├── frontend/                   # Web interface
│   ├── index.html              # Main dashboard page
│   ├── app.html                # Alternative entry point (same as index.html)
│   ├── app.js                  # Frontend JavaScript logic (10,025 bytes)
│   └── style.css               # Dashboard styling (8,843 bytes)
│
├── models/                     # Trained ML models
│   └── malware_detector_latest.pkl  # Pickled Random Forest model + scaler
│
├── yara_rules/                 # YARA signature rules
│   └── malware_rules.yar       # Pattern definitions for malware detection
│
├── downloads/                  # Default location for completed downloads
├── uploads/                    # Temporary storage for uploaded .torrent files
├── quarantine/                 # Isolated storage for malicious files
│
├── tests/                      # Test suite
│   └── (various test files)
│
├── requirements.txt            # Python dependencies (strict versions)
├── requirements_loose.txt      # Python dependencies (flexible versions)
├── setup_and_run.bat           # Windows launcher script
└── .gitignore                  # Git exclusions
```

### Key File Descriptions

**`api_server.py`** (980 lines)
*   The heart of the application
*   Defines Flask routes for the REST API
*   Implements the `TorrentDownloader` class with two download modes (qBittorrent and Mock)
*   Manages WebSocket events for real-time updates
*   Handles quarantine operations

**`malware_detector.py`** (289 lines)
*   Contains the `MalwareDetector` class
*   Loads the trained Random Forest model from `models/malware_detector_latest.pkl`
*   Evaluates each torrent piece and returns a risk assessment
*   Integrates with YARA for signature-based detection

**`qbittorrent_client.py`**
*   Provides a Python interface to qBittorrent's Web API
*   Methods include:
    *   `add_torrent(torrent_path, save_path)`: Add a torrent to qBittorrent
    *   `get_torrent_info(torrent_hash)`: Retrieve download status
    *   `get_piece_states(torrent_hash)`: Get the state of each piece (downloading, complete, etc.)
    *   `pause_torrent(torrent_hash)`: Pause a download
    *   `remove_torrent(torrent_hash, delete_files)`: Remove from client

**`mock_libtorrent.py`**
*   Mimics the libtorrent API for testing
*   Simulates piece-by-piece downloads
*   No actual network traffic is generated

**`frontend/app.js`** (10,025 bytes)
*   Handles all frontend logic
*   Establishes WebSocket connection to the server
*   Listens for events: `download_started`, `download_progress`, `piece_downloaded`, `download_complete`
*   Updates the UI dynamically (progress bars, risk meters, logs)

---

## Technical Deep Dive

### How a Download Works (Step-by-Step)

1.  **User uploads a .torrent file** via the web interface
2.  **Frontend** sends file to `/api/upload-torrent` endpoint
3.  **Backend** (api_server.py):
    *   Receives the file
    *   Saves it to `uploads/` folder with a hash-based filename
    *   Parses the torrent metadata using `mock_libtorrent.torrent_info()`
    *   Extracts: file name, total size, piece count, piece size
    *   Returns torrent metadata to frontend (including a unique `torrent_id`)

4.  **User clicks "Start Download"**
5.  **Frontend** sends POST request to `/api/start-download` with the `torrent_id`
6.  **Backend** creates a `TorrentDownloader` instance:
    *   Checks if qBittorrent is available → use qBittorrent mode
    *   Otherwise → use Mock mode

7.  **TorrentDownloader.download_chunks_with_scan()** is called in a background thread
8.  **qBittorrent Mode** (if available):
    *   Add the torrent to qBittorrent via API
    *   Enter a monitoring loop:
        *   Every 0.5 seconds, check piece states
        *   For each newly completed piece:
            *   Read the bytes from disk
            *   Calculate entropy
            *   Check for MZ header
            *   Call `MalwareDetector.predict()` with extracted features
            *   Emit `piece_downloaded` event with scan results
        *   Emit `download_progress` event with updated stats (peers, rate, progress %)
        *   If all desired pieces are downloaded, exit loop

9.  **Post-Download Analysis**:
    *   Collect all piece scan results
    *   Calculate maximum risk score
    *   Count how many pieces were flagged as malicious
    *   Determine overall verdict (CLEAN, SUSPICIOUS, MALICIOUS)

10. **Quarantine Decision**:
    *   If verdict is MALICIOUS:
        *   Pause the torrent in qBittorrent
        *   Move the file(s) to `quarantine/` folder
        *   Rename with a unique hash ID
        *   Store metadata in `quarantined_files` dictionary
    *   If verdict is CLEAN or SUSPICIOUS:
        *   Leave file in `downloads/` folder

11. **Emit `download_complete` event** to frontend with:
    *   Final verdict
    *   Risk score
    *   Quarantine status
    *   File path

### The Scanning Process (In Detail)

When `TorrentDownloader.scan_piece(piece_index, piece_hash)` is called:

1.  **Locate the piece on disk**:
    *   Calculate byte offset: `piece_offset = piece_index * piece_size`
    *   Determine which file(s) contain this piece (torrents can span multiple files)
    *   Read the bytes from disk

2.  **Entropy Calculation**:
    ```python
    counts = {}
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1
    entropy = -sum((count / len(data)) * math.log2(count / len(data)) for count in counts.values())
    ```
    *   Entropy ranges from 0 (all bytes identical) to 8 (perfectly random)
    *   Normal text files: ~4.5-5.5
    *   Compressed files: ~7.5-7.9
    *   Encrypted/packed malware: often >7.8

3.  **MZ Header Check**:
    ```python
    has_mz = (len(data) >= 2 and data[:2] == b'MZ')
    ```
    *   "MZ" are the magic bytes for Windows executables
    *   Finding this in a file that claims to be a video or document is highly suspicious

4.  **Feature Vector Construction**:
    ```python
    features = {
        'src_bytes': piece_size,
        'dst_bytes': 0,
        'peer_count': current_peer_count,
        'seed_count': current_seed_count,
        'num_files': total_file_count,
        'protocol_type': 'tcp',
        'service': 'other',
        'flag': 'SF'
    }
    ```
    *   These features match the NSL-KDD dataset schema used during model training

5.  **ML Prediction**:
    ```python
    feature_vector_scaled = scaler.transform([feature_values])
    prediction = model.predict(feature_vector_scaled)[0]  # 0 or 1
    probability = model.predict_proba(feature_vector_scaled)[0]  # [prob_clean, prob_malicious]
    base_risk = probability[1] * 100
    ```

6.  **Risk Adjustment**:
    *   Add entropy penalty
    *   Add MZ header penalty
    *   (If full file available) Run YARA scan and add penalty for matches

7.  **Return Scan Result**:
    ```python
    {
        'malicious': (final_risk > 70),
        'confidence': probability[prediction],
        'risk_score': final_risk,
        'verdict': 'CLEAN' | 'SUSPICIOUS' | 'MALICIOUS',
        'entropy': calculated_entropy,
        'scanner': 'random_forest',
        'timestamp': ISO_timestamp
    }
    ```

---

## API Documentation

TorrentGuard exposes a RESTful API on port 5000. All endpoints return JSON.

### Upload Endpoints

#### POST `/api/upload-torrent`
Upload a .torrent file to the server.

**Request:**
*   Content-Type: `multipart/form-data`
*   Field: `file` (binary data)

**Response:**
```json
{
  "success": true,
  "torrent": {
    "torrent_id": "a3f5e9b2c1d4...",
    "name": "example_file.mp4",
    "total_size": 104857600,
    "total_pieces": 400,
    "piece_size": 262144,
    "file_path": "C:\\...\\uploads\\a3f5e9b2c1d4.torrent"
  }
}
```

### Download Endpoints

#### POST `/api/start-download`
Start downloading a torrent with malware scanning.

**Request:**
```json
{
  "torrent_id": "a3f5e9b2c1d4",
  "num_pieces": 10
}
```
*   `num_pieces`: How many pieces to download (default: 10)

**Response:**
```json
{
  "success": true,
  "download_id": "d7c8e1f2a9b4...",
  "message": "Download started"
}
```

#### GET `/api/download-status/<download_id>`
Get the current status of an active download.

**Response:**
```json
{
  "download_id": "d7c8e1f2a9b4",
  "state": "downloading",
  "progress": 45.2,
  "peers": 12,
  "download_rate": 524288,
  "upload_rate": 65536
}
```

#### POST `/api/stop-download/<download_id>`
Stop an active download.

**Response:**
```json
{
  "success": true,
  "message": "Download stopped"
}
```

#### GET `/api/downloads`
List all active downloads.

**Response:**
```json
{
  "downloads": [
    {
      "download_id": "d7c8e1f2a9b4",
      "name": "example_file.mp4",
      "total_size": 104857600
    }
  ]
}
```

### Scan Results Endpoints

#### GET `/api/scan-results/<download_id>`
Retrieve all piece-level scan results for a download.

**Response:**
```json
{
  "download_id": "d7c8e1f2a9b4",
  "results": {
    "0": {
      "malicious": false,
      "confidence": 0.98,
      "risk_score": 12.5,
      "verdict": "CLEAN",
      "entropy": 5.2,
      "scanner": "random_forest",
      "timestamp": "2025-11-30T03:15:22"
    },
    "1": {
      "malicious": false,
      "confidence": 0.95,
      "risk_score": 18.3,
      "verdict": "CLEAN",
      ...
    }
  }
}
```

### Quarantine Endpoints

#### GET `/api/quarantine/list`
List all quarantined files.

**Response:**
```json
{
  "quarantined_files": [
    {
      "quarantine_id": "q1a2b3c4d5e6",
      "original_name": "malicious.exe",
      "download_id": "d7c8e1f2a9b4",
      "quarantine_path": "C:\\...\\quarantine\\q1a2b3c4d5e6_malicious.exe",
      "scan_result": {
        "max_risk_score": 87.5,
        "malicious_pieces": 3,
        "verdict": "MALICIOUS"
      },
      "quarantined_at": "2025-11-30T03:20:15",
      "status": "quarantined"
    }
  ],
  "count": 1
}
```

#### GET `/api/quarantine/<quarantine_id>`
Get details of a specific quarantined file.

#### POST `/api/quarantine/<quarantine_id>/restore`
Restore a file from quarantine (use with extreme caution).

**Request:**
```json
{
  "restore_path": "C:\\Users\\...\\Downloads\\file.exe"
}
```
*   If `restore_path` is omitted, file is restored to original download location

**Response:**
```json
{
  "success": true,
  "message": "File restored to C:\\Users\\...\\Downloads\\file.exe"
}
```

#### DELETE `/api/quarantine/<quarantine_id>/delete`
Permanently delete a quarantined file.

**Response:**
```json
{
  "success": true,
  "message": "File permanently deleted: malicious.exe"
}
```

### Health Check

#### GET `/api/health`
Check if the server is running.

**Response:**
```json
{
  "status": "healthy",
  "active_downloads": 2,
  "timestamp": "2025-11-30T03:25:00"
}
```

---

## Frontend Interface

The web dashboard (`frontend/index.html` + `app.js`) provides a real-time view of all download activities.

### UI Components

1.  **Header**:
    *   Application title: "TorrentGuard"
    *   System status indicator (Online/Offline)
    *   Real-time metrics: MEM (Memory/Progress), PEERS, RATE (Download Speed)

2.  **Upload Section**:
    *   File input for .torrent files
    *   "Upload" button
    *   Displays selected file name

3.  **Active Download Card**:
    *   File name and size
    *   Circular progress indicator (0-100%)
    *   Risk meter (color-coded: green < 40, yellow 40-70, red > 70)
    *   Peer count and download speed
    *   Piece count status (e.g., "5/10 pieces scanned")

4.  **Event Log**:
    *   Scrolling list of events
    *   Each entry shows: timestamp, event type, piece number, verdict, risk score

### WebSocket Events

The frontend listens for the following server-sent events:

**`download_started`**:
```javascript
{
  download_id: "...",
  name: "file.mp4",
  total_size: 104857600,
  total_pieces: 400,
  downloading_pieces: 10
}
```

**`download_progress`**:
```javascript
{
  download_id: "...",
  progress: 45.2,
  state: "downloading",
  peers: 12,
  download_rate: 524288,
  pieces_completed: 181,
  total_pieces: 400
}
```

**`piece_downloaded`**:
```javascript
{
  download_id: "...",
  piece_index: 5,
  piece_hash: "abc123",
  scan_result: {
    verdict: "CLEAN",
    risk_score: 15.2,
    entropy: 5.4
  },
  progress: 50.0
}
```

**`download_complete`**:
```javascript
{
  download_id: "...",
  pieces_downloaded: 10,
  file_path: "C:\\...\\downloads\\file.mp4",
  verdict: "CLEAN",
  max_risk_score: 25.3,
  malicious_pieces: 0,
  quarantined: false
}
```

**`download_error`**:
```javascript
{
  download_id: "...",
  error: "Connection timeout"
}
```

---

## Malware Detection Engine

### The Machine Learning Model

**Type**: Random Forest Classifier  
**Training Dataset**: NSL-KDD (Network Intrusion Detection)  
**Features**: 8 dimensions (src_bytes, dst_bytes, peer_count, seed_count, num_files, protocol_type, service, flag)  
**Precision**: ~98.47% (on training data)

**Training Process** (via `train_model.py`):
1. Load NSL-KDD dataset
2. Encode categorical features (protocol_type, service, flag) using LabelEncoder
3. Split data: 80% training, 20% testing
4. Standardize features using StandardScaler
5. Train RandomForestClassifier with 100 trees
6. Evaluate precision, recall, F1-score
7. Save model, scaler, and encoders to `models/malware_detector_latest.pkl`

**To retrain the model**:
```bash
python train_model.py
```

### YARA Rules

Located in `yara_rules/malware_rules.yar`. Sample rule:

```yara
rule SuspiciousStrings {
    meta:
        description = "Detects suspicious strings in malware"
    strings:
        $s1 = "cmd.exe" nocase
        $s2 = "powershell" nocase
        $s3 = "rundll32" nocase
    condition:
        any of ($s*)
}
```

**How YARA is used**:
*   When a piece is downloaded, if the file exists on disk, `MalwareDetector.scan_with_yara()` is called
*   YARA compiles the rules and scans the file
*   Any matches increase the risk score by 30 points

---

## Download Workflows

### Workflow 1: Clean File Download

1. User uploads `ubuntu.torrent`
2. Backend parses: 4GB file, 16,000 pieces, 256KB per piece
3. User starts download (default: scan first 10 pieces)
4. qBittorrent begins downloading
5. Piece 0 completes → scanned → Risk: 12% → Verdict: CLEAN
6. Piece 1 completes → scanned → Risk: 15% → Verdict: CLEAN
7. ... (pieces 2-9 all CLEAN)
8. All 10 pieces scanned → Max risk: 18% → Overall verdict: CLEAN
9. File remains in `downloads/ubuntu.iso`

### Workflow 2: Malicious File Detection

1. User uploads `game_crack.torrent`
2. Backend parses: 50MB file, 200 pieces
3. User starts download
4. Piece 0 completes
5. Scan detects:
    *   Entropy: 7.9 (very high) → +15 points
    *   MZ header found → +40 points
    *   YARA match: "SuspiciousStrings" → +30 points
    *   ML prediction: 0.85 (malicious) → +85 points
    *   Total risk: min(100, 85 + 15 + 40 + 30) = 100
    *   Verdict: MALICIOUS
6. Download immediately stopped
7. Backend calls `quarantine_file()`
8. File moved to `quarantine/q1a2b3c4_game_crack.exe`
9. Frontend displays: "DANGER: Malicious file quarantined"

---

## Quarantine System

Files flagged as MALICIOUS are automatically quarantined to prevent accidental execution.

**Quarantine Process**:
1. Torrent download is paused (if using qBittorrent)
2. File is moved from `downloads/` to `quarantine/`
3. File is renamed: `{unique_hash}_{original_name}`
4. A quarantine record is created:
```python
{
    'quarantine_id': 'q1a2b3c4d5e6',
    'original_name': 'malware.exe',
    'download_id': 'd7c8e1f2...',
    'quarantine_path': 'C:\\...\\quarantine\\q1a2b3c4_malware.exe',
    'scan_result': {...},
    'quarantined_at': '2025-11-30T03:20:15',
    'status': 'quarantined'
}
```
5. Record is stored in memory (lost on server restart; future versions may use a database)

**Managing Quarantined Files**:
*   View list: `GET /api/quarantine/list`
*   View details: `GET /api/quarantine/<id>`
*   Restore (dangerous): `POST /api/quarantine/<id>/restore`
*   Delete permanently: `DELETE /api/quarantine/<id>/delete`

---

## Testing

TorrentGuard includes several test scripts:

**`test_api.py`**:
*   Tests API endpoints with sample requests
*   Run: `python test_api.py`

**`test_comprehensive.py`**:
*   End-to-end tests covering upload, download, and scanning
*   Run: `python test_comprehensive.py`

**`test_model_integration.py`**:
*   Validates that the ML model loads and makes predictions
*   Run: `python test_model_integration.py`

**`test_real_download.py`**:
*   Tests a real torrent download (requires internet + qBittorrent)
*   Run: `python test_real_download.py`

---

## Troubleshooting

### "Python is not installed or not in PATH"
**Cause**: Python not installed, or PATH not configured  
**Solution**: Reinstall Python with "Add to PATH" checked

### "qBittorrent not found"
**Cause**: `setup_and_run.bat` looks in `C:\Program Files\qBittorrent\`  
**Solution**: Either install qBittorrent there, manually start it first, or run in Mock Mode

### "ImportError: No module named..."
**Cause**: Dependencies not installed  
**Solution**: `pip install -r requirements_loose.txt`

### "Port 5000 already in use"
**Cause**: Another application is using port 5000  
**Solution**: Stop the other app, or edit `api_server.py` to use a different port:
```python
socketio.run(app, host='0.0.0.0', port=8080, debug=True)
```

### "ML model failed to load"
**Cause**: `models/malware_detector_latest.pkl` is missing or corrupt  
**Solution**: Retrain the model: `python train_model.py`

### Downloads stuck at 0%
**Cause**: qBittorrent not connected to peers  
**Solution**: Check firewall settings, ensure torrent has seeders

---

## Development

### Running in Development Mode

```bash
# Enable debug logging
set FLASK_DEBUG=1
python api_server.py
```


