import requests
from auth_client import with_auth, get_headers

@with_auth
def test_call():
    return requests.get("http://localhost:5050/api/v1/auth/verify", headers=get_headers())

resp = test_call()
print(resp.json())
