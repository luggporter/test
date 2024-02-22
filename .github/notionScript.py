import os
import requests
import logging
from datetime import datetime, timezone, timedelta

# 로깅 레벨 설정
logging.basicConfig(level=logging.INFO)

# Notion API 토큰 및 데이터베이스 ID 설정
NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_API_DATABASE_ID')

# GitHub API 토큰 및 저장소 설정
GITHUB_API_TOKEN = os.getenv('GITHUB_API_TOKEN')
GITHUB_REPO_OWNER = 'luggporter'
GITHUB_REPO_NAME = 'test'

logging.info(f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases')
logging.info(NOTION_API_TOKEN)
logging.info(GITHUB_API_TOKEN)

# GitHub 릴리스 정보 가져오기
response = requests.get(f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases',
                        headers={'Authorization': f'token {GITHUB_API_TOKEN}'})

# 에러 체크 추가
if response.status_code != 200:
    print(f"Failed to fetch GitHub releases. Status code: {response.status_code}")
    print(response.text)
    exit(1)

# response.json()의 형태가 예상과 다를 경우에 대비하여 추가적인 체크
if not isinstance(response.json(), list):
    print("GitHub API response is not a list. Exiting...")
    exit(1)

release_dates = [release['created_at'] for release in response.json()]

github_release_notes_list = [
    {'name': release['name'], 'body': release['body']} for release in response.json()
]

table_data = list(map(lambda date, content: {'date': date, 'content': content}, release_dates, github_release_notes_list))

def create_notion_page():
    headers = {
        'Authorization': f'Bearer {NOTION_API_TOKEN}',
        'Content-Type': 'application/json',
        "Notion-Version": "2021-08-16"
    }
    # 조회 URL
    query_notion_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'

    # 등록 URL
    create_notion_url = f'https://api.notion.com/v1/pages/'

    query_response = requests.post(query_notion_url, headers=headers)
    pages = query_response.json().get('results', [])

    # 각 페이지에 대해 삭제 요청 보내기
    for page in pages:
        page_id = page['id']
        delete_url_headers = {
            'Authorization': f'Bearer {NOTION_API_TOKEN}',
            'Content-Type': 'application/json',
            "Notion-Version": "2022-06-28"
        }
        delete_data = {
            "archived": True
        }
        delete_url = f'https://api.notion.com/v1/pages/{page_id}'

        delete_response = requests.patch(delete_url, headers=delete_url_headers, json=delete_data)

        if delete_response.status_code == 200:
            print(f"Page {page_id} deleted successfully.")
        else:
            print(f"Failed to delete page {page_id}. Status code: {delete_response.status_code}")

    # 등록 시작
    for row in table_data:
        # GitHub Release Notes 내용 처리
        github_release_notes_content = row['content']['body'].replace('\r\n', '\n').replace('##', '\n')
        utc_datetime = datetime.strptime(row['date'], "%Y-%m-%dT%H:%M:%SZ")
        kst_timezone = timezone(timedelta(hours=9))
        kst_datetime = utc_datetime.replace(tzinfo=timezone.utc).astimezone(kst_timezone)

        data = {
            'parent': {"database_id": NOTION_DATABASE_ID},
            'properties': {
                '배포날짜': {
                    'type': 'title',
                    'title': [{'text': {'content': kst_datetime.strftime("%Y년 %m월 %d일 \n%H:%M:%S")}}],
                },
                '버전': {
                    'type': 'rich_text',
                    'rich_text': [{'text': {'content': row['content']['name'].replace('관리자홈페이지 ', '').replace('🌈', '')}}],
                },
                '릴리즈노트_내용': {
                    'type': 'rich_text',
                    # 'rich_text': [{'text': {'content': str(row['content'])}}],
                    'rich_text': [{'text': {'content': github_release_notes_content}}],
                },
            },
        }

        response = requests.post(create_notion_url, headers=headers, json=data)

        if response.status_code != 200:
            print(response.status_code)
            print(response.json())

if len(table_data) > 0:
    create_notion_page()
