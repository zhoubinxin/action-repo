import json
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup

import feedparser
import requests
from environs import Env


def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    # 替换所有 <br> 标签为换行符
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # 移除所有标签，包括图片标签
    for tag in soup.find_all(True):
        tag.decompose()

    # 提取文本内容
    text_content = soup.get_text()

    return text_content


def remove_footer(text):
    text = re.sub(r'[☘️📮]+', '', text)
    text = re.sub(r'关注频道\s@(\w+)', '', text)
    text = re.sub(r'投稿爆料\s@(\w+)', '', text)

    return text.strip()


def get_rss(token):
    url = 'https://api.xbxin.com/kv'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    body = {
        'action': 'read',
        'key': 'rss'
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        data = response.json()
        rss = data['data']['value']
        return json.loads(rss)
    elif response.status_code == 404:
        print('Key not found')
        return None
    else:
        return None


def parse(url, history):
    # 解析RSS
    feed = feedparser.parse(url)

    history = datetime.fromisoformat(history)
    new_date = history

    for entry in feed.entries:
        pub_date_str = entry.published
        pub_date = datetime.fromisoformat(pub_date_str)
        if pub_date > new_date:
            new_date = pub_date
        if pub_date <= history:
            break

        title = entry.title
        end_index = title.find('。')
        if end_index == -1:  # 如果没有找到句号，则找第一个逗号
            end_index = title.find('，')
        if end_index != -1:
            title = title[:end_index + 1]  # 包括句号或逗号

        desc = entry.description
        # 使用 BeautifulSoup 处理和清理 HTML 标签
        clean_desc = clean_html(desc)

        # 构造消息内容
        message = f'*{title}*\n{clean_desc}'
        message = remove_footer(message)

        send_to(message)

    return new_date.isoformat()


def send_to(message):
    # 请求数据
    data = {
        "action": "tg",
        'to': 'houinin',
        'message': message,
        'msg_type': 'Markdown'
    }

    api_url = 'https://api.xbxin.com/msg'

    # 发送请求
    response = requests.post(api_url, json=data)

    # 检查请求是否成功
    if response.status_code == 200:
        print(f'消息推送成功')
    else:
        print(f'消息推送失败: {response.text}')


def save_rss(token, rss):
    url = 'https://api.xbxin.com/kv'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    body = {
        'action': 'write',
        'key': 'rss',
        'value': json.dumps(rss)
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        print('RSS保存成功')
    else:
        print(f'RSS保存失败: {response.text}')


def main():
    env = Env()
    env.read_env()
    token = env.str('TOKEN')

    Route = {
        'tg': '/telegram/channel',
        'weibo': '/weibo/user',
        'xhs': '/xiaohongshu/user'
    }
    baseurl = 'https://rss.xbxin.com/rss'

    rss = get_rss(token)

    for item in rss:
        for sub in rss[item]:
            rss_url = f'{baseurl}{Route[item]}/{sub}'
            new_date = parse(rss_url, rss[item][sub])
            rss[item][sub] = new_date
            time.sleep(5)

    save_rss(token,rss)


if __name__ == '__main__':
    main()
