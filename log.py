import logging
import os
import datetime
import time


def setup_logger(config_path:str, process_id:int = None) -> logging.Logger:
    # 设置logger的name
    config_name = config_path.split('.')[0]
    logger_name = f"{config_name}_logger"
    if process_id:
        logger_name += f"_{process_id}"

    # 设置log输出的位置
    log_dir = './log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    now = datetime.datetime.now()
    fmt_time = now.strftime("%Y%m%d_%H_%M_%S")

    logfile_name = f"{logger_name}_{process_id}_{fmt_time}.log" if  process_id else f"{logger_name}_{fmt_time}.log"
    log_path = os.path.join(log_dir, logfile_name)
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # 创建文件处理器，将日志写入到log.txt文件中
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # 创建控制台处理器，将大于debug级别的日志输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建日志格式器
    formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s")

    # 将格式器添加到处理器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 将处理器添加到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 写入初始信息
    logger.info("Created at " + str(datetime.datetime.now()))

    return logger


if __name__ == "__main__":
    logger = setup_logger("test.ini")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")