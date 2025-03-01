import os
import psutil
import logging
import time
import threading
import sys
import gc

class MemoryMonitor:
    """监控内存使用情况并在必要时采取措施以避免内存溢出"""
    
    def __init__(self, warning_threshold=70, critical_threshold=85, check_interval=5):
        """初始化内存监控器
        
        Args:
            warning_threshold: 警告阈值（内存使用百分比）
            critical_threshold: 严重阈值（内存使用百分比）
            check_interval: 检查间隔（秒）
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.callbacks = {
            'warning': [],
            'critical': [],
            'normal': []
        }
        self.last_state = 'normal'
        self.peak_memory = 0
        
    def start(self):
        """开始内存监控"""
        if self.monitoring:
            logging.warning("内存监控已在运行")
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logging.info(f"内存监控已启动，警告阈值: {self.warning_threshold}%, 严重阈值: {self.critical_threshold}%")
        
    def stop(self):
        """停止内存监控"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
            
        logging.info(f"内存监控已停止，峰值内存使用率: {self.peak_memory:.1f}%")
        
    def _monitor_loop(self):
        """内存监控循环"""
        while self.monitoring:
            try:
                mem = psutil.virtual_memory()
                used_percent = mem.percent
                
                # 更新峰值内存
                if used_percent > self.peak_memory:
                    self.peak_memory = used_percent
                
                current_state = 'normal'
                if used_percent >= self.critical_threshold:
                    current_state = 'critical'
                elif used_percent >= self.warning_threshold:
                    current_state = 'warning'
                
                # 状态变化时触发回调
                if current_state != self.last_state:
                    logging.info(f"内存状态从 {self.last_state} 变为 {current_state} ({used_percent:.1f}%)")
                    
                    # 执行回调
                    for callback in self.callbacks.get(current_state, []):
                        try:
                            callback(used_percent)
                        except Exception as e:
                            logging.error(f"执行内存回调时出错: {e}")
                    
                    self.last_state = current_state
                    
                # 严重状态下主动进行垃圾回收
                if current_state == 'critical':
                    logging.warning(f"内存使用率严重: {used_percent:.1f}%，执行垃圾回收")
                    collected = gc.collect()
                    logging.info(f"垃圾回收完成，回收了 {collected} 个对象")
                    
            except Exception as e:
                logging.error(f"内存监控出错: {e}")
                
            time.sleep(self.check_interval)
    
    def add_callback(self, state, callback):
        """添加内存状态变化回调
        
        Args:
            state: 状态类型 ('normal', 'warning', 'critical')
            callback: 回调函数，接受一个参数（当前内存使用百分比）
        """
        if state in self.callbacks:
            self.callbacks[state].append(callback)
        else:
            logging.error(f"无效的状态类型: {state}")
            
    def get_memory_info(self):
        """获取当前内存使用信息
        
        Returns:
            内存信息字典
        """
        mem = psutil.virtual_memory()
        return {
            'percent': mem.percent,
            'used_gb': mem.used / (1024**3),
            'available_gb': mem.available / (1024**3),
            'total_gb': mem.total / (1024**3),
            'peak_percent': self.peak_memory
        }
    
    def print_memory_report(self):
        """打印内存使用报告"""
        info = self.get_memory_info()
        logging.info(f"内存报告: 使用率 {info['percent']:.1f}% ({info['used_gb']:.2f} GB / {info['total_gb']:.2f} GB), "
                   f"可用: {info['available_gb']:.2f} GB, 峰值使用率: {info['peak_percent']:.1f}%")
        
    @staticmethod
    def emergency_cleanup():
        """紧急清理内存"""
        logging.warning("执行紧急内存清理")
        import gc
        gc.collect()
        
        # 清除不必要的模块
        all_modules = list(sys.modules.keys())
        for module_name in all_modules:
            # 避免删除核心模块
            if (not module_name.startswith('_') and 
                not module_name in ('sys', 'os', 'gc', 'logging', 'psutil', 'threading', 'time')):
                try:
                    del sys.modules[module_name]
                except:
                    pass
                    
        # 强制Python执行完整的垃圾回收
        gc.collect(0)
        gc.collect(1)
        gc.collect(2)
        
        # 显示结果
        mem_after = psutil.virtual_memory().percent
        logging.info(f"紧急清理完成，当前内存使用率: {mem_after:.1f}%")
