from mcdreforged.api.all import *
from .config import Config
from .ftp_manager import FTPManager
from .commands import CommandHandler
from .backup_util import BackupManager
from .server_controller import ServerController
from .async_task import AsyncTaskManager

config: Config
ftp_manager: FTPManager
backup_manager: BackupManager
server_controller: ServerController
command_handler: CommandHandler
task_manager: AsyncTaskManager

def on_load(server: PluginServerInterface, old_module):
    global config, ftp_manager, backup_manager, server_controller, command_handler, task_manager

    try:
        config = server.load_config_simple(
            file_name='config.json',
            target_class=Config,
            default_config={'prefix': '!!fb'}
        )

        ftp_manager = FTPManager(server)
        backup_manager = BackupManager(server, config)
        server_controller = ServerController(server)
        task_manager = AsyncTaskManager(server)

        command_handler = CommandHandler(server, config, ftp_manager, backup_manager, server_controller, task_manager)
        command_handler.register_commands()

        if ftp_manager.connect(config):
            server.logger.info("FTP连接初始化成功")
        else:
            server.logger.warning("FTP连接初始化失败")

    except Exception as e:
        server.logger.critical(f"插件加载失败: {str(e)}")
        raise

def on_unload(server: PluginServerInterface):
    ftp_manager.disconnect()
    task_manager.shutdown()