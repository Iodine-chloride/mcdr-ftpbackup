import ftplib
import socket
import chardet
import os
from typing import Optional
from mcdreforged.api.all import PluginServerInterface

class FTPManager:
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.ftp_client: Optional[ftplib.FTP] = None
        self.encoding = 'utf-8'

    def detect_encoding(self, host: str, port: int, timeout: int) -> str:
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                welcome_bytes = sock.recv(1024)
                result = chardet.detect(welcome_bytes)
                return result['encoding'] if result['confidence'] > 0.5 else 'latin-1'
        except Exception as e:
            self.server.logger.error(f"编码检测失败: {e}")
            return 'utf-8'

    def connect(self, config) -> bool:
        try:
            self.encoding = self.detect_encoding(config.host, config.port, config.timeout)
            self.ftp_client = ftplib.FTP()
            self.ftp_client.encoding = self.encoding
            self.ftp_client.connect(config.host, config.port, timeout=config.timeout)
            self.ftp_client.login(config.username, config.password)
            self.server.logger.info("FTP连接成功")
            return True
        except Exception as e:
            self.server.logger.error(f"连接失败: {str(e)}")
            return False

    def upload_file(self, file_path: str, config) -> bool:
        if self.ftp_client is None:
            return False

        try:
            remote_filename = os.path.basename(file_path)
            remote_path = f"{config.remote_path}/{remote_filename}".replace('//', '/')
            with open(file_path, 'rb') as f:
                self.ftp_client.storbinary(f'STOR {remote_path}', f)
            self.server.logger.info(f"已上传至 {remote_path}")
            return True
        except Exception as e:
            self.server.logger.error(f"上传失败: {str(e)}")
            return False

    def disconnect(self):
        if self.ftp_client:
            try:
                self.ftp_client.quit()
            except:
                self.ftp_client.close()
            self.ftp_client = None