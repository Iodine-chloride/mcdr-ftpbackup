import os
import time
import zipfile
import fnmatch
from typing import Optional, Generator
from mcdreforged.api.all import PluginServerInterface
from .config import Config


class BackupManager:
    def __init__(self, server: PluginServerInterface, config: Config):
        self.server = server
        self.backup_dir = os.path.abspath(os.path.join('backups'))
        os.makedirs(self.backup_dir, exist_ok=True)
        self.config = self.__validate_config(config)
        self.__validate_backup_dir()
        self.backup = False
        self.total_files = None
        self.processed_files = 0

    def __validate_backup_dir(self):
        if not os.access(self.backup_dir, os.W_OK):
            raise PermissionError(f"备份目录不可写: {self.backup_dir}")
        if not os.path.isdir(self.backup_dir):
            raise NotADirectoryError(f"备份路径不是目录: {self.backup_dir}")

    def __validate_config(self, config: Config) -> Config:
        if not os.path.isabs(config.server_dir):
            config.server_dir = os.path.abspath(config.server_dir)
        if not os.path.exists(config.server_dir):
            raise ValueError(f"服务器目录不存在: {config.server_dir}")
        if not os.access(config.server_dir, os.R_OK):
            raise PermissionError(f"目录不可读: {config.server_dir}")
        return config

    def __should_include(self, path: str) -> bool:
        rel_path = os.path.relpath(path, self.config.server_dir)
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return False
            if fnmatch.fnmatch(rel_path, os.path.join(pattern, '*')):
                return False
        return True

    def __get_total_files(self) -> int:
        total = 0
        for root, dirs, files in os.walk(self.config.server_dir):
            dirs[:] = [d for d in dirs if self.__should_include(os.path.join(root, d))]
            total += len(files)
        return total

    def __walk_files(self) -> Generator[str, None, None]:
        for root, dirs, files in os.walk(self.config.server_dir):
            dirs[:] = [d for d in dirs if self.__should_include(os.path.join(root, d))]
            for file in files:
                full_path = os.path.join(root, file)
                if self.__should_include(full_path):
                    yield full_path

    def create_backup(self) -> Optional[str]:
        try:
            # 生成备份文件名和路径
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"backup_{timestamp}.zip"
            output_path = os.path.join(self.backup_dir, filename)

            # 确保备份目录存在
            if not os.path.isdir(self.backup_dir):
                os.makedirs(self.backup_dir, exist_ok=True)

            # 初始化备份参数
            self.total_files = self.__get_total_files()
            self.processed_files = 0
            start_time = time.time()

            # 创建 ZIP 压缩包
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                self.server.logger.info("§b开始压缩，共发现 {} 个文件".format(self.total_files))
                self.backup = True
                # 遍历并压缩文件
                for full_path in self.__walk_files():
                    arcname = os.path.relpath(full_path, self.config.server_dir)
                    zipf.write(full_path, arcname)
                    self.processed_files += 1

            # 完成提示
            cost_time = time.time() - start_time
            self.server.logger.info(f"\n§a压缩完成，耗时 {cost_time:.1f} 秒")
            self.server.logger.info(f"§a备份文件已保存至: §e{output_path}")

            return output_path
        except Exception as e:
            self.server.logger.error(f"\n§c压缩失败: {str(e)}")
            # 删除未完成的备份文件
            if os.path.exists(output_path):
                os.remove(output_path)
            return None
        finally:
            self.backup = False

    def cleanup_backups(self):
        backups = sorted(
            [f for f in os.listdir(self.backup_dir) if f.endswith('.zip')],
            key=lambda f: os.path.getctime(os.path.join(self.backup_dir, f)))
        while len(backups) > self.config.keep_local_backups:
            old_file = backups.pop(0)
            os.remove(os.path.join(self.backup_dir, old_file))
            self.server.logger.info(f"§6已清理旧备份: {old_file}")

    def inquire_backup(self):
        if self.backup:
            self.server.logger.info(f"§6总文件数：{self.total_files}")
            self.server.logger.info(f"§6已备份文件数：{self.processed_files}")
        else:
            self.server.logger.info("§6没有在进行的备份任务")
