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

class QBittorrentClient:
    """Adapter to make qBittorrent API look like libtorrent"""
    
    def __init__(self):
        self.client = qbittorrentapi.Client(
            host=QBITTORRENT_HOST,
            port=QBITTORRENT_PORT,
            username=QBITTORRENT_USERNAME,
            password=QBITTORRENT_PASSWORD
        )
        try:
            self.client.auth_log_in()
            print(f"✅ Connected to qBittorrent {self.client.app.version}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to qBittorrent: {e}")
    
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
            'state': torrent.state
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

# Create singleton instance
try:
    qb_client = QBittorrentClient()
    QBITTORRENT_AVAILABLE = True
except Exception as e:
    print(f"⚠️ qBittorrent client initialization failed: {e}")
    qb_client = None
    QBITTORRENT_AVAILABLE = False
