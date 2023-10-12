# -*- coding: utf-8
import sys
import os
import re
from selenium import webdriver
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager, DriverCacheManager
import shutil

def env_check():
    try:
        import selenium
    except ImportError:
        raise ImportError(
            '没有找到selenium包，请用pip安装一下吧～ pip3 install --user selenium')

    lst_conf = sorted([
        fileName for fileName in os.listdir()
        if re.match(r'^config[0-9][0-9]*\.ini$', fileName)
    ],
        key=lambda x: int(re.findall(r'[0-9]+', x)[0]))

    if len(lst_conf) == 0:
        raise ValueError('请先在config.sample.ini文件中填入个人信息，并将它改名为config.ini')

    print('环境检查通过')

    return lst_conf

def check_browser_driver(browser):
    if (browser == 'chrome'):
        __check_chrome_driver()

def __check_chrome_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    driver = None
    while not driver:
        try:
            driver = webdriver.Chrome(chrome_options=chrome_options, executable_path= 'driver/chromedriver.exe')
        except Exception as e: 
            old_version, cnt_version = __get_driver_version_from_exception(e)
            print("Detected that the current driver version and browser version are not compatible, preparing to download a new driver version.") 
            print(f"Old webdriver version: {old_version}")  
            print(f"Current chrome browser version: {cnt_version}")  
            __update_chrome_webdriver(cnt_version, 'driver/test.exe')

    driver.get('chrome://version/')
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # get chrome version
    chrome_version = soup.find('td', {'id': 'version'}).text
    chrome_major_version = chrome_version.split('.')[0]
    print('chrome_version: ', chrome_major_version)

    chromedriver_path = 'chromedriver.exe'
    chromedriver_version = webdriver.__version__.split('.')[0]
    print('chromedriver_version: ', ChromeDriverManager().version)

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