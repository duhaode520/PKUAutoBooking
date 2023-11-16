from configparser import ConfigParser
import warnings
import multiprocessing as mp
from booker import Booker
from env_check import *
from page_func import *
from log import setup_logger

warnings.filterwarnings('ignore')

DEBUG_FLAG = true


def sequence_run(lst_conf):
    print("按序预约")
    for config in lst_conf:
        print("预约 %s" % config)
        task(config)


def multi_run(lst_conf, browser="chrome"):
    parameter_list = []
    for i in range(len(lst_conf)):
        parameter_list.append((lst_conf[i], browser))
    print("并行预约")
    pool = mp.Pool()
    pool.starmap_async(task, parameter_list)
    pool.close()
    pool.join()


def task(config_name:str, process_id=None):
    logger = setup_logger(config_name, process_id)
    booker = Booker(config_name, logger)
    booker.keep_run()


if __name__ == '__main__':
    lst_conf = env_check()
    print("本次使用的config文件:" + str(lst_conf))
    # multi_run(lst_conf, browser)
    sequence_run(lst_conf)
