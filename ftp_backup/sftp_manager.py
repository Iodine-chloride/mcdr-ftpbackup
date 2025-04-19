import os
import paramiko
from typing import Optional
from mcdreforged.api.all import PluginServerInterface


class SFTPManager:
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.transport: Optional[paramiko.Transport] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None

    def connect(self, config) -> bool:
        try:
            self.transport = paramiko.Transport((config.host, config.port))

            if config.private_key_path and os.path.exists(config.private_key_path):
                private_key = paramiko.RSAKey.from_private_key_file(config.private_key_path)
                self.transport.connect(username=config.username, pkey=private_key)
            else:
                self.transport.connect(username=config.username, password=config.password)

            self.sftp_client = paramiko.SFTPClient.from_transport(self.transport)
            self.server.logger.info("SFTP连接成功")
            return True
        except Exception as e:
            self.server.logger.error(f"SFTP连接失败: {str(e)}")
            self.disconnect()
            return False

    def upload_file(self, file_path: str) -> bool:
        if self.sftp_client is None:
            return False

        try:
            remote_filename = os.path.basename(file_path)
            remote_full_path = f'/{remote_filename}'  # 直接上传到根目录
            self.sftp_client.put(file_path, remote_full_path)
            self.server.logger.info(f"已通过SFTP上传 {file_path} 至根目录")
            return True
        except Exception as e:
            self.server.logger.error(f"SFTP上传失败: {str(e)}")
            return False

    def disconnect(self):
        if self.sftp_client:
            self.sftp_client.close()
        if self.transport:
            self.transport.close()
        self.sftp_client = None
        self.transport = None