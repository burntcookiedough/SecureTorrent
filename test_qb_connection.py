import qbittorrentapi

try:
    client = qbittorrentapi.Client(
        host='localhost',
        port=8080,
        username='admin',
        password='torrentguard2024'
    )
    client.auth_log_in()
    print('✅ Connection successful')
    print(f'qBittorrent version: {client.app.version}')
except Exception as e:
    print(f'❌ Connection failed: {e}')
