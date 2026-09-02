import requests, os
url='http://localhost:8000/api/search/image?top_k=3'
file_path=os.path.abspath(os.path.join('..','train','train','tile_10','img_10.jpg'))
print('upload', file_path, os.path.exists(file_path))
with open(file_path,'rb') as f:
    r=requests.post(url, files={'file': f})
print('status', r.status_code)
try:
    print('json', r.json())
except Exception:
    print('text', r.text)
