import urllib.request
import json
import http.cookiejar

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

req1 = urllib.request.Request("http://127.0.0.1:5000/login", data=json.dumps({"email": "alice@example.com", "password": "password123"}).encode('utf-8'), headers={'Content-Type': 'application/json'})
opener.open(req1)

for route in ['/sections', '/schedule']:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:5000{route}")
        res = opener.open(req)
        print(f"{route} SUCCESS: {res.status}")
    except urllib.error.HTTPError as e:
        print(f"{route} ERROR: {e.code}")
