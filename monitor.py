import os
import requests
import base64
import json
import difflib
import configparser

config = configparser.ConfigParser()
config.read("secrets.ini")

OWNER = config["repo"]["owner"]
REPO = config["repo"]["repo"]
FILE_PATH = config["repo"]["file_path"]
DISCORD_WEBHOOKS = config["discord"]["webhooks"].split(',')

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
HISTORY_URL = f"https://github.com/{OWNER}/{REPO}/commits/master/{FILE_PATH}"
SHA_FILE = "content.json"
WEBHOOK_CHARACTER_LIMIT = 2000

def main():
    # Create the file if it doesn't exist.
    # Should only happen once. The first time the script runs.
    # Eliminates the need to manually create the file.
    if not os.path.exists(SHA_FILE):
        open(SHA_FILE, 'w').close()

    # Read the contents of the old file.
    with open(SHA_FILE, "r") as f:
        old_data = f.read()
        if old_data:
            old_data = json.loads(old_data)

    response = requests.get(API_URL)
    new_data = response.json()

    # No changes have happened when the sha is the same
    if old_data and old_data["sha"] == new_data["sha"]:
        return

    if not old_data:
        # Just write the response to file, because there is nothing to compare to
        with open(SHA_FILE, 'w') as f:
            f.write(response.text)

        return

    # Decode the old and new content to create a diff
    old_content = base64.b64decode(old_data["content"]).decode("utf-8").splitlines(keepends=True)
    new_content = base64.b64decode(new_data["content"]).decode("utf-8").splitlines(keepends=True)

    diff = difflib.unified_diff(old_content, new_content, fromfile="old", tofile="new", n=1)
    formatted_diff = f"<{HISTORY_URL}>```diff\n" + "".join(diff) + "\n```"

    # Discord messages aren't sent if the character limit is exceeded.
    if len(formatted_diff) > WEBHOOK_CHARACTER_LIMIT:
        post_to_webhooks({"content": f"The message exceeded the character limit of {WEBHOOK_CHARACTER_LIMIT}. Find the changes here: <{HISTORY_URL}>"})

    post_to_webhooks({"content": formatted_diff})

    # After all is done, write the new data to the file for next comparison
    with open(SHA_FILE, 'w') as f:
        f.write(response.text)


def post_to_webhooks(content):
    for webhook in DISCORD_WEBHOOKS:
        requests.post(webhook, json=content)

if __name__ == '__main__':
    main()
