import threading
from typing import Callable
from mcdreforged.api.all import PluginServerInterface

class AsyncTaskManager:
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.tasks = []
        self.lock = threading.Lock()  # 添加线程锁

    def create_task(self, func: Callable, args: tuple = ()):
        def wrapper():
            try:
                func(*args)
            except Exception as e:
                self.server.logger.error(f"异步任务失败: {str(e)}")
            finally:
                with self.lock:
                    self.tasks.remove(threading.current_thread())

        thread = threading.Thread(target=wrapper, daemon=True)
        with self.lock:
            self.tasks.append(thread)
        thread.start()
        return thread

    def shutdown(self):
        with self.lock:
            for task in self.tasks:
                if task.is_alive():
                    task.join(timeout=5)
            self.tasks.clear()