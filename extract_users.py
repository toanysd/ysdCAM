import json

log_file = r'C:\Users\遠藤 健一\.gemini\antigravity\brain\30899e04-6e70-4d9a-8942-c173075df12d\.system_generated\logs\transcript.jsonl'
with open(log_file, 'r', encoding='utf-8') as f:
    with open('user_messages.txt', 'w', encoding='utf-8') as out:
        for line in f:
            try:
                m = json.loads(line)
                if m.get('source') == 'USER_EXPLICIT':
                    out.write(f"[{m['created_at']}]\n{m.get('content')}\n---\n")
            except Exception:
                pass
