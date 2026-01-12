import requests

url = "http://127.0.0.1:8000/upload"
with open("a2.jpg", "rb") as f:
    response = requests.post(
        url,
        files={"file": ("a2.jpg", f, "image/jpeg")},
        data={"handle": "@betty"}
    )

print(response.json())
