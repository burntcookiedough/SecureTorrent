"""
Automated Real Torrent Test
Downloads Sintel torrent, uploads to API, starts download, and monitors progress.
"""
import requests
import time
import os
import sys

API_URL = "http://localhost:5000/api"
TORRENT_URL = "https://webtorrent.io/torrents/sintel.torrent"
TORRENT_FILE = "sintel.torrent"

def run_test():
    print("=" * 60)
    print("[START] REAL TORRENT TEST (Sintel)")
    print("=" * 60)
    
    # Step 1: Download .torrent file
    print(f"\n[DL] Downloading {TORRENT_FILE}...")
    try:
        response = requests.get(TORRENT_URL)
        response.raise_for_status()
        with open(TORRENT_FILE, 'wb') as f:
            f.write(response.content)
        print("[OK] Torrent file downloaded successfully")
    except Exception as e:
        print(f"[ERR] Failed to download torrent file: {e}")
        return

    # Step 2: Upload to API
    print(f"\n[UL] Uploading to API...")
    try:
        with open(TORRENT_FILE, 'rb') as f:
            files = {'file': (TORRENT_FILE, f, 'application/x-bittorrent')}
            response = requests.post(f"{API_URL}/upload-torrent", files=files)
            response.raise_for_status()
            data = response.json()
            torrent_id = data['torrent']['torrent_id']
            print(f"[OK] Upload successful. Torrent ID: {torrent_id}")
    except Exception as e:
        print(f"[ERR] Upload failed: {e}")
        return

    # Step 3: Start Download
    print(f"\n[START] Starting download...")
    try:
        payload = {'torrent_id': torrent_id, 'num_pieces': 20}  # Download first 20 pieces
        response = requests.post(f"{API_URL}/start-download", json=payload)
        response.raise_for_status()
        data = response.json()
        download_id = data['download_id']
        print(f"[OK] Download started. Download ID: {download_id}")
    except Exception as e:
        print(f"[ERR] Start download failed: {e}")
        return

    # Step 4: Monitor Progress
    print(f"\n[MON] Monitoring progress (timeout: 60s)...")
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < 60:
        try:
            response = requests.get(f"{API_URL}/download-status/{download_id}")
            if response.status_code == 200:
                status = response.json()
                progress = status['progress']
                state = status['state']
                peers = status['peers']
                rate = status['download_rate'] / 1024  # KB/s
                
                # Print update only if changed
                if progress != last_progress or time.time() % 5 < 1:
                    print(f"   Status: {state} | Progress: {progress:.1f}% | Peers: {peers} | Rate: {rate:.1f} KB/s")
                    last_progress = progress
                
                if progress >= 100 or state in ['finished', 'seeding', 'uploading']:
                    print("\n[OK] Download COMPLETED!")
                    break
                    
                if state == 'error':
                    print("\n[ERR] Download ERROR reported by API")
                    break
            else:
                print(f"[WARN] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[WARN] Monitoring error: {e}")
            
        time.sleep(1)
    
    # Step 5: Check Scan Results
    print(f"\n[SCAN] Checking scan results...")
    try:
        response = requests.get(f"{API_URL}/scan-results/{download_id}")
        if response.status_code == 200:
            results = response.json()['results']
            print(f"[OK] Found {len(results)} scan results")
            for piece, res in list(results.items())[:3]:
                print(f"   Piece {piece}: {res['verdict']} (Risk: {res['risk_score']}%)")
        else:
            print(f"[WARN] No scan results found (might be too early)")
    except Exception as e:
        print(f"[WARN] Failed to get scan results: {e}")

    # Step 6: Stop Download
    print(f"\n[STOP] Stopping download...")
    try:
        requests.post(f"{API_URL}/stop-download/{download_id}")
        print("[OK] Download stopped")
    except Exception as e:
        print(f"[WARN] Failed to stop download: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
