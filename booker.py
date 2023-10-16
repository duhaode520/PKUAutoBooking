import logging
import random
from configparser import ConfigParser
import sys
import os
from os import stat
import warnings
import time
from functools import wraps
import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as Chrome_Options
from selenium.webdriver.edge.options import Options as Edge_Options
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


from utils import verify, get_size, check_element_exist, wait_loading_complete
from log import setup_logger
from notice import wechat_push
warnings.filterwarnings('ignore')


class Booker:

    def __init__(self, config_path: str, logger: logging.Logger, browser_name: str) -> None:
        self.config_path = config_path
        self.logger = logger
        self.browser_name = browser_name

        # 爬虫状态
        self.status = True

        # 场地锁定状态
        self.court_locked = False

        # 读取配置文件
        self.__load_config(config_path)

        # 预约场地的时间列表
        self.venue_time_list = []

    def __load_config(self, config_path: str) -> None:
        conf = ConfigParser()
        conf.read(config_path, encoding='utf8')

        self.user_name = conf['login']['user_name']
        self.password = conf['login']['password']
        self.tt_usr = conf['tt']['tt_usr']
        self.tt_pwd = conf['tt']['tt_pwd']
        self.venue = conf['type']['venue']
        self.venue_num = int(conf['type']['venue_num'])
        self.start_time = conf['time']['start_time']
        self.end_time = conf['time']['end_time']
        self.wechat_notice = conf.getboolean('wechat', 'wechat_notice')
        self.sckey = conf['wechat']['SCKEY']

    def book(self) -> None:
        self.status = True
        start_time_list, end_time_list, delta_day_list = self.__judge_exceeds_days_limit(
            self.start_time, self.end_time)

        # 如果没有有效的预约日期, 则退出
        if len(start_time_list) == 0:
            self.logger.warn("没有可用的预约日期")
            self.status = False
            return

        # 初始化浏览器
        self.__driver_init()

        # 登录
        self.__login()

        # 进入预约界面
        self.__go_to_venue_page()

        # 查找空闲场地
        self.__find_available_court(
            start_time_list, end_time_list, delta_day_list)

        # 确认预约
        self.__confirm_booking()

        # 提交订单
        self.__submit_order()

        # 完成验证码
        self.__complete_captcha()

        # 微信推送
        if self.wechat_notice and self.status:
            self.__push_court_locking_info()

        # 付款
        self.__pay()

        if self.status:
            self.logger.info("预约成功")
            if self.wechat_notice:
                wechat_push(self.sckey, '预定成功', '锁定的场地已成功自动付款', self.logger)

    def keep_run(self):
        retry_times = 0
        self.book()
        while not self.court_locked:
            retry_times += 1
            self.logger.info("第 %d 次整体重试" % retry_times)
            self.book()
            
        if self.court_locked and (not self.status):
            self.logger.warn("场地已锁定，但是预约付款失败")

    def __judge_exceeds_days_limit(self, start_time: str, end_time: str) -> tuple:
        """判断预约日期是否超过3天

        Args:
            start_time (`str`): 场地开始时间

            end_time (`str`): 场地结束时间

        Returns:
            tuple: 可用的时间列表

            (start_time_list_valid, end_time_list_valid, delta_day_list_valid): `list`, `list`, `list`

            start_time_list_valid: 可用的开始时间列表

            end_time_list_valid: 可用的结束时间列表

            delta_day_list_valid: 可用的距今天数列表
        """
        start_time_list = start_time.split('/')
        end_time_list = end_time.split('/')
        self.logger.info("start_time_list: %s" % start_time_list)
        self.logger.info("end_time_list: %s" % end_time_list)

        # 获取当前时间
        now = datetime.datetime.today()
        today = datetime.datetime.strptime(str(now)[:10], "%Y-%m-%d")

        # 当前时间的小时
        time_hour = datetime.datetime.strptime(
            str(now).split()[1][:-7], "%H:%M:%S")
        # 11:55 的时间戳
        time_11_55 = datetime.datetime.strptime(
            "11:55:00", "%H:%M:%S")

        start_time_list_valid = []
        end_time_list_valid = []
        delta_day_list_valid = []

        for i in range(len(start_time_list)):
            start_time = start_time_list[i]
            end_time = end_time_list[i]

            if len(start_time) > 8:
                # 支持 20230909-1500 这种格式
                date = datetime.datetime.strptime(
                    start_time.split('-')[0], "%Y%m%d")
                delta_day = (date-today).days
            else:
                # 正常情况下是 5-1500 这种格式
                delta_day = (int(start_time[0])+6-today.weekday()) % 7
                date = today+datetime.timedelta(days=delta_day)

            if delta_day > 3 or (delta_day == 3 and (time_hour < time_11_55)):
                self.logger.warn("预定日期: %s 无效" % str(date).split()[0])
                self.logger.warn("只能在当天中午11:55后预约未来3天以内的场馆")
                break
            else:
                start_time_list_valid.append(start_time)
                end_time_list_valid.append(end_time)
                delta_day_list_valid.append(delta_day)
                self.logger.info("预定日期: %s 有效" % str(date).split()[0])
                self.logger.info("在预约可预约日期范围内")

        return start_time_list_valid, end_time_list_valid, delta_day_list_valid

    def __driver_init(self) -> None:
        """初始化浏览器
        """

        def get_driver_path(browser: str) -> str:
            """获取驱动路径"""
            path = 'driver'
            if browser == "chrome":
                if sys.platform.startswith('win'):
                    return os.path.join(path, 'chromedriver.exe')
                elif sys.platform.startswith('linux'):
                    return os.path.join(path, 'chromedriver.bin')
                else:
                    raise Exception('不支持该系统')
            elif browser == "firefox":
                if sys.platform.startswith('win'):
                    return os.path.join(path, 'geckodriver.exe')
                elif sys.platform.startswith('linux'):
                    return os.path.join(path, 'geckodriver.bin')
                else:
                    raise Exception('不支持该系统')
            elif browser == "edge":
                if sys.platform.startswith('win'):
                    return os.path.join(path, 'msedgedriver.exe')
                elif sys.platform.startswith('linux'):
                    return os.path.join(path, 'msedgedriver.bin')
                else:
                    raise Exception('不支持该系统')
            else:
                raise Exception('不支持该浏览器')

        if self.browser_name == "chrome":
            chrome_options = Chrome_Options()
            chrome_options.add_argument("--headless")
            # 下面这两个option 用来解决 ssl error code 1, net_error -101 问题
            chrome_options.add_argument('-ignore-certificate-errors')
            chrome_options.add_argument('-ignore -ssl-errors')
            self.driver = webdriver.Chrome(
                options=chrome_options,
                executable_path=get_driver_path(browser="chrome"))

            self.logger.info('Chrome launched\n')
        elif self.browser_name == "firefox":
            firefox_options = Firefox_Options()
            firefox_options.add_argument("--headless")
            self.driver = webdriver.Firefox(
                options=firefox_options,
                executable_path=get_driver_path(browser="firefox"))
            self.logger.info('Firefox launched\n')
        elif self.browser_name == 'edge':
            edge_options = Edge_Options()
            edge_options.add_argument("--headless")
            self.driver = webdriver.Edge(
                executable_path=get_driver_path(browser="edge"))
            self.logger.info('Edge launched\n')
        else:
            raise Exception("不支持此类浏览器")

    def stage(stage_name):
        def decorate(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                if not self.status:
                    return
                try:
                    self.logger.info("开始执行 %s" % stage_name)
                    func(self, *args, **kwargs)
                    self.logger.info("执行 %s 完成" % stage_name)
                except Exception as e:
                    self.logger.error("执行 %s 失败" % stage_name)
                    self.logger.error(e)
                    self.logger.debug(e, exc_info=True, stack_info=True)
                    self.status = False
            return wrapper
        return decorate

    @stage(stage_name="登录")
    def __login(self, max_retry: int = 3) -> None:
        """登录

        Args:
            max_retry (int, optional): 最大重试次数. Defaults to 3.
        """

        portalURL = "https://portal.pku.edu.cn/portal2017"
        for i in range(max_retry):
            try:
                self.driver.get(portalURL)
                time.sleep(1)
                # 等待界面出现
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "div")))

                self.driver.find_element(By.CLASS_NAME, 'mainWrap02'
                                         ).find_element(By.PARTIAL_LINK_TEXT, '请登录'
                                                        ).click()

                # 跳转到登陆界面
                self.logger.info("门户登陆中...")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "user_name")))
                # 所有的 time.sleep都是防止被识别，这里多留一点时间sleep也没什么影响，这里应该是在抢票时间到之前就已经登录好了
                self.driver.find_element(
                    By.ID, "user_name").send_keys(self.user_name)
                time.sleep(0.5)
                self.driver.find_element(
                    By.ID, "password").send_keys(self.password)
                time.sleep(0.5)
                self.driver.find_element(By.ID, "logon_button").click()

                # 检测有没有加载到下一个页面，这里检测门户对应的表格和'全部'按钮
                WebDriverWait(self.driver,
                              10).until(EC.visibility_of_element_located((By.CLASS_NAME, 'no-border-table')))
                WebDriverWait(self.driver,
                              10).until(EC.visibility_of_element_located((By.ID, 'all')))

                # 检测有没有弹窗
                # 疫情防控期间的弹窗逻辑，现在好像没有这个了，或许 deprecated
                if check_element_exist(self.driver, By.XPATH, '/html/body/div[1]/div[5]/div/div/div[1]/div/div/table'):
                    # 这里随便点一下消除弹窗
                    ActionChains(self.driver)\
                        .move_to_element(self.driver.find_element(By.XPATH, "/html/body/div[1]/header/section/section[2]/section[1]"))\
                        .click()\
                        .perform()

                time.sleep(0.2)
                self.logger.info("门户登录成功")
                break
            except Exception as e:
                self.logger.info(f'Retrying {i+1} / {max_retry}.')
                self.logger.debug(e)
                self.logger.debug(e, exc_info=True, stack_info=True)

    @stage(stage_name="进入预约界面")
    def __go_to_venue_page(self, max_retry: int = 3) -> None:
        for i in range(max_retry):
            try:
                self.logger.info("进入预约界面...")

                # 点击全部按钮，显示出智慧场馆按钮
                butt_all = self.driver.find_element(By.ID, 'all')
                self.driver.execute_script('arguments[0].click();', butt_all)

                wait_loading_complete(self.driver, (By.ID, 'venues'))
                time.sleep(0.5)

                # 点击智慧场馆按钮
                self.driver.find_element(By.ID, 'venues').click()
                # 打开智慧场馆会新跳出一个界面，通过判断窗口数量来判断是否打开了新界面
                while len(self.driver.window_handles) < 2:
                    time.sleep(0.5)
                self.driver.switch_to.window(self.driver.window_handles[-1])

                # 这个 funModuleItem 应该是场馆预定页面独有的，用来判断是否进入了场馆预定页面
                wait_loading_complete(
                    self.driver, (By.CLASS_NAME, 'funModule'))

                # 找到场地预约按钮并点击
                items = self.driver.find_element(By.CLASS_NAME, 'funModule').find_elements(
                    By.CLASS_NAME, 'funModuleItem')
                for item in items:
                    if '场地预约' in item.text:
                        item.click()
                        break

                # '//div [contains(text(),\'%s\')]' 这个是对应羽毛球场/羽毛球馆的按钮的xpath
                wait_loading_complete(
                    self.driver, (By.XPATH, '//div [contains(text(),\'%s\')]' % self.venue))
                time.sleep(0.5)
                self.driver.find_element(
                    By.XPATH, '//div [contains(text(),\'%s\')]' % self.venue).click()
                wait_loading_complete(
                    self.driver, (By.CLASS_NAME, 'ivu-form-item-content'))

                self.logger.info("进入预约界面成功")
                # TODO: 这里要加一个判断有没有载入成功的逻辑
                break
            except Exception as e:
                self.logger.info(f'Retrying {i+1} / {max_retry}.')
                self.logger.debug(e)
                self.logger.debug(e, exc_info=True, stack_info=True)

    @stage(stage_name="查找空闲场地")
    def __find_available_court(self, start_time_list: list, end_time_list: list, delta_day_list: list) -> None:
        """自旋查找空闲场地

        Args:
            start_time_list (`list`): 开始日期列表
            end_time_list (`list`): 结束日期列表
            delta_day_list (`list`): 距离今天的天数列表
        """
        is_find = False
        times = 0
        while not is_find:
            times += 1
            self.logger.info("查找空闲场地, 第 %d 次尝试" % times)
            is_find = self.__find_available_court_single(
                start_time_list, end_time_list, delta_day_list)
            time.sleep(2 + random.random())  # 防止封号

    def __find_available_court_single(self, start_time_list: list, end_time_list: list, delta_day_list: list) -> bool:
        """ 完成单趟的查找空闲场地 """
        self.driver.switch_to.window(self.driver.window_handles[-1])
        wait_loading_complete(self.driver)

        is_find = False
        for k in range(len(start_time_list)):
            self.driver.refresh()
            wait_loading_complete(self.driver)
            start_time = start_time_list[k]
            end_time = end_time_list[k]
            delta_day = delta_day_list[k]
            # 若接近但是没到12点，停留在此页面
            if delta_day == 3:
                self.__spin_wait_until_12()

            # 移动到对应的日期
            self.__move_to_date(delta_day)

            start_hour = datetime.datetime.strptime(
                start_time.split('-')[1], "%H%M")
            end_hour = datetime.datetime.strptime(
                end_time.split('-')[1], "%H%M")
            day = datetime.datetime.today() + datetime.timedelta(days=delta_day)
            start_time = datetime.datetime(
                day.year, day.month, day.day, start_hour.hour, start_hour.minute)
            end_time = datetime.datetime(
                day.year, day.month, day.day, end_hour.hour, end_hour.minute)

            self.logger.info("场地开始时间: %s -- 结束时间: %s" % (start_time, end_time))

            table_num = 0
            is_find = False
            while not is_find:
                is_find = self.__click_available_court(
                    start_hour, end_hour, delta_day, table_num)
                table_num += 1

                # 找有没有下一个表
                table_div = self.driver.find_element(
                    By.CLASS_NAME, 'tableWrap')
                forward_arrow = table_div.find_elements(
                    By.CLASS_NAME, 'ivu-icon-ios-arrow-forward')
                if forward_arrow:
                    forward_arrow[0].click()
                else:
                    break
            if is_find:
                self.logger.info("找到空闲场地")
                break
            else:
                self.logger.info("未找到空闲场地")
        return is_find

    def __spin_wait_until_12(self) -> None:
        """循环等待到12点 """
        # 等待到12点
        self.logger.info("抢场时间未到，等待中...")
        while True:
            now = datetime.datetime.now()
            if now.hour == 12:
                break
            else:
                time.sleep(0.5)

    def __move_to_date(self, delta_day: int) -> None:
        """移动表格页面到对应的日期"""
        for i in range(delta_day):
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'ivu-form-item-content')))
            head = self.driver.find_element(
                By.CLASS_NAME, 'ivu-form-item-content')
            btn = head.find_elements(By.CLASS_NAME, 'ivu-btn')
            # btn0是向前的按钮，btn1是向后的按钮
            btn[1].click()
            time.sleep(0.1)

    def __click_available_court(self, start_time: datetime.datetime, end_time: datetime.datetime, delta_day: int, table_num: int) -> bool:
        """点击空闲场地

        Args:
            start_time (`datetime`): 场地开始时间 

            end_time (`datetime`): 场地结束时间 

            delta_day (`int`): 距离今天的天数

            table_num (`int`): 表格编号

        Returns:
            bool: 是否找到空闲场地
        """

        def judge_in_time_range(start_time: datetime.datetime, end_time: datetime.datetime, venue_time_range: str) -> bool:
            vt = venue_time_range.split('-')
            vt_start_time = datetime.datetime.strptime(vt[0], "%H:%M")
            vt_end_time = datetime.datetime.strptime(vt[1], "%H:%M")
            if start_time <= vt_start_time and vt_end_time <= end_time:
                return True
            else:
                return False

        def check_if_court_available(available_rows_list: list, col_index: int) -> bool:
            """检查场地是否可用
            """
            for tr in available_rows_list:
                cell_classes = tr[col_index].find_element(
                    By.TAG_NAME, 'div').get_attribute('class')
                if 'free' in cell_classes.split():
                    return True
            return False

        # 找到对应的表格
        rows = self.__get_table_rows(delta_day)
        # 筛选有效行
        valid_rows_list = []
        venue_time_list = []
        for i in range(1, len(rows) - 2):
            venue_time = rows[i].find_elements(By.TAG_NAME,
                                               'td')[0].find_element(By.TAG_NAME, 'div').text
            if judge_in_time_range(start_time, end_time, venue_time):
                valid_rows_list.append(
                    rows[i].find_elements(By.TAG_NAME, 'td'))
                venue_time_list.append(venue_time)
        if len(valid_rows_list) == 0:
            return False

        # 筛选有效场地
        col_index_list = [x for x in range(1, len(valid_rows_list[0]))]
        has_checked_num = table_num * 5
        self.logger.debug("当前场地号: %d" % self.venue_num)
        self.logger.debug("当前表格号: %d" % table_num)
        self.logger.debug("当前表格中场地号: %s" %
                          [x + has_checked_num for x in col_index_list])

        if self.venue_num != -1:
            # 如果指定了场地号，就只检查指定的场地号
            if self.venue_num - has_checked_num in col_index_list:
                is_available = check_if_court_available(
                    valid_rows_list, self.venue_num - has_checked_num)
            else:
                return False
        else:
            # shuffle一下index_list，防止每次都点第一列
            random.shuffle(col_index_list)
            self.logger.debug("随机后当前表格中场地号: %s" %
                              [x + has_checked_num for x in col_index_list])
            for col_index in col_index_list:
                is_available = check_if_court_available(
                    valid_rows_list, col_index)
                if is_available:
                    self.venue_num = col_index + has_checked_num  # 更新场地号
                    break
        if is_available:
            for i in range(len(valid_rows_list)):
                cell = valid_rows_list[i][col_index].find_element(
                    By.TAG_NAME, 'div')
                if 'free' in cell.get_attribute('class').split():
                    cell.click()
                    self.venue_time_list.append(venue_time_list[i])
            return True
        return False

    def __get_table_rows(self, delta_day) -> list:
        """ 获取预定场地表的行

        这里使用delta_day是为了防止表格加载不出来, 实在加载不出来就重新move一下
        """
        rows = self.driver.find_elements(By.TAG_NAME, 'tr')
        # 如果表格没有加载出来，就刷新一下
        no_table_count = 0
        while rows[1].find_elements(By.TAG_NAME,
                                    'td')[0].find_element(By.TAG_NAME, 'div').text == "时间段":
            no_table_count += 1
            time.sleep(0.2)
            rows = self.driver.find_elements(By.TAG_NAME, 'tr')
            if no_table_count > 10:
                self.driver.refresh()
                no_table_count = 0
                self.move_to_date(delta_day)
        return rows

    @stage(stage_name="确认预约")
    def __confirm_booking(self) -> None:
        """确认预定
        """
        self.driver.switch_to.window(self.driver.window_handles[-1])

        # 同意预约须知
        self.logger.info("同意预约须知")
        wait_loading_complete(
            self.driver, (By.CLASS_NAME, 'ivu-checkbox-wrapper'))
        self.driver.find_element(By.CLASS_NAME, 'ivu-checkbox-wrapper').click()

        # 点击'我要预约'
        self.logger.info("点击'我要预约'")
        wait_loading_complete(self.driver, (By.CLASS_NAME, 'payHandle'))
        payBtns = self.driver.find_element(
            By.CLASS_NAME, 'reservationStep1').find_elements(By.CLASS_NAME, 'payHandleItem')
        payBtns[1].click()

    @stage(stage_name="提交订单")
    def __submit_order(self) -> None:
        self.driver.switch_to.window(self.driver.window_handles[-1])
        # 点击提交订单按钮
        wait_loading_complete(self.driver, (By.CLASS_NAME, 'payHandleItem'))
        submitBtns = self.driver.find_element(
            By.CLASS_NAME, 'reservation-step-two').find_elements(By.CLASS_NAME, 'payHandleItem')
        submitBtns[1].click()

    @stage(stage_name="填写验证码")
    def __complete_captcha(self, max_retry=3) -> None:
        wait_loading_complete(self.driver, (By.CLASS_NAME, 'verify-img-out'))
        for i in range(max_retry):
            # 得到验证图片的base64
            base_img_element = self.driver.find_element(
                By.CLASS_NAME, 'verify-img-out').find_element(By.TAG_NAME, 'img')
            base_img = base_img_element.get_attribute(
                'src').replace('data:image/png;base64,', '')
            # 计算图片的缩放情况
            real_img_size = get_size(base_img)
            scale = (base_img_element.size['width'] / real_img_size[0],
                     base_img_element.size['height'] / real_img_size[1])

            # 得到点击的内容
            verify_msg_element = self.driver.find_element(
                By.CLASS_NAME, 'verify-msg')
            verify_msg = verify_msg_element.text.replace(',', '')
            content = verify_msg[verify_msg.find('【')+1:verify_msg.find('】')]

            try:
                points = verify(base_img, content, self.tt_usr, self.tt_pwd)
                action = ActionChains(self.driver)
                for point in points:
                    # 这里需要先移入中心，再移入左上角，再移入目标点，不然会出现偏移
                    action.move_to_element(base_img_element).move_by_offset(
                        -base_img_element.size['width']/2, -
                        base_img_element.size['height']/2
                    ).move_by_offset(
                        point[0]*scale[0], point[1]*scale[1]).click().perform()
                wait_loading_complete(
                    self.driver, (By.CLASS_NAME, 'payMent'), wait_seconds=3)
                if check_element_exist(self.driver, By.CLASS_NAME, 'payMent'):
                    self.court_locked = True
                    break
            except Exception as e:
                if i == max_retry - 1:
                    # 达到最大重试次数，抛出异常
                    raise e
                self.logger.error(f"验证码识别失败, 准备第 {i+1} 次重试")
                self.logger.debug(e, exc_info=True, stack_info=True)

    @stage(stage_name="付款")
    def __pay(self) -> None:
        self.logger.info("使用校园卡进行快速支付")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        # 选择使用校园卡
        payMent = self.driver.find_element(By.CLASS_NAME, 'payMent')
        payMentItems = payMent.find_elements(By.CLASS_NAME, 'payMentItem')
        payMentItems[0].click()
        # 点击确认支付
        payHandle = self.driver.find_elements(By.CLASS_NAME, 'payHandle')[1]
        payBtns = payHandle.find_elements(By.TAG_NAME, 'button')
        payBtns[1].click()

        # 检查是否成功
        wait_loading_complete(self.driver, (By.CLASS_NAME, 'promoptCon'))
        self.status = check_element_exist(
            self.driver, By.CLASS_NAME, 'promoptCon')

    def __push_court_locking_info(self) -> None:
        """微信推送场地锁定信息
        """
        title = '场地锁定成功'
        content = ''
        place = self.venue
        if place == '羽毛球场':
            place = '邱德拔' + place
        elif place == '羽毛球馆':
            place = '五四' + place

        for time_range in self.venue_time_list:
            content += f"学号: {self.user_name} 成功预约: {place} {self.venue_num}号场地 {time_range}\n"
        content += "\n付款应该自动完成并推送付款信息，如果没有完成请及时手动付款"
        wechat_push(self.sckey, title, content, self.logger)


if __name__ == "__main__":
    # test
    booker = Booker(config_path="config0.ini", logger=setup_logger(
        'config0.ini'), browser_name="chrome")
    booker.book()
