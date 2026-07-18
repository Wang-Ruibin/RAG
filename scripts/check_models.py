import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'Authorization': 'Bearer sk-501d5ac4e336457cb1efc63d8ab333cd',
    'Content-Type': 'application/json'
}

# List models
r = requests.get('https://api.siliconflow.cn/v1/models', headers=headers, timeout=10)
if r.status_code == 200:
    models = r.json().get('data', [])
    ds_models = [m for m in models if 'deepseek' in m.get('id','').lower()]
    print('DeepSeek models available:')
    for m in ds_models:
        print(f'  {m["id"]}')
    if not ds_models:
        print(f'No deepseek found. Total models: {len(models)}')
        for m in models[:20]:
            print(f'  {m["id"]}')
else:
    print(f'API Error: {r.status_code}')
    print(r.text[:500])
