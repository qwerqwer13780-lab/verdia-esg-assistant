import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv('VERDIA_AI_URL', 'http://127.0.0.1:8000').rstrip('/')


def get(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=30) as response:
        return response.status, json.loads(response.read().decode('utf-8'))


def post(path, payload):
    body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method='POST',
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.status, json.loads(response.read().decode('utf-8'))


def main():
    status, health = get('/health')
    print('health', status, health)
    if status != 200:
        return 1

    questions = [
        'What is the difference between Scope 1 and Scope 2 emissions?',
        'What should a company collect to calculate purchased electricity emissions?',
        'Who won the football match yesterday?',
    ]

    for question in questions:
        try:
            status, response = post('/api/esg/chat', {'question': question, 'history': []})
            print('\nQ:', question)
            print('status:', status, 'mode:', response.get('mode'), 'grounded:', response.get('grounded'))
            print('A:', response.get('answer'))
        except urllib.error.HTTPError as exc:
            print('\nQ:', question)
            print('HTTP', exc.code, exc.read().decode('utf-8'))

    return 0


if __name__ == '__main__':
    sys.exit(main())
