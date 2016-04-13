import http.client

conn = http.client.HTTPConnection("127.0.0.1:8081")

headers = {
    'referer': "127.0.0.1:8081/hub/",
    'cache-control': "no-cache",
    'cookie': "jupyter-hub-token=\"2|1:0|10:1460464624|17:jupyter-hub-token|44:ZjZmYzUzMTRlMjgzNDE0MzkzYjcwODQ2YjEyN2I4YjY=|9f2e40c810b8fb1744cb4e203bec24ea94f3cb82d75b3d097419aade3dbd10a7\""
    }

conn.request("POST", "/hub/api/proxy", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
