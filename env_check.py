# -*- coding: utf-8
import sys
import os
import re
from selenium import webdriver
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager, DriverCacheManager
from selenium.webdriver.chrome.service import Service as Chrome_Service
import shutil
from configparser import ConfigParser

def env_check():
    try:
        import selenium
    except ImportError:
        raise ImportError(
            '没有找到selenium包，请用pip安装一下吧～ pip3 install --user selenium')

    lst_conf = [
        fileName for fileName in os.listdir()
        if re.match(r'^config[_0-9a-zA-Z]*.ini$', fileName) and is_config_enabled(fileName)
    ]

    if len(lst_conf) == 0:
        raise ValueError('请先在config.sample.ini文件中填入个人信息，并将它改名为config.ini')

    print('环境检查通过')

    return lst_conf

def is_config_enabled(config_name:str) -> bool:
    parser = ConfigParser()
    parser.read(config_name, encoding='utf-8')
    is_enabled = parser.getboolean('enabled', 'enabled')
    return is_enabled

def check_browser_driver(browser):
    # 目前支持了chrome
    if (browser == 'chrome'):
        __check_chrome_driver()

def __check_chrome_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')

    chrome_service = Chrome_Service(executable_path='driver/chromedriver.exe')
    driver = None
    while not driver:
        try:
            driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
        except Exception as e: 
            old_version, cnt_version = __get_driver_version_from_exception(e)
            print("Detected that the current driver version and browser version are not compatible, preparing to download a new driver version.") 
            print(f"Old webdriver version: {old_version}")  
            print(f"Current chrome browser version: {cnt_version}")  
            __update_chrome_webdriver(cnt_version, 'driver/test.exe')

    # Use JavaScript to get the version of Chrome
    chrome_version = driver.execute_script("return navigator.userAgent")
    # get major version from user agent
    chrome_major_version = re.search(r'Chrome/(\d+)\.', chrome_version).group(1)
    print('chrome_major_version: ', chrome_major_version)

    # get chromedriver version
    print('chromedriver_version: ', driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0])

    driver.quit()

def __get_driver_version_from_exception(e:Exception) -> (str,str):
    error_message = e.args[0]
    pattern = r'ChromeDriver only supports Chrome version ([\d\.]+)'
    match = re.search(pattern, error_message)
    if match:
        old_chrome_version = match.group(1)
    else:
        old_chrome_version = None

    pattern = r'Current browser version is ([\d\.]+)'
    match = re.search(pattern, error_message)
    if match:
        current_browser_version = match.group(1)
    else:
        current_browser_version = None

    return old_chrome_version, current_browser_version

def __update_chrome_webdriver(driver_version:str, driver_path:str):
    manager = ChromeDriverManager(cache_manager=DriverCacheManager(root_dir='./driver'))
    path = manager.install()
    shutil.copyfile(path, './driver/chromedriver.exe')
    shutil.rmtree('./driver/.wdm') 
    
    
if __name__ == '__main__':
    check_browser_driver('chrome')
    lst_conf = env_check()