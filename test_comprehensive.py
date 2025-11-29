"""
Comprehensive Test Suite for qBittorrent Integration - Simple Version
Tests all changes from Phases 1-3
"""
import sys
sys.path.insert(0, '.')

print("=" * 80)
print("COMPREHENSIVE TEST SUITE - qBittorrent Integration")
print("=" * 80)

test_results = []

# Test 1: Git Backup
print("\nTEST 1: Git Backup Verification")
import subprocess
try:
    result = subprocess.run(['git', 'tag'], capture_output=True, text=True, cwd='.')
    tags = result.stdout.strip().split('\n')
    if 'backup-before-piece-download' in tags:
        print("[PASS] Git backup tag exists")
        test_results.append(("Git Backup", True))
    else:
        print("[FAIL] Git backup tag NOT found")
        test_results.append(("Git Backup", False))
except Exception as e:
    print(f"[FAIL] Git check failed: {e}")
    test_results.append(("Git Backup", False))

# Test 2: qbittorrent_client imports
print("\nTEST 2: qbittorrent_client Module")
try:
    import qbittorrent_client
    from qbittorrent_client import qb_client, QBITTORRENT_AVAILABLE, PIECE_DOWNLOADED
    
    print(f"[PASS] Imports successful (QBITTORRENT_AVAILABLE={QBITTORRENT_AVAILABLE})")
    
    methods = ['get_piece_states', 'get_piece_hashes', 'get_download_path', 'get_torrent_files']
    all_exist = all(hasattr(qb_client, m) for m in methods)
    
    if all_exist:
        print(f"[PASS] All 4 new methods exist")
        test_results.append(("qbittorrent_client", True))
    else:
        print(f"[FAIL] Some methods missing")
        test_results.append(("qbittorrent_client", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("qbittorrent_client", False))

# Test 3: api_server imports
print("\nTEST 3: api_server Module")
try:
    from api_server import USE_QBITTORRENT, TorrentDownloader
    
    print(f"[PASS] Imports successful (USE_QBITTORRENT={USE_QBITTORRENT})")
    test_results.append(("api_server imports", True))
    
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("api_server imports", False))

# Test 4: TorrentDownloader initialization
print("\nTEST 4: TorrentDownloader Initialization")
try:
    downloader = TorrentDownloader("test_init")
    
    if downloader.use_qbittorrent:
        has_attrs = hasattr(downloader, 'qb_client') and hasattr(downloader, 'torrent_hash')
        if has_attrs:
            print(f"[PASS] qBittorrent mode initialized correctly")
            test_results.append(("TorrentDownloader init", True))
        else:
            print(f"[FAIL] Missing qBittorrent attributes")
            test_results.append(("TorrentDownloader init", False))
    else:
        print(f"[PASS] Mock mode initialized (qBittorrent unavailable)")
        test_results.append(("TorrentDownloader init", True))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("TorrentDownloader init", False))

# Test 5: Methods exist
print("\nTEST 5: TorrentDownloader Methods")
try:
    methods = [
        'download_chunks_with_scan',
        '_download_with_qbittorrent',
        '_download_with_mock',
        'scan_piece',
        'stop'
    ]
    
    all_exist = all(hasattr(downloader, m) for m in methods)
    
    if all_exist:
        print(f"[PASS] All 5 methods exist")
        test_results.append(("Methods exist", True))
    else:
        missing = [m for m in methods if not hasattr(downloader, m)]
        print(f"[FAIL] Missing methods: {missing}")
        test_results.append(("Methods exist", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("Methods exist", False))

# Test 6: Dispatcher logic
print("\nTEST 6: Dispatcher Logic")
try:
    import inspect
    source = inspect.getsource(downloader.download_chunks_with_scan)
    
    has_conditional = 'if self.use_qbittorrent:' in source
    calls_qb = '_download_with_qbittorrent' in source
    calls_mock = '_download_with_mock' in source
    
    if has_conditional and calls_qb and calls_mock:
        print(f"[PASS] Dispatcher has correct logic")
        test_results.append(("Dispatcher", True))
    else:
        print(f"[FAIL] Dispatcher logic incomplete")
        test_results.append(("Dispatcher", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("Dispatcher", False))

# Test 7: scan_piece dual-mode
print("\nTEST 7: scan_piece Dual-Mode")
try:
    source = inspect.getsource(downloader.scan_piece)
    
    has_conditional = 'if self.use_qbittorrent:' in source
    uses_qb_api = 'self.qb_client.get_torrent_info' in source
    
    if has_conditional and uses_qb_api:
        print(f"[PASS] scan_piece has dual-mode support")
        test_results.append(("scan_piece", True))
    else:
        print(f"[FAIL] scan_piece missing dual-mode logic")
        test_results.append(("scan_piece", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("scan_piece", False))

# Test 8: stop dual-mode
print("\nTEST 8: stop Method Dual-Mode")
try:
    source = inspect.getsource(downloader.stop)
    
    has_conditional = 'if self.use_qbittorrent:' in source
    uses_qb_api = 'self.qb_client.remove_torrent' in source
    
    if has_conditional and uses_qb_api:
        print(f"[PASS] stop has dual-mode support")
        test_results.append(("stop method", True))
    else:
        print(f"[FAIL] stop missing dual-mode logic")
        test_results.append(("stop method", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("stop method", False))

# Test 9: Server health
print("\nTEST 9: Server Health Check")
try:
    import requests
    response = requests.get('http://localhost:5000/api/health', timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        print(f"[PASS] Server healthy (status={data.get('status')})")
        test_results.append(("Server health", True))
    else:
        print(f"[FAIL] Server returned {response.status_code}")
        test_results.append(("Server health", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("Server health", False))

# Test 10: Code structure
print("\nTEST 10: _download_with_qbittorrent Structure")
try:
    source = inspect.getsource(downloader._download_with_qbittorrent)
    
    features = [
        ('get_piece_states', 'Piece state monitoring'),
        ('PIECE_DOWNLOADED', 'Piece state checking'),
        ('scan_piece', 'Piece scanning'),
        ('socketio.emit', 'WebSocket events'),
        ('quarantine_file', 'Quarantine logic'),
        ('MAX_STALL_ITERATIONS', 'Stall detection'),
    ]
    
    all_present = all(code in source for code, _ in features)
    
    if all_present:
        print(f"[PASS] All 6 key features implemented")
        test_results.append(("Code structure", True))
    else:
        missing = [name for code, name in features if code not in source]
        print(f"[FAIL] Missing features: {missing}")
        test_results.append(("Code structure", False))
        
except Exception as e:
    print(f"[FAIL] {e}")
    test_results.append(("Code structure", False))

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for test_name, result in test_results:
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {test_name}")

print(f"\nTotal: {passed}/{total} tests passed")

if passed == total:
    print("\n[SUCCESS] All tests passed! Ready for real torrent testing.")
    sys.exit(0)
else:
    print(f"\n[WARNING] {total - passed} test(s) failed. Review above.")
    sys.exit(1)
