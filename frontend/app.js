const API_URL = window.location.origin;
const socket = io(API_URL);

let torrentId = null;
let downloadId = null;
let maxRisk = 0;

// Socket.IO connection
socket.on('connect', () => {
    console.log('✅ Connected to WebSocket');
});

socket.on('download_started', (data) => {
    console.log('Download started:', data);
    document.getElementById('progressSection').classList.remove('hidden');
});

socket.on('piece_downloaded', (data) => {
    // Update progress
    const progress = data.progress;
    document.getElementById('progressBar').style.width = progress + '%';
    document.getElementById('progressText').textContent = Math.round(progress) + '%';
    
    // Update risk
    const risk = data.scan_result.risk_score;
    maxRisk = Math.max(maxRisk, risk);
    
    const riskBar = document.getElementById('riskBar');
    riskBar.style.width = maxRisk + '%';
    
    if (maxRisk < 40) {
        riskBar.className = 'risk-fill risk-low';
    } else if (maxRisk < 70) {
        riskBar.className = 'risk-fill risk-medium';
    } else {
        riskBar.className = 'risk-fill risk-high';
    }
    
    document.getElementById('riskText').textContent = `RISK LEVEL: ${maxRisk.toFixed(1)}%`;
    
    // Add piece to list
    const pieceList = document.getElementById('pieceList');
    const pieceDiv = document.createElement('div');
    
    let verdictClass = 'clean';
    if (data.scan_result.verdict === 'MALICIOUS') verdictClass = 'malicious';
    else if (data.scan_result.verdict === 'SUSPICIOUS') verdictClass = 'suspicious';
    
    pieceDiv.className = `piece-item ${verdictClass}`;
    
    pieceDiv.innerHTML = `
        <span>PIECE #${data.piece_index} [${data.scan_result.verdict}]</span>
        <span>${data.scan_result.risk_score.toFixed(1)}%</span>
    `;
    
    pieceList.insertBefore(pieceDiv, pieceList.firstChild);
});

socket.on('download_complete', (data) => {
    console.log('Download complete:', data);
    
    const resultDiv = document.getElementById('resultSection');
    resultDiv.classList.remove('hidden');
    
    if (data.quarantined) {
        resultDiv.className = 'verdict malicious';
        resultDiv.innerHTML = `
            <h3>🔒 THREAT DETECTED - QUARANTINED</h3>
            <p>File has been isolated to prevent system infection.</p>
            <div style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">
                <p>Risk Score: ${data.max_risk_score.toFixed(1)}%</p>
                <p>Malicious Pieces: ${data.malicious_pieces} / ${data.pieces_downloaded}</p>
            </div>
        `;
    } else {
        const verdictClass = data.verdict.toLowerCase();
        resultDiv.className = `verdict ${verdictClass}`;
        
        const icon = data.verdict === 'CLEAN' ? '✅' : '⚠️';
        
        resultDiv.innerHTML = `
            <h3>${icon} SCAN COMPLETE: ${data.verdict}</h3>
            <p>Risk Score: ${data.max_risk_score.toFixed(1)}%</p>
            ${data.verdict === 'CLEAN' ? `<p style="margin-top: 10px; font-size: 0.8em; color: var(--success);">Saved to: ${data.file_path}</p>` : ''}
        `;
    }
    
    document.getElementById('startBtn').textContent = 'Download Complete';
});

async function uploadTorrent() {
    const file = document.getElementById('torrentFile').files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/api/upload-torrent`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            torrentId = data.torrent.torrent_id;
            
            document.getElementById('uploadResult').innerHTML = `
                <div class="torrent-info">
                    <h3 style="color: var(--primary);">✅ FILE ANALYZED</h3>
                    <p><strong>Name:</strong> ${data.torrent.name}</p>
                    <p><strong>Size:</strong> ${(data.torrent.total_size / 1024 / 1024).toFixed(2)} MB</p>
                    <p><strong>Pieces:</strong> ${data.torrent.total_pieces}</p>
                </div>
            `;
            
            document.getElementById('uploadResult').classList.remove('hidden');
            document.getElementById('startBtn').disabled = false;
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Upload failed: ' + error);
    }
}

async function startDownload() {
    if (!torrentId) return;
    
    try {
        const response = await fetch(`${API_URL}/api/start-download`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                torrent_id: torrentId,
                num_pieces: 10 // Scan first 10 pieces
            })
        });
        
        const data = await response.json();
        downloadId = data.download_id;
        
        document.getElementById('startBtn').disabled = true;
        document.getElementById('startBtn').textContent = 'SCANNING IN PROGRESS...';
        
    } catch (error) {
        alert('Download failed: ' + error);
    }
}
