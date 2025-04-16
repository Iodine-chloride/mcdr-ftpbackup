import os
from mcdreforged.api.all import *
from .config import Config
from .ftp_manager import FTPManager
from .backup_util import BackupManager
from .server_controller import ServerController
from .async_task import AsyncTaskManager


class CommandHandler:
    def __init__(self, server: PluginServerInterface, config: Config,
                 ftp_manager: FTPManager, backup_manager: BackupManager,
                 server_controller: ServerController, task_manager: AsyncTaskManager):
        self.server = server
        self.config = config
        self.ftp_manager = ftp_manager
        self.backup_manager = backup_manager
        self.server_controller = server_controller
        self.task_manager = task_manager

    def register_commands(self):
        self.server.register_command(
            Literal(self.config.prefix)
                .then(Literal('help').runs(self.show_help))
                .then(Literal('test').runs(self.test_connection))
                .then(Literal('make').runs(self.safe_backup))
                .then(Literal('inquire').runs(self.backup_manager.inquire_backup))
            )

    def show_help(self, source: CommandSource):
        help_msg = RTextList(
            RText("=== FTP备份插件帮助 ===").set_color(RColor.gold), "\n",
            RText(f"{self.config.prefix} help").set_color(RColor.blue) + " - 显示帮助\n",
            RText(f"{self.config.prefix} test").set_color(RColor.blue) + " - 测试FTP连接\n",
            RText(f"{self.config.prefix} make").set_color(RColor.blue) + " - 创建并上传备份\n",
            RText(f"{self.config.prefix} inquire").set_color(RColor.blue) + " - 查询备份进度\n",
            RText(f"所需权限等级: {self.config.required_permission}").set_color(RColor.gray)
        )
        source.reply(help_msg)

    def test_connection(self, source: CommandSource):
        if self.ftp_manager.connect(self.config):
            source.reply(RText("✓ 连接成功", color=RColor.green))
        else:
            source.reply(RText("✗ 连接失败", color=RColor.red))
        self.ftp_manager.disconnect()

    def safe_backup(self, source: CommandSource):
        if not source.has_permission(self.config.required_permission):
            source.reply(RText("权限不足!", color=RColor.red))
            return

        if self.server_controller.watcher_thread and self.server_controller.watcher_thread.is_alive():
            source.reply(RText("§c已有备份任务在进行中", color=RColor.red))
            return

        source.reply(RText("§6正在准备备份，请稍候..."))
        self.task_manager.create_task(self.__execute_safe_backup, (source,))

    def __execute_safe_backup(self, source: CommandSource):
        def shutdown_callback():
            try:
                source.reply(RText("§6正在创建备份文件...", color=RColor.gold))
                backup_path = self.backup_manager.create_backup()

                if backup_path is None or not isinstance(backup_path, str):
                    raise ValueError("无效的备份路径")

                source.reply(RText("§a备份文件创建完成，正在重启服务器...", color=RColor.green))
                self.server_controller.restart_server()

                self.task_manager.create_task(
                    self.__upload_background,
                    (source, str(backup_path))
                )
            except Exception as e:
                self.server.logger.error(f"备份流程错误: {str(e)}")
                source.reply(RText("§c备份流程出现异常", color=RColor.red))

        self.server_controller.safe_shutdown(shutdown_callback)

    def __upload_background(self, source: CommandSource, backup_path: str):
        try:
            if self.ftp_manager.connect(self.config):
                file_size = os.path.getsize(backup_path) / 1024 / 1024
                if self.ftp_manager.upload_file(backup_path):
                    source.reply(
                        RTextList(
                            RText("§a备份上传成功！", color=RColor.green),
                            RText(f"\n文件名: §e{os.path.basename(backup_path)}"),
                            RText(f"\n大小: §e{file_size:.2f} MB"),
                            RText(f"\n路径: §e{backup_path}")
                        )
                    )
                else:
                    source.reply(RText("§c备份上传失败，请检查日志", color=RColor.red))
        except Exception as e:
            self.server.logger.error(f"上传错误: {str(e)}")
            source.reply(RText("§c上传过程中发生意外错误", color=RColor.red))
        finally:
            self.ftp_manager.disconnect()
            self.backup_manager.cleanup_backups()

    def upload_file(self, source: CommandSource, ctx: dict):
        file_path = ctx['file_path']
        if not source.has_permission(self.config.required_permission):
            source.reply(RText("权限不足!", color=RColor.red))
            return

        self.task_manager.create_task(self.__do_upload, (source, file_path))

    def __do_upload(self, source: CommandSource, file_path: str):
        if self.ftp_manager.connect(self.config):
            try:
                if self.ftp_manager.upload_file(file_path):
                    source.reply(RText(f"§a已上传 {file_path}", color=RColor.green))
                else:
                    source.reply(RText("§c上传失败", color=RColor.red))
            finally:
                self.ftp_manager.disconnect()