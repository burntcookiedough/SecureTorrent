import os
import sys

# Paste the bdecode logic from mock_libtorrent.py
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

def parse_torrent(path):
    print(f"Parsing: {path}")
    with open(path, 'rb') as f:
        data = f.read()
        print(f"File size: {len(data)} bytes")
        meta = bdecode(data)
        info = meta.get('info', {})
        
        name = info.get('name', b'Unknown').decode('utf-8', errors='ignore')
        print(f"Name: {name}")
        
        if 'length' in info:
            print(f"Single file mode. Length: {info['length']} bytes ({info['length']/1024/1024:.2f} MB)")
        elif 'files' in info:
            print("Multi-file mode.")
            total = 0
            for f in info['files']:
                l = f.get('length', 0)
                total += l
                print(f"  - File length: {l}")
            print(f"Total length: {total} bytes ({total/1024/1024:.2f} MB)")
        
        piece_len = info.get('piece length', 0)
        print(f"Piece length: {piece_len}")
        
        pieces = info.get('pieces', b'')
        print(f"Pieces hash length: {len(pieces)}")
        print(f"Num pieces: {len(pieces) // 20}")

if __name__ == "__main__":
    # Check the file in tests/data
    path = r"c:\Users\anshu\Desktop\TorrentGuard\tests\data\tiny-iso-test_archive.torrent"
    if os.path.exists(path):
        parse_torrent(path)
    else:
        print("File not found")
