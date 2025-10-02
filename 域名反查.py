import requests
import re
# 域名查备案号
def get_number(domain):
    url = f'https://icp.aizhan.com/geticp/?host={domain}&style=text'
    headers = {
        'Host': 'icp.aizhan.com',
        'Cookie': '',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
        'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Accept': '*/*',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Dest': 'script',
        'Referer': 'https://icp.aizhan.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Priority': 'u=2',
        'Connection': 'keep-alive',
    }

    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    pattern = "document.write\((.*?)\);"
    a = re.search(pattern, response.text)
    print(a.group(1))
    return a.group(1)

def get_ICP(domain):
    url = f'https://icp.aizhan.com/{domain}/'
    headers = {
        'Host': 'icp.aizhan.com',
        'Cookie': '',
        'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://icp.aizhan.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Priority': 'u=0, i',
        'Connection': 'keep-alive',
    }

    response = requests.get(url, headers=headers)

    print(response.status_code)

    response.encoding = 'utf-8'
    pattern = "<td>(.*?)&nbsp;&nbsp;"
    a = re.search(pattern, response.text)
    print(a.group(1))
    return a.group(1)

# get_number('slrss.cn')

get_ICP('slrss.cn')