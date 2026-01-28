import logging
from logging.handlers import RotatingFileHandler


def get_logger(filename='auto_login.log'):
    # 创建RotatingFileHandler
    handler = RotatingFileHandler(
        filename=filename,  # 日志文件名
        maxBytes=10000,             # 单个文件最大字节数（10KB）
        backupCount=10              # 保留的备份文件数量
    )
    # 配置日志
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # 添加到logger
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
