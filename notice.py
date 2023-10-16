from email.header import Header
from email.mime.text import MIMEText
from urllib.parse import quote
from urllib import request
import json
import logging


# ! Deprecated
def wechat_notification(user_name, venue, venue_num, start_time, end_time, sckey):
    with request.urlopen(
            quote('https://sctapi.ftqq.com/' + sckey + '.send?title=成功预约&desp=学号：' +
                  str(user_name) + ' 成功预约：' + str(venue) + " 场地编号："+str(venue_num) +
                  " 开始时间："+str(start_time)+" 结束时间："+str(end_time),
                  safe='/:?=&')) as response:
        response = json.loads(response.read().decode('utf-8'))
        if response['code'] == 0 and response['data']['error'] == 'SUCCESS':
            print('微信通知成功')
        else:
            print(str(response['errno']) + ' error: ' + response['errmsg'])
    return "微信通知成功\n"

def wechat_push(sckey:str, title:str, content:str, logger=None) -> None:
    """通过server酱公众号完成微信推送的功能

    Args:
        sckey (`str`): server酱的sendKey

        title (`str`): 推送信息的标题

        content (`str`): 推送信息的内容

        logger (`logging.Logger`, optional): logger. Defaults to `logging.getLogger()`.

    """
    if logger is None:
        logger = logging.getLogger()

    with request.urlopen(
            quote('https://sctapi.ftqq.com/' + sckey + '.send?title=' + title + '&desp=' + content,
                  safe='/:?=&')) as response:
        response = json.loads(response.read().decode('utf-8'))
        if response['code'] == 0 and response['data']['error'] == 'SUCCESS':
            logger.info('微信通知成功')
        else:
            logger.error('Errno:' + str(response['errno']) + ': ' + response['errmsg'])

if __name__ == '__main__':
    # wechat_notification('', "羽毛球场测试",
    #                     "")
    wechat_push('', 'test', 'test')

