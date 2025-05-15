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
    remote_path : str = '/'
    local_path: str = './backups'
    auto_backup: bool = False
    cron_expression: str = '0 0 * * *'
    saved_game_regex: str = r'Saved the game.*' #保存世界完成信息正则表达式