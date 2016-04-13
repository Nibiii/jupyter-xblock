import http.client

conn = http.client.HTTPConnection("127.0.0.1:8081")

payload = "{\"admin\":false,\"usernames\":[\"new_unix_user\"]}"

headers = {
		'referer': "127.0.0.1:8081/hub/",
    'content-type': "application/json",
    'authorization': "Basic ZWR4X3hibG9ja19qdXB5dGVyOmVkeA==",
    }

conn.request("POST", "/hub/api/users", payload, headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
