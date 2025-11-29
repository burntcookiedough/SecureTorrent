# Mock libtorrent for development/testing when the real library is hard to install
import time
import threading
import random

class session:
    def __init__(self):
        self.settings = {}
        print("⚠️ USING MOCK LIBTORRENT SESSION")

    def get_settings(self):
        return self.settings

    def apply_settings(self, settings):
        self.settings.update(settings)

    def add_dht_router(self, router, port):
        pass

    def start_dht(self):
        pass

    def add_torrent(self, params):
        return torrent_handle(params)

    def remove_torrent(self, handle):
        pass

import os

# Simple bencode parser for the mock
def bdecode(data):
    def decode_func(data, index):
        if index >= len(data):
            return None, index
        char = chr(data[index])
        if char == 'i':
            index += 1
            end = data.index(b'e', index)
            return int(data[index:end]), end + 1
        elif char == 'l':
            index += 1
            lst = []
            while chr(data[index]) != 'e':
                val, index = decode_func(data, index)
                lst.append(val)
            return lst, index + 1
        elif char == 'd':
            index += 1
            dct = {}
            while chr(data[index]) != 'e':
                key, index = decode_func(data, index)
                val, index = decode_func(data, index)
                dct[key.decode('utf-8', errors='ignore')] = val
            return dct, index + 1
        elif char.isdigit():
            colon = data.index(b':', index)
            length = int(data[index:colon])
            start = colon + 1
            end = start + length
            return data[start:end], end
        return None, index

    try:
        res, _ = decode_func(data, 0)
        return res
    except:
        return {}

class torrent_info:
    def __init__(self, path):
        self.path = path
        self._name = "Unknown"
        self._total_size = 0
        self._num_pieces = 0
        self._piece_length = 0
        
        try:
            with open(path, 'rb') as f:
                data = f.read()
                meta = bdecode(data)
                info = meta.get('info', {})
                
                self._name = info.get('name', b'Unknown').decode('utf-8', errors='ignore')
                self._piece_length = info.get('piece length', 0)
                
                pieces = info.get('pieces', b'')
                self._num_pieces = len(pieces) // 20
                
                if 'length' in info:
                    self._total_size = info['length']
                elif 'files' in info:
                    self._total_size = sum(f.get('length', 0) for f in info['files'])
                    
        except Exception as e:
            print(f"⚠️ Failed to parse torrent file: {e}")
            # Fallback to dummy values if parsing fails
            self._name = "Mock Torrent File (Parse Error)"
            self._total_size = 1024 * 1024 * 500
            self._num_pieces = 100
            self._piece_length = 1024 * 1024 * 5

    def name(self):
        return self._name

    def total_size(self):
        return self._total_size

    def num_pieces(self):
        return self._num_pieces

    def piece_length(self):
        return self._piece_length

    def hash_for_piece(self, index):
        return f"hash_{index}"
    
    def num_files(self):
        return 1

class torrent_handle:
    def __init__(self, params):
        self.params = params
        self._status = torrent_status()
        self._downloaded_pieces = set()
        self._total_pieces = 100 # Match torrent_info default

    def prioritize_pieces(self, priorities):
        pass

    def status(self):
        # Simulate progress
        if self._status.state < 4: # downloading
             self._status.state = 3
        
        # Simulate download progress
        if self._status.progress < 1.0:
            self._status.progress += 0.05
            self._status.download_rate = random.randint(1000000, 5000000)
            
            # Simulate pieces completing based on progress
            # 100 pieces total, progress 0.0-1.0
            # Mark pieces as downloaded up to current progress
            num_to_have = int(self._status.progress * self._total_pieces)
            for i in range(num_to_have):
                self._downloaded_pieces.add(i)
        
        if self._status.progress >= 1.0:
            self._status.state = 5 # seeding
            self._status.is_seeding = True
            
            # Create a dummy file to satisfy the user
            try:
                save_path = self.params.get('save_path', '.')
                name = self.params['ti'].name()
                file_path = os.path.join(save_path, name)
                
                if not os.path.exists(file_path):
                    with open(file_path, 'wb') as f:
                        f.write(b'MOCK_DOWNLOAD_CONTENT' * 100)
                    print(f"📝 Created dummy file at: {file_path}")
            except Exception as e:
                print(f"⚠️ Failed to create dummy file: {e}")

        return self._status

    def have_piece(self, index):
        return index in self._downloaded_pieces

class torrent_status:
    def __init__(self):
        self.state = 0
        self.progress = 0.0
        self.download_rate = 0
        self.upload_rate = 0
        self.num_peers = random.randint(5, 50)
        self.num_seeds = random.randint(1, 10)
        self.is_seeding = False
        self.has_metadata = True

class storage_mode_t:
    storage_mode_sparse = 1
