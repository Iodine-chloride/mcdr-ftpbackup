import os
from mcdreforged.api.all import *
from .config import Config
from .ftp_manager import FTPManager
from .backup_util import BackupManager
from .server_controller import ServerController
from .sftp_manager import SFTPManager
from .backup_util import BackupAbortedException


class CommandHandler:
    def __init__(self, server: PluginServerInterface, config: Config,
                 ftp_manager: FTPManager, backup_manager: BackupManager,
                 server_controller: ServerController):
        self.server = server
        self.config = config
        self.ftp_manager = ftp_manager
        self.backup_manager = backup_manager
        self.server_controller = server_controller

    def register_commands(self):
        self.server.register_command(
            Literal(self.config.prefix)
                .runs(self.show_help)
                .then(Literal('test').runs(self.test_connection))
                .then(Literal('make').runs(self.make_backup))
                .then(Literal('inquire').runs(self.backup_manager.inquire_backup))
                .then(Literal('reload').runs(self.reload_config))
                .then(Literal('abort').runs(self.abort_backup))
            )

    def show_help(self, source: CommandSource):
        help_msg = RTextList(
            RText("=== FTP备份插件帮助 ===").set_color(RColor.gold), "\n",
            RText(f"{self.config.prefix}").set_color(RColor.blue) + " - 显示本帮助\n",
            RText(f"{self.config.prefix} test").set_color(RColor.blue) + " - 测试FTP连接\n",
            RText(f"{self.config.prefix} make").set_color(RColor.blue) + " - 创建并上传备份\n",
            RText(f"{self.config.prefix} inquire").set_color(RColor.blue) + " - 查询备份进度\n",
            RText(f"{self.config.prefix} reload").set_color(RColor.blue) + " - 热重载配置\n",
            RText(f"{self.config.prefix} abort").set_color(RColor.blue) + " - 终止进行中的备份\n"
        )
        source.reply(help_msg)

    def test_connection(self, source: CommandSource):
        if self.ftp_manager.connect(self.config):
            source.reply(RText("✓ 连接成功", color=RColor.green))
        else:
            source.reply(RText("✗ 连接失败", color=RColor.red))
        self.ftp_manager.disconnect()

    def make_backup(self, source: CommandSource):
        if not source.has_permission(self.config.required_permission):
            source.reply(RText("权限不足!", color=RColor.red))
            return

        if self.backup_manager.backup:
            source.reply(RText("§c已有备份任务在进行中", color=RColor.red))
            return

        source.reply(RText("§6正在准备备份，请稍候..."))
        self.__execute_make_backup(source)

    @new_thread
    def __execute_make_backup(self, source: CommandSource):
        def shutdown_callback():
            try:
                source.reply(RText("§6正在创建备份文件...", color=RColor.gold))
                backup_path = self.backup_manager.create_backup()

                if backup_path is None:
                    raise BackupAbortedException("用户终止备份")
                if not isinstance(backup_path, str):
                    raise ValueError("无效的备份路径")
                if self.config.stop_server:
                    source.reply(RText("§a备份文件创建完成，正在重启服务器...", color=RColor.green))
                    self.server_controller.restart_server()
                else:
                    source.reply(RText("§a备份文件创建完成", color=RColor.green))
                self.__upload_background(source, str(backup_path))
            except BackupAbortedException as e:
                self.server.logger.error("备份被用户终止")
                source.reply(RText("§c备份已终止", color=RColor.red))
                return
            except Exception as e:
                self.server.logger.error(f"备份流程错误: {str(e)}")
                source.reply(RText("§c备份流程出现异常", color=RColor.red))
            finally:
                if self.config.stop_server:
                    try:
                            self.server_controller.restart_server()
                            source.reply(RText("§a服务器已强制重启", color=RColor.green))
                    except Exception as e:
                        self.server.logger.critical(f"服务器重启失败: {str(e)}")
        if self.config.stop_server:
            self.server_controller.safe_shutdown(shutdown_callback)
        else:
            shutdown_callback()

    @new_thread
    def __upload_background(self, source: CommandSource, backup_path: str):
        try:
            if self.ftp_manager.connect(self.config):
                file_size = os.path.getsize(backup_path) / 1024 / 1024
                if self.ftp_manager.upload_file(backup_path, self.config):
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

        self.__do_upload(source, file_path)

    @new_thread
    def __do_upload(self, source: CommandSource, file_path: str):
        if self.ftp_manager.connect(self.config):
            try:
                if self.ftp_manager.upload_file(file_path, self.config):
                    source.reply(RText(f"§a已上传 {file_path}", color=RColor.green))
                else:
                    source.reply(RText("§c上传失败", color=RColor.red))
            finally:
                self.ftp_manager.disconnect()

    def reload_config(self, source: CommandSource):
        if not source.has_permission(self.config.required_permission):
            source.reply(RText("权限不足!", color=RColor.red))
            return

        try:
            # 断开当前连接
            self.ftp_manager.disconnect()

            # 重新加载配置
            new_config = self.server.load_config_simple(
                file_name='config.json',
                target_class=Config,
                default_config={'prefix': '!!fb'}
            )

            # 更新配置引用
            self.config = new_config
            self.__update_transfer_manager()
            self.backup_manager.update_config(new_config)

            source.reply(RText("§a配置已重载", color=RColor.green))
        except Exception as e:
            self.server.logger.error(f"配置重载失败: {str(e)}")
            source.reply(RText(f"§c配置重载失败: {str(e)}", color=RColor.red))

    def __update_transfer_manager(self):
        if self.config.protocol.lower() == 'sftp':
            self.ftp_manager = SFTPManager(self.server)
            self.server.logger.info("已选择SFTP协议")
        elif self.config.protocol.lower() == 'ftp':
            self.ftp_manager = FTPManager(self.server)
            self.server.logger.info("已选择FTP协议")
        else:
            self.ftp_manager = FTPManager(self.server)
            self.server.logger.error("未知的协议，已选择默认FTP协议")

    def abort_backup(self, source: CommandSource):
        if self.backup_manager.backup:
            self.backup_manager.abort_backup_process()
            source.reply(RText("§6已发送终止信号，正在停止备份...", color=RColor.gold))
        else:
            source.reply(RText("§c当前没有进行中的备份", color=RColor.red))