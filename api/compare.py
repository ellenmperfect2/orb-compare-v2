"""
api/compare.py
Vercel Python serverless function.
Queries Metronome + Orb Mintlify assistants in parallel and returns
a side-by-side HTML comparison page.
"""

import asyncio
import json
import uuid
import html
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import httpx

MINTLIFY_HOST = "https://leaves.mintlify.com"

PRODUCTS = {
    "metronome": {
        "fp":    "metronome-b35a6a36",
        "name":  "Metronome",
        "docs":  "https://docs.metronome.com",
        "path":  "/guides/pricing-packaging/billing-model-guides/enterprise-commit",
        "color": "#e8c547",
    },
    "orb": {
        "fp":    "orb-9bba378a",
        "name":  "Orb",
        "docs":  "https://docs.withorb.com",
        "path":  "/overview",
        "color": "#5b9cf6",
    },
}


async def query_mintlify(product_key: str, question: str) -> str:
    p = PRODUCTS[product_key]
    url = f"{MINTLIFY_HOST}/api/assistant/{p['fp']}/message"

    payload = {
        "fp": p["fp"],
        "threadId": None,
        "threadKey": None,
        "messages": [
            {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": "user",
                "content": question,
                "parts": [{"type": "text", "text": question}],
            }
        ],
        "currentPath": p["path"],
    }

    headers = {
        "Content-Type": "application/json",
        "Origin": p["docs"],
        "Referer": p["docs"] + "/",
    }

    text_chunks = []

    async with httpx.AsyncClient(timeout=60.0) as http:
        async with http.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("0:"):
                    try:
                        token = json.loads(line[2:])
                        text_chunks.append(token)
                    except json.JSONDecodeError:
                        text_chunks.append(line[2:])
                elif line.startswith("d:"):
                    break

    return "".join(text_chunks)


def render_html(question: str, answer_a: str, answer_b: str) -> str:
    pa = PRODUCTS["metronome"]["name"]
    pb = PRODUCTS["orb"]["name"]
    ca = PRODUCTS["metronome"]["color"]
    cb = PRODUCTS["orb"]["color"]

    # Escape for safe HTML embedding
    q_safe  = html.escape(question)
    aa_safe = html.escape(answer_a)
    ab_safe = html.escape(answer_b)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{pa} vs {pb} — {q_safe}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #0c0c0c; --surf: #141414; --surf2: #1a1a1a;
  --b0: #242424; --b1: #2e2e2e;
  --tx: #e6e2d9; --txm: #888; --txd: #444;
  --ca: {ca}; --cb: {cb};
  --r: 10px; --rl: 16px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg); color: var(--tx);
  font-family: 'DM Sans', sans-serif; font-size: 14.5px; line-height: 1.7;
  min-height: 100vh;
}}

/* ── header ── */
.hdr {{
  border-bottom: 1px solid var(--b0);
  padding: 24px 40px;
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
}}
.hdr-left {{ flex: 1; min-width: 0; }}
.eyebrow {{
  font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--txd); margin-bottom: 6px;
}}
.hdr h1 {{
  font-family: 'DM Serif Display', serif; font-size: 20px; font-weight: 400;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.hdr h1 em {{ color: var(--ca); font-style: italic; }}
.question-pill {{
  font-family: 'DM Mono', monospace; font-size: 11px; color: var(--txm);
  margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.back-btn {{
  flex-shrink: 0;
  padding: 7px 16px; border-radius: 100px;
  background: var(--surf2); border: 1px solid var(--b1);
  color: var(--txm); font-size: 12px; font-family: 'DM Sans', sans-serif;
  cursor: pointer; text-decoration: none; transition: color .15s, border-color .15s;
}}
.back-btn:hover {{ color: var(--tx); border-color: var(--b0); }}

/* ── main grid ── */
.main {{ display: grid; grid-template-columns: 1fr 1fr; height: calc(100vh - 73px); }}

.col {{
  display: flex; flex-direction: column;
  border-right: 1px solid var(--b0); overflow: hidden;
}}
.col:last-child {{ border-right: none; }}

.col-hdr {{
  padding: 18px 28px 16px;
  border-bottom: 1px solid var(--b0);
  display: flex; align-items: center; gap: 10px;
  flex-shrink: 0;
}}
.col-dot {{
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}}
.col-name {{
  font-family: 'DM Mono', monospace; font-size: 11px; font-weight: 500;
  letter-spacing: .08em; text-transform: uppercase;
}}
.col-name.a {{ color: var(--ca); }}
.col-name.b {{ color: var(--cb); }}
.col-link {{
  margin-left: auto; font-size: 11px; color: var(--txd);
  text-decoration: none; font-family: 'DM Mono', monospace;
}}
.col-link:hover {{ color: var(--txm); }}

.col-body {{
  flex: 1; overflow-y: auto; padding: 28px;
  scrollbar-width: thin; scrollbar-color: var(--b1) transparent;
}}
.col-body::-webkit-scrollbar {{ width: 4px; }}
.col-body::-webkit-scrollbar-track {{ background: transparent; }}
.col-body::-webkit-scrollbar-thumb {{ background: var(--b1); border-radius: 2px; }}

.answer-text {{
  font-size: 14px; color: #c8c3b8; line-height: 1.85;
  white-space: pre-wrap; word-break: break-word;
}}

/* ── loading state ── */
.loading {{
  display: flex; align-items: center; gap: 10px;
  color: var(--txm); font-size: 13px; font-family: 'DM Mono', monospace;
}}
.dots span {{
  display: inline-block; width: 4px; height: 4px; border-radius: 50%;
  background: var(--txm); margin: 0 2px;
  animation: blink 1.2s infinite;
}}
.dots span:nth-child(2) {{ animation-delay: .2s; }}
.dots span:nth-child(3) {{ animation-delay: .4s; }}
@keyframes blink {{
  0%, 80%, 100% {{ opacity: .15; transform: scale(.8); }}
  40% {{ opacity: 1; transform: scale(1); }}
}}

/* ── new query bar ── */
.query-bar {{
  grid-column: 1 / -1;
  border-top: 1px solid var(--b0);
  padding: 16px 28px;
  display: flex; gap: 10px; align-items: center;
  background: var(--surf);
}}
.query-input {{
  flex: 1; background: var(--bg); border: 1px solid var(--b1);
  border-radius: var(--r); padding: 10px 16px;
  color: var(--tx); font-size: 13.5px; font-family: 'DM Sans', sans-serif;
  outline: none; transition: border-color .15s;
}}
.query-input::placeholder {{ color: var(--txd); }}
.query-input:focus {{ border-color: var(--ca); }}
.query-btn {{
  padding: 10px 20px; border-radius: var(--r);
  background: var(--ca); border: none; color: #0c0c0c;
  font-size: 13px; font-weight: 600; font-family: 'DM Sans', sans-serif;
  cursor: pointer; transition: opacity .15s; white-space: nowrap;
  flex-shrink: 0;
}}
.query-btn:hover {{ opacity: .85; }}
.query-btn:disabled {{ opacity: .4; cursor: not-allowed; }}

@media (max-width: 700px) {{
  .main {{ grid-template-columns: 1fr; height: auto; }}
  .col {{ border-right: none; border-bottom: 1px solid var(--b0); min-height: 50vh; }}
  .hdr {{ padding: 18px 20px; }}
  .query-bar {{ padding: 14px 20px; flex-wrap: wrap; }}
}}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-left">
    <div class="eyebrow">Docs Comparison Tool · Orb Internal</div>
    <h1><em>{pa}</em> vs {pb}</h1>
    <div class="question-pill">Q: {q_safe}</div>
  </div>
  <a href="/" class="back-btn">← New query</a>
</header>

<div class="main" id="main">
  <div class="col" id="col-a">
    <div class="col-hdr">
      <div class="col-dot" style="background:{ca}"></div>
      <span class="col-name a">{pa}</span>
      <a href="https://docs.metronome.com" target="_blank" class="col-link">docs ↗</a>
    </div>
    <div class="col-body">
      <div class="answer-text">{aa_safe}</div>
    </div>
  </div>

  <div class="col" id="col-b">
    <div class="col-hdr">
      <div class="col-dot" style="background:{cb}"></div>
      <span class="col-name b">{pb}</span>
      <a href="https://docs.withorb.com" target="_blank" class="col-link">docs ↗</a>
    </div>
    <div class="col-body">
      <div class="answer-text">{ab_safe}</div>
    </div>
  </div>
</div>

<div class="query-bar">
  <input
    class="query-input"
    id="new-q"
    type="text"
    placeholder="Ask another question..."
    onkeydown="if(event.key==='Enter') runQuery()"
  />
  <button class="query-btn" onclick="runQuery()">Compare →</button>
</div>

<script>
function runQuery() {{
  const q = document.getElementById('new-q').value.trim();
  if (!q) return;
  window.location.href = '/api/compare?q=' + encodeURIComponent(q);
}}
</script>
</body>
</html>"""


def render_loading_html(question: str) -> str:
    """Shown while results stream — we redirect immediately so this is a fallback."""
    q_safe = html.escape(question)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Comparing...</title>
<meta http-equiv="refresh" content="0;url=/api/compare?q={html.escape(question, quote=True)}">
</head><body></body></html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        question = params.get("q", [""])[0].strip()

        if not question:
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        try:
            # Run both queries concurrently
            answer_a, answer_b = asyncio.run(asyncio.gather(
                query_mintlify("metronome", question),
                query_mintlify("orb", question),
            ))

            page = render_html(question, answer_a, answer_b)
            body = page.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            error_body = f"<pre>Error: {html.escape(str(e))}</pre>".encode()
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(error_body)))
            self.end_headers()
            self.wfile.write(error_body)

    def log_message(self, format, *args):
        pass  # suppress default logging
