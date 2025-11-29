"""
qBittorrent Client Adapter
Provides libtorrent-compatible interface using qBittorrent Web API
"""
import qbittorrentapi
import time
import os
from typing import Optional, Dict, Any

# Connection settings
QBITTORRENT_HOST = 'localhost'
QBITTORRENT_PORT = 8080
QBITTORRENT_USERNAME = 'admin'
QBITTORRENT_PASSWORD = 'torrentguard2024'

# Piece states (from qBittorrent API)
PIECE_NOT_DOWNLOADED = 0
PIECE_DOWNLOADING = 1
PIECE_DOWNLOADED = 2

# Torrent states
STATE_ERROR = 'error'
STATE_PAUSED = 'pausedDL'
STATE_QUEUED = 'queuedDL'
STATE_DOWNLOADING = 'downloading'
STATE_STALLED = 'stalledDL'
STATE_CHECKING = 'checkingDL'
STATE_COMPLETE = 'uploading'  # seeding


class QBittorrentClient:
    """Adapter to make qBittorrent API look like libtorrent"""
    
    def __init__(self):
        self.client = qbittorrentapi.Client(
            host=QBITTORRENT_HOST,
            port=QBITTORRENT_PORT,
            username=QBITTORRENT_USERNAME,
            password=QBITTORRENT_PASSWORD,
            REQUESTS_ARGS={'timeout': 3}
        )
        try:
            print(f"DEBUG: Connecting to qBittorrent at {QBITTORRENT_HOST}:{QBITTORRENT_PORT}...")
            self.client.auth_log_in()
            print("DEBUG: qBittorrent connected")
            # This print statement is now handled by the singleton creation block
            # print(f"[OK] Connected to qBittorrent {self.client.app.version}")
        except Exception as e:
            print(f"[WARN] qBittorrent client initialization failed: {e}")
            print(f"[WARN] Make sure qBittorrent is running on {QBITTORRENT_HOST}:{QBITTORRENT_PORT}")
            self.client = None
    
    def add_torrent(self, torrent_file: str, save_path: str) -> str:
        """Add torrent and return hash"""
        with open(torrent_file, 'rb') as f:
            result = self.client.torrents_add(
                torrent_files=f,
                save_path=save_path
            )
        
        # Get the torrent hash
        time.sleep(1)  # Wait for torrent to be added
        torrents = self.client.torrents_info()
        if torrents:
            return torrents[-1].hash
        raise Exception("Failed to add torrent")
    
    def get_torrent_info(self, torrent_hash: str) -> Dict[str, Any]:
        """Get torrent information"""
        torrents = self.client.torrents_info(torrent_hashes=torrent_hash)
        if not torrents:
            raise Exception(f"Torrent {torrent_hash} not found")
        
        torrent = torrents[0]
        return {
            'name': torrent.name,
            'total_size': torrent.total_size,
            'num_pieces': torrent.num_pieces if hasattr(torrent, 'num_pieces') else 0,
            'piece_size': torrent.piece_size if hasattr(torrent, 'piece_size') else 0,
            'progress': torrent.progress,
            'num_peers': torrent.num_peers if hasattr(torrent, 'num_peers') else 0,
            'num_seeds': torrent.num_seeds if hasattr(torrent, 'num_seeds') else 0,
            'download_rate': torrent.dlspeed,
            'state': torrent.state,
            'error': torrent.error if hasattr(torrent, 'error') else '',
            'error_prog': torrent.error_prog if hasattr(torrent, 'error_prog') else ''
        }
    
    def set_piece_priorities(self, torrent_hash: str, num_pieces: int):
        """Set piece priorities to download first N pieces"""
        # qBittorrent uses file priorities, not piece priorities
        # For now, just start the download
        self.client.torrents_resume(torrent_hashes=torrent_hash)
    
    def remove_torrent(self, torrent_hash: str, delete_files: bool = False):
        """Remove torrent"""
        self.client.torrents_delete(
            delete_files=delete_files,
            torrent_hashes=torrent_hash
        )
    
    def pause_torrent(self, torrent_hash: str):
        """Pause torrent"""
        self.client.torrents_pause(torrent_hashes=torrent_hash)
    
    def resume_torrent(self, torrent_hash: str):
        """Resume torrent"""
        self.client.torrents_resume(torrent_hashes=torrent_hash)
    
    def get_piece_states(self, torrent_hash: str) -> list:
        """
        Get state of all pieces for a torrent
        Returns: List of integers (0=not downloaded, 1=downloading, 2=downloaded)
        """
        try:
            states = self.client.torrents_piece_states(torrent_hash=torrent_hash)
            return states if states else []
        except Exception as e:
            print(f"[WARN] Failed to get piece states: {e}")
            return []
    
    def get_piece_hashes(self, torrent_hash: str, num_pieces: int) -> list:
        """
        Get identifiers for pieces (qBittorrent doesn't expose SHA1 hashes)
        Returns: List of piece identifiers
        """
        try:
            return [f"piece_{i}_{torrent_hash[:8]}" for i in range(num_pieces)]
        except Exception as e:
            print(f"[WARN] Failed to generate piece hashes: {e}")
            return []
    
    def get_torrent_files(self, torrent_hash: str) -> list:
        """Get list of files in torrent"""
        try:
            return self.client.torrents_files(torrent_hash=torrent_hash)
        except Exception as e:
            print(f"[WARN] Failed to get torrent files: {e}")
            return []
    
    def get_download_path(self, torrent_hash: str) -> str:
        """
        Get full path to downloaded file(s)
        For single-file torrents: returns file path
        For multi-file torrents: returns directory path
        """
        try:
            info = self.get_torrent_info(torrent_hash)
            files = self.get_torrent_files(torrent_hash)
            
            if not files:
                return None
            
            save_path = info.get('save_path', '')
            
            # For single-file torrents
            if len(files) == 1:
                return os.path.join(save_path, files[0].name)
            
            # For multi-file torrents, return directory
            return save_path
        except Exception as e:
            print(f"[WARN] Failed to get download path: {e}")
            return None

# Create singleton instance
try:
    qb_client = QBittorrentClient()
    if qb_client.client:
        print(f"[OK] Connected to qBittorrent {qb_client.client.app.version}")
        QBITTORRENT_AVAILABLE = True
    else:
        print("[WARN] qBittorrent not available, will use mock")
        QBITTORRENT_AVAILABLE = False
except Exception as e:
    print(f"[ERR] Failed to connect to qBittorrent: {e}")
    qb_client = None
    QBITTORRENT_AVAILABLE = False
