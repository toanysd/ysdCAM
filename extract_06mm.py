import json

log_file = r'C:\Users\遠藤 健一\.gemini\antigravity\brain\30899e04-6e70-4d9a-8942-c173075df12d\.system_generated\logs\transcript.jsonl'
with open(log_file, 'r', encoding='utf-8') as f:
    with open('reqs_06mm.txt', 'w', encoding='utf-8') as out:
        for line in f:
            try:
                m = json.loads(line)
                if m.get('source') in ['USER_EXPLICIT', 'MODEL']:
                    content = m.get('content', '')
                    if '0.6mm' in content or 'tính toán lỗ' in content:
                        out.write(f"[{m['created_at']} {m['source']}]\n{content}\n---\n")
            except Exception:
                pass
