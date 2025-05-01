from mcdreforged.api.all import *
from .config import Config
from .ftp_manager import FTPManager
from .sftp_manager import SFTPManager
from .commands import CommandHandler
from .backup_util import BackupManager
from .server_controller import ServerController

config: Config
transfer_manager: object
backup_manager: BackupManager
server_controller: ServerController
command_handler: CommandHandler


def on_load(server: PluginServerInterface, old_module):
    global config, transfer_manager, backup_manager, server_controller, command_handler

    try:
        def init_config():
            return server.load_config_simple(
                file_name='config.json',
                target_class=Config,
                default_config={'prefix': '!!fb'}
            )

        config = init_config()

        if config.protocol.lower() == 'sftp':
            transfer_manager = SFTPManager(server)
            server.logger.info("§6已选择SFTP协议")
        elif config.protocol.lower() == 'ftp':
            transfer_manager = FTPManager(server)
            server.logger.info("§6已选择FTP协议")
        else:
            transfer_manager = FTPManager(server)
            server.logger.error("未知的协议，已选择默认FTP协议")

        backup_manager = BackupManager(server, config)
        server_controller = ServerController(server)
        command_handler = CommandHandler(
            server,
            config,
            transfer_manager,
            backup_manager,
            server_controller
        )
        command_handler.register_commands()

        if config.auto_backup:
            command_handler.start_timed_tasks()


    except Exception as e:
        server.logger.critical(f"插件加载失败: {str(e)}")
        raise


def on_unload(server: PluginServerInterface):
    transfer_manager.disconnect()
    command_handler.shutdown_scheduler()