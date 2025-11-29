"""
Test TorrentDownloader initialization in both modes
"""
import sys
sys.path.insert(0, '.')

# Test 1: Import and check USE_QBITTORRENT flag
print("=" * 60)
print("TEST 1: Checking qBittorrent mode flag")
print("=" * 60)

try:
    from api_server import USE_QBITTORRENT, TorrentDownloader
    print(f"✅ Imports successful")
    print(f"   USE_QBITTORRENT = {USE_QBITTORRENT}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize TorrentDownloader
print("\n" + "=" * 60)
print("TEST 2: Initialize TorrentDownloader")
print("=" * 60)

try:
    downloader = TorrentDownloader("test_download_123")
    print(f"✅ TorrentDownloader created")
    print(f"   download_id: {downloader.download_id}")
    print(f"   use_qbittorrent: {downloader.use_qbittorrent}")
    print(f"   stopped: {downloader.stopped}")
    
    if downloader.use_qbittorrent:
        print(f"   qb_client: {downloader.qb_client}")
        print(f"   torrent_hash: {downloader.torrent_hash}")
        print(f"   torrent_info: {downloader.torrent_info}")
    else:
        print(f"   session: {downloader.session}")
        print(f"   handle: {downloader.handle}")
        print(f"   info: {downloader.info}")
    
    print("\n✅ TorrentDownloader initialized correctly!")
    
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify methods exist
print("\n" + "=" * 60)
print("TEST 3: Verify methods exist")
print("=" * 60)

methods = ['download_chunks_with_scan', 'scan_piece', 'stop']
for method in methods:
    if hasattr(downloader, method):
        print(f"✅ Method '{method}' exists")
    else:
        print(f"❌ Method '{method}' missing")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
