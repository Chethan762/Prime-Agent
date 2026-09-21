import subprocess
import json

cmd = [
    "bash", "./../prime-agent.sh",
    "--mode", "rpc",
    "--no-session",
    "--provider", "groq",
    "--model", "openai/gpt-oss-20b",
    "--thinking", "low",
    "--no-context-files",
    "--no-prompt-templates",
    "--tools", "ipython",
]

process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

request = {
    "id": "test-1",
    "type": "prompt",
    "message": "Use ipython to run: python -m py_compile generated/dynamic_scraper.py. Reply only with PASS or FAIL.",
}

process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()

for line in process.stdout:
    event = json.loads(line)
    print("EVENT:", event.get("type"), "|", json.dumps(event, ensure_ascii=False), flush=True)

    if event.get("type") == "message_update":
        delta = event.get("assistantMessageEvent", {})
        if delta.get("type") == "text_delta":
            print(delta.get("delta", ""), end="", flush=True)

    elif event.get("type") == "agent_end":
        print()
        break

process.stdin.close()
process.terminate()
