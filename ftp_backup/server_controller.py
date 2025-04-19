import time
from mcdreforged.api.all import *

class ServerController:
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.watcher_thread = None
        self.last_status = False

    def is_server_running(self) -> bool:
        current_status = self.server.is_server_running()
        if current_status != self.last_status:
            self.server.logger.debug(f"服务器状态变化: {self.last_status} -> {current_status}")
            self.last_status = current_status
        return current_status

    def safe_shutdown(self, callback: callable):
        @new_thread
        def watcher():
            try:
                if self.is_server_running():
                    self.server.logger.info("§6正在关闭服务器...")
                    self.server.stop()
                else:
                    self.server.logger.warning("§e服务器已处于关闭状态")

                check_interval = 0.1
                while self.is_server_running():
                    time.sleep(check_interval)
                    check_interval = min(check_interval * 1.2, 5)  # 指数退避

                self.server.logger.info("§a服务器关闭确认完成")
                callback()
            except Exception as e:
                self.server.logger.error(f"关闭过程出错: {str(e)}")

        watcher()

    def restart_server(self):
        if not self.is_server_running():
            self.server.start()
            self.server.logger.info("§a正在启动服务器...")
        else:
            self.server.logger.warning("§c服务器已在运行状态")