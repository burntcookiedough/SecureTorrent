from malware_detector import MalwareDetector
import traceback

try:
    print("🔬 Initializing MalwareDetector...")
    detector = MalwareDetector()
    
    # Simulate data from api_server.py
    # piece_data = {
    #     'src_bytes': self.info.piece_length(),
    #     'dst_bytes': 0,
    #     'peer_count': self.handle.status().num_peers if self.handle else 0,
    #     'seed_count': self.handle.status().num_seeds if self.handle else 0,
    #     'num_files': self.info.num_files()
    # }
    
    piece_data = {
        'src_bytes': 524288, # 512KB
        'dst_bytes': 0,
        'peer_count': 25,
        'seed_count': 5,
        'num_files': 1
    }
    
    print(f"📊 Testing prediction with data: {piece_data}")
    result = detector.predict(piece_data)
    print(f"✅ Prediction successful: {result}")

except Exception as e:
    print(f"❌ Prediction failed: {e}")
    traceback.print_exc()
