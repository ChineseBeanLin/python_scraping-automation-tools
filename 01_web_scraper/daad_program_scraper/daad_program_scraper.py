# -*- coding: utf-8 -*-
"""
Created on Thu Jun 16 15:33:46 2022

@author: AEsir

DAAD International Programmes Scraper

Description:
    Extracts Master's program data from the DAAD (German Academic Exchange Service) database.
    Instead of parsing HTML, this script interacts directly with the internal Solr API
    to retrieve clean JSON data.

Techniques:
    - API Reverse Engineering (Solr JSON)
    - Standard Library Usage (urllib)
    - JSON to CSV Conversion
"""

from urllib import request 
import json
import time
import re
import os

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
os.chdir(script_dir)
def array2csv(arr) :
    str1 = '\",\"'.join(arr)
    str1 = '\"' + str1 + '\"'
    return str1

limit = 100
file = open('daad.csv', mode = 'w+', encoding = 'utf-8')
avaliable_data_id = ['id', 'courseName', 'academy', 'applicationDeadline']
file.write(array2csv(avaliable_data_id))
# This is the url in 2022 June, which changed now.
# url_fore = "https://www2.daad.de/deutschland/studienangebote/international-programmes/api/solr/en/search.json?cert=&admReq=&langExamPC=&langExamLC=&langExamSC=&degree%5B%5D=2&fos=6&langDeAvailable=&langEnAvailable=&lang%5B%5D=2&modStd%5B%5D=7&fee=&bgn%5B%5D=2&sort=4&dur=&subjects%5B%5D=49&q=&limit=10&offset="
url_format = "https://www2.daad.de/deutschland/studienangebote/international-programmes/api/solr/en/search.json?cert=&admReq=&langExamPC=&langExamLC=&langExamSC=&degree%5B%5D=2&langDeAvailable=&langEnAvailable=&lang%5B%5D=2&lang%5B%5D=4&modStd%5B%5D=7&fee=1&sort=4&dur=&q=Computer%20Science&limit={}&offset={}&display=list&isElearning=&isSep="
rst = []
i = -1
while True :
    i += 1
    time.sleep(0.5)
    url = url_format.format(limit, i*limit)
    response1 = request.urlopen(url)
    # print(response1.read())
    json_str = response1.read()
    try :
        json_data = json.loads(str(json_str, "utf-8"))
        if (len(json_data['courses']) == 0) :
            break
        for j in range(len(json_data['courses'])) :
            courses_data = json_data['courses'][j]
            print(i)
            for pointer in avaliable_data_id:
                # print(courses_data[pointer])
                if (pointer == 'id') :
                    rst.append(str(courses_data[pointer]))
                else :
                    rst.append(re.sub(r'<[^>]+>', '',str(courses_data[pointer]).replace('\n', ' ').replace('\r', ' ').replace('\"', '\'')))
            file.write(array2csv(rst))
            file.write('\n')
            rst = []
    except json.decoder.JSONDecodeError :
        print (json_str)
file.close()        
    
        