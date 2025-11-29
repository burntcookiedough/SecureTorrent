import requests
import time
from socketio import Client

API_URL = "http://localhost:5000"

def test_upload_torrent():
    """Test uploading a torrent file"""
    print("\n1️⃣ Testing torrent upload...")
    
    with open('tiny-iso-test_archive.torrent', 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{API_URL}/api/upload-torrent", files=files)
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")
    
    return data['torrent']['torrent_id'] if data.get('success') else None


def test_start_download(torrent_id):
    """Test starting a download"""
    print(f"\n2️⃣ Starting download for torrent: {torrent_id}")
    
    response = requests.post(
        f"{API_URL}/api/start-download",
        json={'torrent_id': torrent_id, 'num_pieces': 5}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")
    
    return data['download_id'] if data.get('success') else None


def test_websocket_updates(download_id):
    """Test WebSocket real-time updates"""
    print(f"\n3️⃣ Connecting to WebSocket for real-time updates...")
    
    sio = Client()
    
    @sio.on('connect')
    def on_connect():
        print('✓ Connected to WebSocket')
        sio.emit('subscribe_download', {'download_id': download_id})
    
    @sio.on('download_started')
    def on_started(data):
        print(f"\n📥 Download Started:")
        print(f"   Name: {data['name']}")
        print(f"   Size: {data['total_size'] / (1024**2):.2f} MB")
        print(f"   Pieces: {data['downloading_pieces']}/{data['total_pieces']}")
    
    @sio.on('download_progress')
    def on_progress(data):
        print(f"\r⏳ Progress: {data['progress']:.1f}% | "
              f"Peers: {data['peers']} | "
              f"State: {data['state']}", end='')
    
    @sio.on('piece_downloaded')
    def on_piece(data):
        print(f"\n✓ Piece {data['piece_index']} downloaded")
        print(f"   Hash: {data['piece_hash'][:16]}...")
        print(f"   Scan: {'🔴 MALICIOUS' if data['scan_result']['malicious'] else '🟢 CLEAN'}")
    
    @sio.on('download_complete')
    def on_complete(data):
        print(f"\n\n✅ Download Complete!")
        print(f"   Pieces: {data['pieces_downloaded']}")
        print(f"   File: {data['file_path']}")
        sio.disconnect()
    
    @sio.on('download_error')
    def on_error(data):
        print(f"\n❌ Error: {data['error']}")
        sio.disconnect()
    
    try:
        sio.connect(API_URL)
        sio.wait()
    except Exception as e:
        print(f"WebSocket error: {e}")


if __name__ == '__main__':
    print("="*60)
    print("🧪 Testing Torrent Malware Detection API")
    print("="*60)
    
    # Test 1: Upload torrent
    torrent_id = test_upload_torrent()
    
    if torrent_id:
        # Test 2: Start download
        download_id = test_start_download(torrent_id)
        
        if download_id:
            # Test 3: Monitor via WebSocket
            test_websocket_updates(download_id)
    
    print("\n" + "="*60)
    print("✅ API testing complete!")
    print("="*60)
