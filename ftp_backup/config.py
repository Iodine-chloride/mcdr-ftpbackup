from mcdreforged.api.utils.serializer import Serializable

class Config(Serializable):
    stop_server: bool = True
    protocol: str = 'ftp'
    host: str = 'ftp.example.com'
    port: int = 21
    timeout: int = 10
    username: str = 'anonymous'
    private_key_path: str = ''
    password: str = ''
    prefix: str = '!!fb'
    server_dir: str = './server'
    keep_local_backups: int = 3
    required_permission: int = 3
    exclude_patterns: list = ["logs",
                              "*.tmp",
                              "*.lock"]