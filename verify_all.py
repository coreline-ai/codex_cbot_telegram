"""
all_new_cbot - Verification Script (Final with security bypass)

This script runs the codex command with safety flags for integration testing.
"""

import os
import json
import subprocess

_DIR = os.path.dirname(os.path.abspath(__file__))
MSG_FILE = os.path.join(_DIR, "messages.json")
CODEX_MD = os.path.join(_DIR, "codex.md")

def verify():
    print("🚀 Starting Final Codex Verification (Bypassing Repo Check)...")
    
    # Codex command string - using --full-auto and --skip-git-repo-check
    cmd = f'codex exec --full-auto --skip-git-repo-check --config "developer_instructions_file={CODEX_MD}" "Check messages.json and process message_id 1001 using core.py. Just list files and call core.mark_as_done(1001, instruction=\'Verifying setup\', summary=\'Integration test successful\')."'
    
    print(f"Executing: {cmd}")
    
    # Run codex via shell
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_DIR, shell=True)
    
    print("--- Codex Output ---")
    print(result.stdout)
    if result.stderr:
        print("--- Codex Info/Error ---")
        print(result.stderr)
    
    # Check messages.json
    if os.path.exists(MSG_FILE):
        with open(MSG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for msg in data["messages"]:
                if msg["message_id"] == 1001:
                    print(f"✅ Message 1001 Processed State: {msg.get('processed')}")
    
    # Check Index
    index_file = os.path.join(_DIR, "index.json")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)
            print(f"✅ Indexed Tasks: {len(index.get('tasks', []))}")

if __name__ == "__main__":
    verify()
