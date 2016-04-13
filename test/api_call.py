import http.client

conn = http.client.HTTPConnection("127.0.0.1:8081")

payload = "{\"admin\":true,\"username\":\"edx_xblock_jupyter\", \"password\":\"edx\"}"

headers = {
    'referer': "127.0.0.1:8081/hub/",
    'cache-control': "no-cache",
    'authorization': "Basic ZWR4X3hibG9ja19qdXB5dGVyOmVkeA=="
    }

conn.request("POST", "/hub/api/authorizations/token", payload, headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
