import requests
import urllib3

# Suppress InsecureRequestWarning when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

username = "spade605"
token = "ba0f3dd3208247412bfe2457bda6a756616e852d"
host = "www.pythonanywhere.com"

# Warning: SSL verification is disabled. This is not recommended for production environments
# as it makes the connection vulnerable to man-in-the-middle attacks.
response = requests.get(
    "https://{host}/api/v0/user/{username}/cpu/".format(host=host, username=username),
    headers={"Authorization": "Token {token}".format(token=token)},
    verify=False
)
if response.status_code == 200:
    print("CPU quota info:")
    print(response.content)
else:
    print("Got unexpected status code {}: {!r}".format(response.status_code, response.content))