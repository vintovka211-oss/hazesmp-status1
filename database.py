import json
import os

DATA_FILE = "data/shop_data.json"
KEYS_FILE = "data/keys_data.json"
USED_KEYS_FILE = "data/used_keys.json"
USERS_FILE = "data/users.json"

# Гарантируем, что папка data существует
os.makedirs("data", exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        default = {"prices": {"1day": 100, "7day": 500, "30day": 1500, "forever": 5000}}
        save_data(default)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_keys():
    if not os.path.exists(KEYS_FILE):
        default = {
            "1day": ["DEMO_KEY_1DAY_001"],
            "7day": ["DEMO_KEY_7DAY_001"],
            "30day": ["DEMO_KEY_30DAY_001"],
            "forever": ["DEMO_KEY_FOREVER_001"]
        }
        save_keys(default)
        return default
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=4, ensure_ascii=False)

def load_used_keys():
    if not os.path.exists(USED_KEYS_FILE):
        save_used_keys([])
        return []
    with open(USED_KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_used_keys(used):
    with open(USED_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, indent=4, ensure_ascii=False)

def load_users():
    if not os.path.exists(USERS_FILE):
        save_users([])
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

def get_and_remove_key(tarif):
    keys = load_keys()
    used = load_used_keys()
    if not keys.get(tarif) or len(keys[tarif]) == 0:
        return None
    key = keys[tarif].pop(0)
    used.append(key)
    save_keys(keys)
    save_used_keys(used)
    return key

def add_key(tarif, key):
    keys = load_keys()
    if tarif not in keys:
        keys[tarif] = []
    keys[tarif].append(key)
    save_keys(keys)
