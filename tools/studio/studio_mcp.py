"""Minimal stdio client for Roblox's StudioMCP.exe (the app's connector rejects its protocol version).
usage: studio_mcp.py list | call <tool> <json args or @file> [timeout_s]
"""
import json, os, subprocess, sys, threading, queue, time

EXE = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\mcp.bat")
VERSION = os.environ.get("MCP_VERSION", "2026-07-28")

proc = subprocess.Popen(["cmd.exe", "/c", EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
out = queue.Queue()
threading.Thread(target=lambda: [out.put(l) for l in proc.stdout], daemon=True).start()
threading.Thread(target=lambda: [sys.stderr.write("[stderr] " + l) for l in proc.stderr], daemon=True).start()


def send(o):
    proc.stdin.write(json.dumps(o) + "\n")
    proc.stdin.flush()


def request(i, method, params, timeout):
    send({"jsonrpc": "2.0", "id": i, "method": method, "params": params})
    end = time.time() + timeout
    while time.time() < end:
        try:
            line = out.get(timeout=max(0.1, end - time.time()))
        except queue.Empty:
            break
        try:
            m = json.loads(line)
        except ValueError:
            print("[non-json]", line.rstrip())
            continue
        if m.get("id") == i:
            return m
    raise TimeoutError(method)


try:
    init = request(1, "initialize", {"protocolVersion": VERSION, "capabilities": {},
                                     "clientInfo": {"name": "local-studio-client", "version": "1"}}, 30)
    print("[init]", json.dumps(init.get("result", init))[:400])
    send({"jsonrpc": "2.0", "method": "notifications/initialized"}); time.sleep(float(os.environ.get("MCP_WAIT", "4")))
    if sys.argv[1] == "list":
        r = request(2, "tools/list", {}, 30)
        for t in r.get("result", {}).get("tools", []):
            if len(sys.argv) < 3 or t["name"] == sys.argv[2]:
                print(t["name"], json.dumps(t.get("inputSchema", {}))[:int(sys.argv[3]) if len(sys.argv) > 3 else 300])
        if "error" in r:
            print(r)
    else:
        a = sys.argv[3]
        args = json.load(open(a[1:], encoding="utf-8")) if a.startswith("@") else json.loads(a)
        timeout = float(sys.argv[4]) if len(sys.argv) > 4 else 120
        for attempt in range(8):
            r = request(10 + attempt, "tools/call", {"name": sys.argv[2], "arguments": args}, timeout)
            if "No Roblox Studio instances" not in json.dumps(r)[:400]:
                break
            time.sleep(2)
        res = r.get("result", r)
        import base64
        for n, c in enumerate(res.get("content", []) if isinstance(res, dict) else []):
            if c.get("type") == "image":
                p = os.environ.get("MCP_IMG", "capture.png")
                ext = c.get("mimeType", "image/png").split("/")[-1]
                p = os.path.splitext(p)[0] + "." + ext
                open(p, "wb").write(base64.b64decode(c["data"]))
                c["data"] = "saved " + p
        print(json.dumps(res, ensure_ascii=False)[:20000])
finally:
    proc.terminate()
