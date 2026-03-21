import urllib.request
import json
import http.cookiejar

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

login_data = json.dumps({"email": "alice@example.com", "password": "password123"}).encode('utf-8')
req1 = urllib.request.Request("http://127.0.0.1:5000/login", data=login_data, headers={'Content-Type': 'application/json'})
res1 = opener.open(req1)

req3 = urllib.request.Request("http://127.0.0.1:5000/schedule")
try:
    res3 = opener.open(req3)
    print(f"Schedule Status: {res3.status}")
except urllib.error.HTTPError as e:
    print(f"Schedule Error Status: {e.code}")
    print(e.read().decode())
