import base64
import json
import requests
from configparser import ConfigParser
from PIL import Image
from io import BytesIO


def get_size(img):
    return Image.open(BytesIO(base64.b64decode(img))).size

def verify(base, content, username, password, retry=0):
    # print(base, slide)
    if retry == 3:
        raise Exception('retry 3 times in captcha')
    data = {"username": username, "password": password,
            "typeid": 43, "image": base, "content": content}
    result = json.loads(requests.post("http://api.ttshitu.com/predict", json=data).text)
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

# if __name__ == '__main__':
	# result = verify(base, slide)