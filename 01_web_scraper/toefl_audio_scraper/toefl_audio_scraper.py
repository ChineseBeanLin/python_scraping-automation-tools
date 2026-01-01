"""
TOEFL/TPO Content Scraper

Description:
    A crawler designed to extract study materials from the KMF TOEFL platform.
    It iterates through pagination, parses detailed pages, and cleans HTML tags
    to extract pure text content.

Techniques:
    - DOM Parsing (BeautifulSoup)
    - Regular Expressions (Regex) for data cleaning
    - HTTP Header spoofing (User-Agent)
"""
import re
import time
import requests
import bs4
import os

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
os.chdir(script_dir)


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 			(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE",
    }

root_url = "https://toefl.kmf.com"
read_url = "/read/ets/new-order/{}/0"

def parse_content(html_content) :
    """
    Extracts the main content div and removes all HTML tags 
    to return clean text.
    """
    soup = bs4.BeautifulSoup(html_content, features="html.parser")
    content = soup.find('div', attrs={"id":"js-stem-cont"})
    return re.sub(r"<.*?>", "", str(content))


def get_read_detail_url(html_content):
    """Extracts links to individual articles from the list page."""
    links = []
    soup = bs4.BeautifulSoup(html_content, features="html.parser")
    ori_links = soup.find_all('a', attrs={"class": "check-links js-check-link"})
    for ori_link in ori_links:
        links.append(ori_link.attrs["href"])
    return links


if __name__=="__main__":
    read_detail_url = ""
    links = []
    for i in range(1, 12):
        r = requests.get(root_url+read_url.format(str(i)), headers=headers)
        temp = get_read_detail_url(r.content)
        links.extend(temp)
        time.sleep(0.5)
    with open("tpo.txt", 'wb') as f:
        for link in links:
            r = requests.get(root_url+link, headers=headers)
            time.sleep(0.5)
            f.write(bytes(parse_content(r.content), encoding='utf-8'))
            f.flush()
        f.close


