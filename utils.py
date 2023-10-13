import base64
import json
import requests
from configparser import ConfigParser
from PIL import Image
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def get_size(img):
    return Image.open(BytesIO(base64.b64decode(img))).size

def verify(base, content, username, password, retry=0):
    # print(base, slide)
    if retry == 3:
        raise Exception('retry 3 times in captcha')
    data = {"username": username, "password": password,
            "typeid": 43, "image": base, "content": content}
    resp = requests.post("http://api.ttshitu.com/predict", json=data).text
    result = json.loads(resp)
    if result['success']:
        result_str = result['data']['result'].split('|')
        points = [list(map(int, p.split(','))) for p in result_str]
        if len(points) == 3:
            return points
        else:
            return verify(base, content, username, password, retry+1)
        # return map(int, result["data"]["result"].split(','))
    else:
        return result["message"]

def check_element_exist(driver, condition, element):
    """_summary_: 检查元素是否存在且可见

    Args:
        driver (_type_): _description_
        condition (_type_): _description_
        element (_type_): _description_

    Returns:
        bool: is_exist
    """
    try:
        ele = driver.find_element(condition, element)
        return ele.is_displayed()
    except:
        return False

def wait_loading_complete(driver, locator=None, wait_seconds=10) -> None:
    """等待加载完成
    locator 中的要素会被执行一个 util 的等待，条件为 visibility_of_element_located

    Args:
        driver (WebDriver): webdriver
        locator (tuple): 定位器, 为(By, value)的元组, Defaults to None.
    """

    WebDriverWait(driver, wait_seconds).until_not(
        EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
    if (locator):
        WebDriverWait(driver, wait_seconds).until(
            EC.visibility_of_element_located(locator))

# if __name__ == '__main__':
	# result = verify(base, slide)