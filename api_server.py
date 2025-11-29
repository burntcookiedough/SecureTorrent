print("DEBUG: Starting imports...")
from flask import Flask, request, jsonify, send_from_directory
print("DEBUG: Imported Flask")
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import threading
import time
from datetime import datetime
import hashlib
print("DEBUG: Importing MalwareDetector...")
from malware_detector import MalwareDetector
print("DEBUG: Imported MalwareDetector")

# Try qBittorrent first, then fall back to mock
USE_QBITTORRENT = False
try:
    import qbittorrent_client
    if qbittorrent_client.QBITTORRENT_AVAILABLE:
        USE_QBITTORRENT = True
        print("[OK] Using qBittorrent for REAL torrenting")
    else:
        raise ImportError("qBittorrent not available")
except Exception as e:
    import mock_libtorrent as lt
    print(f"[WARN] qBittorrent not available ({e}). Using MOCK implementation.")

print("DEBUG: Initializing Flask app...")
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
QUARANTINE_FOLDER = os.path.join(os.getcwd(), "quarantine")  # NEW
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QUARANTINE_FOLDER, exist_ok=True)  # NEW


# Global state management
active_downloads = {}
scan_results = {}
quarantined_files = {}
# Initialize ML detector
try:
    print("DEBUG: Loading MalwareDetector model...")
    detector = MalwareDetector()  # Uses pre-trained model
    print("DEBUG: MalwareDetector loaded")
    print("[OK] Malware detector loaded successfully")
except Exception as e:
    print(f"[WARN] Malware detector failed to load: {e}")
    detector = None
# ============= QUARANTINE HELPER FUNCTIONS =============
def quarantine_file(file_path, scan_result, download_id):
    """
    Move malicious file to quarantine folder
    """
    if not os.path.exists(file_path):
        return {'success': False, 'error': 'File not found'}
    
    try:
        # Create quarantine record
        file_name = os.path.basename(file_path)
        quarantine_id = hashlib.md5(f"{file_name}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Move file to quarantine
        quarantine_path = os.path.join(QUARANTINE_FOLDER, f"{quarantine_id}_{file_name}")
        os.rename(file_path, quarantine_path)
        
        # Store quarantine record
        quarantined_files[quarantine_id] = {
            'quarantine_id': quarantine_id,
            'original_name': file_name,
            'download_id': download_id,
            'quarantine_path': quarantine_path,
            'scan_result': scan_result,
            'quarantined_at': datetime.now().isoformat(),
            'status': 'quarantined'
        }
        
        print(f"[SEC] Quarantined: {file_name} (Risk: {scan_result.get('risk_score', 0):.1f}%)")
        
        return {
            'success': True,
            'quarantine_id': quarantine_id,
            'message': f'File quarantined: {file_name}'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def restore_from_quarantine(quarantine_id, restore_path=None):
    """
    Restore file from quarantine (use with caution!)
    """
    if quarantine_id not in quarantined_files:
        return {'success': False, 'error': 'Quarantine record not found'}
    
    try:
        record = quarantined_files[quarantine_id]
        quarantine_path = record['quarantine_path']
        
        if not os.path.exists(quarantine_path):
            return {'success': False, 'error': 'Quarantined file not found'}
        
        # Determine restore path
        if restore_path is None:
            restore_path = os.path.join(DOWNLOAD_FOLDER, record['original_name'])
        
        # Move file back
        os.rename(quarantine_path, restore_path)
        
        # Update record
        record['status'] = 'restored'
        record['restored_at'] = datetime.now().isoformat()
        record['restored_to'] = restore_path
        
        print(f"✅ Restored: {record['original_name']} to {restore_path}")
        
        return {
            'success': True,
            'message': f"File restored to {restore_path}"
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
# ============= TORRENT CLIENT CLASS =============
class TorrentDownloader:
    def __init__(self, download_id):
        self.download_id = download_id
        self.use_qbittorrent = USE_QBITTORRENT
        self.stopped = False
        
        if self.use_qbittorrent:
            # qBittorrent mode
            self.qb_client = qbittorrent_client.qb_client
            self.torrent_hash = None
            self.torrent_info = None
            print(f"[INFO] TorrentDownloader initialized in qBittorrent mode")
        else:
            # Mock libtorrent mode (fallback)
            import mock_libtorrent as lt
            self.session = lt.session()
            
            settings = self.session.get_settings()
            settings['listen_interfaces'] = '0.0.0.0:6881'
            settings['enable_dht'] = True
            settings['enable_lsd'] = True
            settings['enable_upnp'] = True
            settings['enable_natpmp'] = True
            settings['announce_to_all_trackers'] = True
            settings['announce_to_all_tiers'] = True
            self.session.apply_settings(settings)
            
            self.session.add_dht_router("router.bittorrent.com", 6881)
            self.session.add_dht_router("router.utorrent.com", 6881)
            self.session.add_dht_router("dht.transmissionbt.com", 6881)
            self.session.start_dht()
            
            self.handle = None
            self.info = None
            print(f"[INFO] TorrentDownloader initialized in mock mode")


    def download_chunks_with_scan(self, torrent_file_path, save_path, num_pieces=10):
        """Download torrent with chunk-level scanning - dispatches to qBittorrent or mock"""
        if self.use_qbittorrent:
            return self._download_with_qbittorrent(torrent_file_path, save_path, num_pieces)
        else:
            return self._download_with_mock(torrent_file_path, save_path, num_pieces)
    
    def _download_with_mock(self, torrent_file_path, save_path, num_pieces=10):
        """Download using mock libtorrent (fallback mode)"""
        import mock_libtorrent as lt
        
        try:
            self.info = lt.torrent_info(torrent_file_path)
        
            params = {
                'save_path': save_path,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                'ti': self.info
            }
        
            self.handle = self.session.add_torrent(params)
        
            total_pieces = self.info.num_pieces()
            num_pieces = min(num_pieces, total_pieces)
        
        # Prioritize only first N pieces
            priorities = [0] * total_pieces
            for i in range(num_pieces):
                priorities[i] = 7
        
            self.handle.prioritize_pieces(priorities)
        
            # Emit initial status
            socketio.emit('download_started', {
                'download_id': self.download_id,
                'name': self.info.name(),
                'total_size': self.info.total_size(),
                'total_pieces': total_pieces,
                'downloading_pieces': num_pieces,
                'piece_size': self.info.piece_length()
            })
        
            pieces_downloaded = set()
        
            while len(pieces_downloaded) < num_pieces and not self.stopped:
                s = self.handle.status()
            
                state_str = [
                    'queued', 'checking', 'downloading metadata',
                    'downloading', 'finished', 'seeding', 'allocating',
                    'checking fastresume', 'unknown'
                ]
                state_idx = min(s.state, len(state_str) - 1)
            
                # Check for newly downloaded pieces
                if s.has_metadata:
                    for i in range(num_pieces):
                        if self.handle.have_piece(i) and i not in pieces_downloaded:
                            pieces_downloaded.add(i)
                        
                         # 🔬 HOOK FOR ML MALWARE DETECTION
                            piece_hash = str(self.info.hash_for_piece(i))
                            scan_result = self.scan_piece(i, piece_hash)
                        
                            socketio.emit('piece_downloaded', {
                                'download_id': self.download_id,
                                'piece_index': i,
                                'piece_hash': piece_hash,
                                'scan_result': scan_result,
                                'progress': (len(pieces_downloaded) / num_pieces) * 100
                            })
            
            # Emit progress update
                progress_percent = (len(pieces_downloaded) / num_pieces) * 100
                socketio.emit('download_progress', {
                    'download_id': self.download_id,
                    'progress': progress_percent,
                    'state': state_str[state_idx],
                    'peers': s.num_peers,
                    'download_rate': s.download_rate,
                    'pieces_completed': len(pieces_downloaded),
                    'total_pieces': num_pieces
                })
            
                time.sleep(0.5)
        
        # ============ NEW QUARANTINE LOGIC ============
            if not self.stopped:
                file_path = os.path.join(save_path, self.info.name())
                print(f"📊 Checking scan results for {self.download_id}")  # ADD THIS
                print(f"   scan_results keys: {list(scan_results.keys())}")  # ADD THIS
            # Collect all scan results
                all_scans = []
                max_risk = 0
                malicious_count = 0
            
                for piece_idx in pieces_downloaded:
                    if self.download_id in scan_results and piece_idx in scan_results[self.download_id]:
                        scan = scan_results[self.download_id][piece_idx]
                        all_scans.append(scan)
                        max_risk = max(max_risk, scan.get('risk_score', 0))
                        if scan.get('malicious', False):
                            malicious_count += 1
            
            # Calculate overall verdict
                overall_risk = max_risk
                verdict = 'CLEAN'
            
                if max_risk > 70:
                    verdict = 'MALICIOUS'
                elif max_risk > 40:
                    verdict = 'SUSPICIOUS'
            
            # Quarantine if malicious
                quarantine_result = None
                if verdict == 'MALICIOUS':
                    quarantine_result = quarantine_file(
                        file_path,
                        {
                            'max_risk_score': max_risk,
                            'malicious_pieces': malicious_count,
                            'total_pieces': len(pieces_downloaded),
                            'verdict': verdict,
                            'scans': all_scans
                        },
                        self.download_id
                    )
            
                socketio.emit('download_complete', {
                    'download_id': self.download_id,
                    'pieces_downloaded': len(pieces_downloaded),
                    'file_path': file_path,
                    'verdict': verdict,
                    'max_risk_score': max_risk,
                    'malicious_pieces': malicious_count,
                    'quarantined': quarantine_result is not None and quarantine_result.get('success'),
                    'quarantine_info': quarantine_result
                })
        # ============================================
            
            return {
                'success': True,
                'pieces_downloaded': len(pieces_downloaded),
                'file_name': self.info.name()
            }
        
        except Exception as e:
            socketio.emit('download_error', {
                'download_id': self.download_id,
                'error': str(e)
            })
            return {'success': False, 'error': str(e)}
    
    def _download_with_qbittorrent(self, torrent_file_path, save_path, num_pieces=10):
        """Download using qBittorrent with TRUE piece-level scanning"""
        try:
            # Step 1: Parse torrent metadata
            import mock_libtorrent as lt_parser
            self.torrent_info = lt_parser.torrent_info(torrent_file_path)
            
            total_pieces = self.torrent_info.num_pieces()
            num_pieces = min(num_pieces, total_pieces)
            
            # Step 2: Add torrent to qBittorrent
            abs_save_path = os.path.abspath(save_path)
            print(f"[INFO] Adding torrent to qBittorrent. Save path: {abs_save_path}")
            if not os.path.exists(abs_save_path):
                print(f"[WARN] Save path does not exist, creating: {abs_save_path}")
                os.makedirs(abs_save_path, exist_ok=True)

            self.torrent_hash = self.qb_client.add_torrent(torrent_file_path, abs_save_path)
            print(f"[OK] Torrent added to qBittorrent: {self.torrent_hash}")
            
            # Step 3: Emit download_started
            socketio.emit('download_started', {
                'download_id': self.download_id,
                'name': self.torrent_info.name(),
                'total_size': self.torrent_info.total_size(),
                'total_pieces': total_pieces,
                'downloading_pieces': num_pieces,
                'piece_size': self.torrent_info.piece_length()
            })
            
            # Step 4: Monitor download loop
            pieces_downloaded = set()
            pieces_scanned = set()
            last_progress = 0
            stall_counter = 0
            MAX_STALL_ITERATIONS = 600  # 5 minutes
            
            while len(pieces_downloaded) < num_pieces and not self.stopped:
                # Get current piece states
                piece_states = self.qb_client.get_piece_states(self.torrent_hash)
                
                if not piece_states:
                    print("[WARN] No piece states yet, waiting for metadata...")
                    time.sleep(1)
                    continue
                
                # Get torrent info for progress/peers
                info = self.qb_client.get_torrent_info(self.torrent_hash)
                
                # Check for errors
                if info['state'] == qbittorrent_client.STATE_ERROR:
                    print(f"[ERR] Torrent in ERROR state. Full info: {info}")
                    error_msg = info.get('error', 'Unknown')
                    error_prog = info.get('error_prog', '')
                    raise Exception(f"Torrent error: {error_msg} (Prog: {error_prog})")
                
                # Check for newly downloaded pieces
                for i in range(min(num_pieces, len(piece_states))):
                    piece_state = piece_states[i]
                    
                    # Piece is fully downloaded
                    if piece_state == qbittorrent_client.PIECE_DOWNLOADED:
                        if i not in pieces_downloaded:
                            pieces_downloaded.add(i)
                            
                            # Scan this piece
                            if i not in pieces_scanned:
                                pieces_scanned.add(i)
                                piece_hash = f"piece_{i}_{self.torrent_hash[:8]}"
                                scan_result = self.scan_piece(i, piece_hash)
                                
                                socketio.emit('piece_downloaded', {
                                    'download_id': self.download_id,
                                    'piece_index': i,
                                    'piece_hash': piece_hash,
                                    'scan_result': scan_result,
                                    'progress': (len(pieces_downloaded) / num_pieces) * 100
                                })
                                
                                print(f"[PIECE] Piece {i}/{num_pieces} downloaded and scanned")
                
                # Emit progress update
                progress_percent = (len(pieces_downloaded) / num_pieces) * 100
                socketio.emit('download_progress', {
                    'download_id': self.download_id,
                    'progress': progress_percent,
                    'state': info['state'],
                    'peers': info.get('num_peers', 0),
                    'download_rate': info.get('download_rate', 0),
                    'pieces_completed': len(pieces_downloaded),
                    'total_pieces': num_pieces
                })
                
                # Stall detection
                if progress_percent == last_progress:
                    stall_counter += 1
                    if stall_counter > MAX_STALL_ITERATIONS:
                        raise Exception("Download stalled for 5 minutes, aborting")
                else:
                    stall_counter = 0
                    last_progress = progress_percent
                
                time.sleep(0.5)
            
            # Step 5: Download complete - quarantine check
            if not self.stopped:
                file_path = self.qb_client.get_download_path(self.torrent_hash)
                
                # Collect scan results
                all_scans = []
                max_risk = 0
                malicious_count = 0
                
                for piece_idx in pieces_downloaded:
                    if self.download_id in scan_results and piece_idx in scan_results[self.download_id]:
                        scan = scan_results[self.download_id][piece_idx]
                        all_scans.append(scan)
                        max_risk = max(max_risk, scan.get('risk_score', 0))
                        if scan.get('malicious', False):
                            malicious_count += 1
                
                # Determine verdict
                verdict = 'CLEAN'
                if max_risk > 70:
                    verdict = 'MALICIOUS'
                elif max_risk > 40:
                    verdict = 'SUSPICIOUS'
                
                # Quarantine if malicious
                quarantine_result = None
                if verdict == 'MALICIOUS':
                    self.qb_client.pause_torrent(self.torrent_hash)
                    quarantine_result = quarantine_file(
                        file_path,
                        {
                            'max_risk_score': max_risk,
                            'malicious_pieces': malicious_count,
                            'total_pieces': len(pieces_downloaded),
                            'verdict': verdict,
                            'scans': all_scans
                        },
                        self.download_id
                    )
                
                # Remove from qBittorrent
                delete_files = (verdict == 'MALICIOUS')
                self.qb_client.remove_torrent(self.torrent_hash, delete_files=delete_files)
                
                # Emit completion
                socketio.emit('download_complete', {
                    'download_id': self.download_id,
                    'pieces_downloaded': len(pieces_downloaded),
                    'file_path': file_path,
                    'verdict': verdict,
                    'max_risk_score': max_risk,
                    'malicious_pieces': malicious_count,
                    'quarantined': quarantine_result is not None and quarantine_result.get('success'),
                    'quarantine_info': quarantine_result
                })
                
                return {
                    'success': True,
                    'pieces_downloaded': len(pieces_downloaded),
                    'file_name': self.torrent_info.name()
                }
        
        except Exception as e:
            print(f"[ERR] qBittorrent download error: {e}")
            import traceback
            traceback.print_exc()
            
            # Cleanup
            if self.torrent_hash:
                try:
                    self.qb_client.remove_torrent(self.torrent_hash, delete_files=True)
                except:
                    pass
            
            socketio.emit('download_error', {
                'download_id': self.download_id,
                'error': str(e)
            })
            
            return {'success': False, 'error': str(e)}


    def scan_piece(self, piece_index, piece_hash):
        """[ML] Multi-layer Malware Detection"""
    
        print(f"[SCAN] Scanning piece {piece_index} for download {self.download_id}")
    
        if detector is None:
            return {
                'malicious': False,
                'confidence': 0.0,
                'risk_score': 0.0,
                'verdict': 'CLEAN', # Default to CLEAN if detector is broken
                'scanner': 'unavailable',
                'timestamp': datetime.now().isoformat(),
                'error': 'ML model not loaded'
            }

        try:
           
           
                # Get piece data based on mode
            if self.use_qbittorrent:
                # qBittorrent mode
                info = self.qb_client.get_torrent_info(self.torrent_hash)
                piece_data = {
                    'src_bytes': self.torrent_info.piece_length(),
                    'dst_bytes': 0,
                    'peer_count': info.get('num_peers', 0),
                    'seed_count': info.get('num_seeds', 0),
                    'num_files': 1  # Simplified
                }
            else:
                # Mock mode
                piece_data = {
                    'src_bytes': self.info.piece_length(),
                    'dst_bytes': 0,
                    'peer_count': self.handle.status().num_peers if self.handle else 0,
                    'seed_count': self.handle.status().num_seeds if self.handle else 0,
                    'num_files': self.info.num_files()
                }
            
        
            # Run detection (rest stays the same)
            result = detector.predict(piece_data, file_path=None)
        
            scan_result = {
                'malicious': result['ml_detection']['is_malicious'],
                'confidence': result['ml_detection']['confidence'],
                'risk_score': result['combined_risk_score'],
                'verdict': result['verdict'],
                'scanner': 'random_forest',
                'timestamp': datetime.now().isoformat()
            }
        
            # Store scan result
            if self.download_id not in scan_results:
                scan_results[self.download_id] = {}
            scan_results[self.download_id][piece_index] = scan_result
        
            print(f"[OK] Piece {piece_index} scanned: {scan_result['verdict']} (Risk: {scan_result['risk_score']:.1f}%)")
        
            return scan_result
        
        except Exception as e:
            print(f"[ERR] Scan error for piece {piece_index}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'malicious': False,
                'confidence': 0.0,
                'risk_score': 0.0,
                'verdict': 'ERROR', # Ensure verdict is present
                'scanner': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def stop(self):
        """Stop the download"""
        self.stopped = True
        
        if self.use_qbittorrent:
            if self.torrent_hash:
                try:
                    self.qb_client.remove_torrent(self.torrent_hash, delete_files=True)
                    print(f"[STOP] qBittorrent torrent removed: {self.torrent_hash}")
                except Exception as e:
                    print(f"[WARN] Failed to remove torrent: {e}")
        else:
            if self.handle:
                self.session.remove_torrent(self.handle)
                print(f"[STOP] Mock torrent removed")


# ============= REST API ENDPOINTS =============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'active_downloads': len(active_downloads),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/quarantine/list', methods=['GET'])
def list_quarantined():
    """List all quarantined files"""
    return jsonify({
        'quarantined_files': list(quarantined_files.values()),
        'count': len(quarantined_files)
    })


@app.route('/api/quarantine/<quarantine_id>', methods=['GET'])
def get_quarantine_details(quarantine_id):
    """Get details of a quarantined file"""
    if quarantine_id not in quarantined_files:
        return jsonify({'error': 'Quarantine record not found'}), 404
    
    return jsonify(quarantined_files[quarantine_id])


@app.route('/api/quarantine/<quarantine_id>/restore', methods=['POST'])
def restore_quarantined(quarantine_id):
    """Restore a quarantined file (use with caution!)"""
    data = request.json or {}
    restore_path = data.get('restore_path')
    
    result = restore_from_quarantine(quarantine_id, restore_path)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@app.route('/api/quarantine/<quarantine_id>/delete', methods=['DELETE'])
def delete_quarantined(quarantine_id):
    """Permanently delete a quarantined file"""
    if quarantine_id not in quarantined_files:
        return jsonify({'error': 'Quarantine record not found'}), 404
    
    try:
        record = quarantined_files[quarantine_id]
        quarantine_path = record['quarantine_path']
        
        if os.path.exists(quarantine_path):
            os.remove(quarantine_path)
        
        del quarantined_files[quarantine_id]
        
        return jsonify({
            'success': True,
            'message': f"File permanently deleted: {record['original_name']}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-torrent', methods=['POST'])
def upload_torrent():
    """Upload .torrent file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.torrent'):
        return jsonify({'error': 'File must be a .torrent file'}), 400
    
    # Save the torrent file
    filename = f"{hashlib.md5(file.filename.encode()).hexdigest()}.torrent"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Parse torrent info
    try:
        # Use mock_libtorrent for parsing (works for both modes)
        import mock_libtorrent as lt_parser
        info = lt_parser.torrent_info(filepath)
        torrent_data = {
            'torrent_id': filename.replace('.torrent', ''),
            'name': info.name(),
            'total_size': info.total_size(),
            'total_pieces': info.num_pieces(),
            'piece_size': info.piece_length(),
            'file_path': filepath
        }
        
        return jsonify({
            'success': True,
            'torrent': torrent_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Invalid torrent file: {str(e)}'}), 400


@app.route('/api/start-download', methods=['POST'])
def start_download():
    """Start downloading torrent with chunk-level scanning"""
    data = request.json
    
    if not data or 'torrent_id' not in data:
        return jsonify({'error': 'torrent_id required'}), 400
    
    torrent_id = data['torrent_id']
    num_pieces = data.get('num_pieces', 10)
    
    torrent_file = os.path.join(UPLOAD_FOLDER, f"{torrent_id}.torrent")
    
    if not os.path.exists(torrent_file):
        return jsonify({'error': 'Torrent file not found'}), 404
    
    download_id = hashlib.md5(f"{torrent_id}_{datetime.now().isoformat()}".encode()).hexdigest()
    
    downloader = TorrentDownloader(download_id)
    active_downloads[download_id] = downloader
    
    def download_thread():
        try:
            print(f"[START] Download thread started: {download_id}")
            result = downloader.download_chunks_with_scan(
                torrent_file,
                DOWNLOAD_FOLDER,
                num_pieces
            )
            print(f"[OK] Download completed: {result}")
        except Exception as e:
            print(f"[ERR] Download thread error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up download, but KEEP scan results
            if download_id in active_downloads:
                del active_downloads[download_id]
            
            # Print scan results status
            if download_id in scan_results:
                print(f"[OK] Scan results preserved: {len(scan_results[download_id])} pieces")
            else:
                print(f"[WARN] No scan results found for {download_id}")
            
            print(f"[CLEAN] Download thread cleaned up: {download_id}")
    
    # Use socketio background task for compatibility with eventlet/gevent
    socketio.start_background_task(download_thread)
    
    return jsonify({
        'success': True,
        'download_id': download_id,
        'message': 'Download started'
    }), 202



@app.route('/api/download-status/<download_id>', methods=['GET'])
def download_status(download_id):
    """Get download status"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    downloader = active_downloads[download_id]
    
    if downloader.handle:
        s = downloader.handle.status()
        state_str = [
            'queued', 'checking', 'downloading metadata',
            'downloading', 'finished', 'seeding', 'allocating',
            'checking fastresume', 'unknown'
        ]
        state_idx = min(s.state, len(state_str) - 1)
        
        return jsonify({
            'download_id': download_id,
            'state': state_str[state_idx],
            'progress': s.progress * 100,
            'peers': s.num_peers,
            'download_rate': s.download_rate,
            'upload_rate': s.upload_rate
        })
    
    return jsonify({'error': 'Download not active'}), 400


@app.route('/api/stop-download/<download_id>', methods=['POST'])
def stop_download(download_id):
    """Stop a download"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    downloader = active_downloads[download_id]
    downloader.stop()
    del active_downloads[download_id]
    
    return jsonify({
        'success': True,
        'message': 'Download stopped'
    })


@app.route('/api/scan-results/<download_id>', methods=['GET'])
def get_scan_results(download_id):
    """Get malware scan results for a download"""
    if download_id in scan_results:
        return jsonify({
            'download_id': download_id,
            'results': scan_results[download_id]
        })
    
    return jsonify({'error': 'No scan results found'}), 404


@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """List all active downloads"""
    downloads = []
    for download_id, downloader in active_downloads.items():
        if downloader.info:
            downloads.append({
                'download_id': download_id,
                'name': downloader.info.name(),
                'total_size': downloader.info.total_size()
            })
    
    return jsonify({'downloads': downloads})


# ============= WEBSOCKET EVENTS =============

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')


@socketio.on('subscribe_download')
def handle_subscribe(data):
    """Client subscribes to download updates"""
    download_id = data.get('download_id')
    print(f'Client {request.sid} subscribed to download {download_id}')

# ============= FRONTEND ROUTES =============

@app.route('/')
def serve_frontend():
    """Serve frontend HTML"""
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS, images)"""
    try:
        return send_from_directory('frontend', path)
    except:
        return send_from_directory('frontend', 'index.html')
# ============= RUN SERVER =============

if __name__ == '__main__':
    print("="*60)
    print("[INFO] Torrent Malware Detection API Server")
    print("="*60)
    print(f"[DIR] Downloads: {DOWNLOAD_FOLDER}")
    print(f"[DIR] Uploads: {UPLOAD_FOLDER}")
    print(f"[SEC] Quarantine: {QUARANTINE_FOLDER}")
    print("[WS] WebSocket: Enabled for real-time updates")
    
    # Show actual ML status
    if detector:
        print(f"[ML] ML Integration: [OK] ACTIVE (Random Forest)")
    else:
        print("[ML] ML Integration: [ERR] FAILED TO LOAD")
    
    print("="*60)
    print("\nAPI Endpoints:")
    print("  GET  /api/health")
    print("  POST /api/upload-torrent")
    print("  POST /api/start-download")
    print("  GET  /api/download-status/<id>")
    print("  POST /api/stop-download/<id>")
    print("  GET  /api/scan-results/<id>")
    print("  GET  /api/downloads")
    print("  GET    /api/quarantine/list")
    print("  GET    /api/quarantine/<id>")
    print("  POST   /api/quarantine/<id>/restore")
    print("  DELETE /api/quarantine/<id>/delete")
    print("\nStarting server on http://localhost:5000")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

