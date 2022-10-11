import base64
import json
import requests
from configparser import ConfigParser
from PIL import Image
from io import BytesIO


def get_size(img):
    return Image.open(BytesIO(base64.b64decode(img))).size

def verify(base, slide, username, password):
    # print(base, slide)
    data = {"username": username, "password": password,
            "typeid": 18, "image": slide, "imageback": base}
    result = json.loads(requests.post("http://api.ttshitu.com/predict", json=data).text)
    if result['success']:
        return map(int, result["data"]["result"].split(','))
    else:
        return result["message"]

# if __name__ == '__main__':
	# result = verify(base, slide)