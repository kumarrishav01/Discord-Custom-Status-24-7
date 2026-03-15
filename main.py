import os
import sys
import json
import time
import requests
import websocket
import threading
from keep_alive import keep_alive

# Collect all tokens with their corresponding status and custom_status
tokens_config = []

# Try to collect token, token1, token2, token3, etc.
index = 0
while True:
    if index == 0:
        token_key = "token"
        status_key = "status"
        custom_status_key = "custom_status"
    else:
        token_key = f"token{index}"
        status_key = f"status{index}"
        custom_status_key = f"custom_status{index}"
    
    token = os.getenv(token_key)
    if not token:
        break
    
    status = os.getenv(status_key, "online")  # Default to online if not specified
    custom_status = os.getenv(custom_status_key, "")  # Default to empty if not specified
    
    tokens_config.append({
        "token": token,
        "status": status,
        "custom_status": custom_status
    })
    
    index += 1

if not tokens_config:
    print("[ERROR] Please add at least one token inside Secrets (token, token1, token2, etc.).")
    sys.exit()

# Validate all tokens
validated_tokens = []
for config in tokens_config:
    token = config["token"]
    headers = {"Authorization": token, "Content-Type": "application/json"}
    
    validate = requests.get("https://canary.discordapp.com/api/v9/users/@me", headers=headers)
    if validate.status_code != 200:
        print(f"[ERROR] Token '{token[:20]}...' might be invalid. Skipping this token.")
        continue
    
    userinfo = requests.get("https://canary.discordapp.com/api/v9/users/@me", headers=headers).json()
    config["username"] = userinfo["username"]
    config["discriminator"] = userinfo["discriminator"]
    config["userid"] = userinfo["id"]
    validated_tokens.append(config)

if not validated_tokens:
    print("[ERROR] No valid tokens found. Please check your tokens again.")
    sys.exit()

def onliner(token, status, custom_status):
    try:
        ws = websocket.WebSocket()
        ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
        start = json.loads(ws.recv())
        heartbeat = start["d"]["heartbeat_interval"]
        auth = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "Windows 10",
                    "$browser": "Google Chrome",
                    "$device": "Windows",
                },
                "presence": {"status": status, "afk": False},
            },
            "s": None,
            "t": None,
        }
        ws.send(json.dumps(auth))
        cstatus = {
            "op": 3,
            "d": {
                "since": 0,
                "activities": [
                    {
                        "type": 4,
                        "state": custom_status,
                        "name": "Custom Status",
                        "id": "custom",
                        #Uncomment the below lines if you want an emoji in the status
                        #"emoji": {
                            #"name": "emoji name",
                            #"id": "emoji id",
                            #"animated": False,
                        #},
                    }
                ],
                "status": status,
                "afk": False,
            },
        }
        ws.send(json.dumps(cstatus))
        online = {"op": 1, "d": "None"}
        time.sleep(heartbeat / 1000)
        ws.send(json.dumps(online))
    except Exception as e:
        print(f"[ERROR] Connection failed for token: {e}")

def run_token_keepalive(config):
    """Keep a single token online"""
    token = config["token"]
    status = config["status"]
    custom_status = config["custom_status"]
    username = config["username"]
    discriminator = config["discriminator"]
    
    print(f"[{username}#{discriminator}] Keep-alive started with status: {status}")
    while True:
        onliner(token, status, custom_status)
        time.sleep(30)

def run_onliner():
    os.system("cls")
    print(f"Logged in with {len(validated_tokens)} token(s):")
    for config in validated_tokens:
        print(f"  - {config['username']}#{config['discriminator']} ({config['userid']})")
    print()
    
    # Create a thread for each token
    threads = []
    for config in validated_tokens:
        thread = threading.Thread(target=run_token_keepalive, args=(config,), daemon=True)
        threads.append(thread)
        thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        sys.exit()

keep_alive()
run_onliner()
