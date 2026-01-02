# -*- coding: utf-8 -*-
"""
Baidu OCR API Wrapper

Handles interaction with Baidu Cloud OCR services for text recognition.
"""
# NOTICE: Ensure actual API keys are NOT committed to version control.
# Use environment variables or a local-only config file.
try:
    import config.baidu_aip_config as config
    APP_ID = config.BAIDU_APP_ID
    API_KEY = config.BAIDU_API_KEY
    SECRET_KEY = config.BAIDU_SECRET_KEY
except ImportError:
    # Fallback for portfolio demonstration if config is missing
    APP_ID, API_KEY, SECRET_KEY = "DUMMY", "DUMMY", "DUMMY"

from aip import AipOcr

client = AipOcr(APP_ID, API_KEY, SECRET_KEY)

def image2text(file_path):
    """Extracts text from an image file."""
    with open(file_path, 'rb') as fp:
        image = fp.read()
    
    dic_result = client.basicGeneral(image)
    if 'words_result' not in dic_result:
        return ""
        
    res = dic_result['words_result']
    result = ''
    for m in res:
        result += str(m['words'])
    return result

def image2num(file_path):
    """Extracts numeric values from an image."""    
    with open(file_path, "rb") as fp:
        image = fp.read()
   
    res_image = client.numbers(image)   
    if 'words_result' not in res_image:
        return []

    result = []
    for m in res_image['words_result']:
        try:
            result.append(int(m['words']))
        except ValueError:
            pass
    return result

if __name__ == '__main__':
    # Test function
    pass