import urllib.request
import json

base_url = "http://localhost:8000/api/v1"

# 1. Health
with urllib.request.urlopen(f"{base_url}/health") as res:
    print("Health:", res.status, res.read().decode())

# 2. Login
login_data = json.dumps({"email": "admin@codeeagle.com", "password": "admin123"}).encode()
req = urllib.request.Request(f"{base_url}/auth/login", data=login_data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read().decode())
    token = data["access_token"]
    print("Login:", res.status, "Token obtained:", bool(token))

# 3. List & Update Inquiries
req = urllib.request.Request(f"{base_url}/inquiries", headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as res:
    print("Inquiries:", res.status, res.read().decode())

patch_data = json.dumps({"status": "contacted"}).encode()
patch_req = urllib.request.Request(
    f"{base_url}/inquiries/CE-1042",
    data=patch_data,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="PATCH"
)
with urllib.request.urlopen(patch_req) as res:
    print("Patch Inquiry CE-1042:", res.status, res.read().decode())

# 4. List Applications
req = urllib.request.Request(f"{base_url}/applications", headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as res:
    print("Applications:", res.status, res.read().decode())

# 5. List Windows
with urllib.request.urlopen(f"{base_url}/windows") as res:
    print("Windows:", res.status, res.read().decode())

# 6. List Careers
with urllib.request.urlopen(f"{base_url}/careers") as res:
    print("Careers:", res.status, res.read().decode())

print("ALL ENDPOINTS VERIFIED OK!")
