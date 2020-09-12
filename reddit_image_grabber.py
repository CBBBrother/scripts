import requests
import shutil
import argparse
from pathlib import Path

headers = {"User-Agent": "UnixpornGrabber/0.1 by CBBBrother"}

def getAccessToken(client_id, client_token, user, password):
    client_auth = requests.auth.HTTPBasicAuth(client_id, client_token)
    post_data = {"grant_type": "password", "username": user, "password": password}
    response = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data, headers=headers)
    return response.json().get("access_token", None)

def getSaved(user, token, after):
    saved_headers = {"Authorization": "bearer {}".format(token)}
    saved_headers.update(headers)
    params = {}
    if after:
        params.update({"after": after})
    response = requests.get("https://oauth.reddit.com/user/{}/saved/".format(user), params=params, headers=saved_headers)
    return response.json()["data"]

def getFileName(user, title, url):
    wm = "unknown"
    start = title.find("[")
    if start != -1:
        end = title.find("]")
        wm = title[start + 1:end]
    wm = wm.replace(" ", "")
    wm = wm.replace("/", "_")
   
    start = url.rfind("/")
    pic = url[start + 1:]

    return "{}_{}_{}".format(wm, user, pic)

def downloadImage(url, folder, filename):
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = Path.cwd() / folder / filename
    if path.is_file():
        return False
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(path, "wb") as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return True
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Image grabber for reddit saved posts')
    parser.add_argument('client_id', help='app client id')
    parser.add_argument('client_token', help='app client token')
    parser.add_argument('user')
    parser.add_argument('password')
    parser.add_argument('--subreddit', help='filter by subreddit name')
    parser.add_argument('--folder', help='folder to save images, itwill be create if not exist')
    args = parser.parse_args()

    token = getAccessToken(args.client_id, args.client_token, args.user, args.password)
    if token is None:
        print("Can't get token")

    already_get = None
    while True:
        data = getSaved(args.user, token, already_get)
        count = data["dist"]
        already_get = data["after"]
        if not already_get:
            break

        children = data["children"]
        for i in range(count):
            child_data = children[i]["data"]
            user = child_data["author"]
            title = child_data["title"]
            url = child_data["url"]
            subreddit = child_data["subreddit"]
            if args.subreddit and subreddit != args.subreddit:
                continue
            filename = getFileName(user, title, url)
            if filename.find('.') == -1 or child_data["is_video"]:
                continue
            result = downloadImage(url, args.folder, filename)
            print(user, title, url, subreddit, "[success]" if result else "[downloaded early]")
