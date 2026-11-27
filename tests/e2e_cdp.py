import json, time, urllib.request, websocket
class CDP:
    def __init__(s, port):
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
        tab = [t for t in tabs if t["type"] == "page"][0]
        s.ws = websocket.create_connection(tab["webSocketDebuggerUrl"], max_size=None); s.n = 0
    def call(s, method, **params):
        s.n += 1; i = s.n
        s.ws.send(json.dumps({"id": i, "method": method, "params": params}))
        while True:
            m = json.loads(s.ws.recv())
            if m.get("id") == i:
                if "error" in m: raise RuntimeError(m["error"])
                return m["result"]
    def js(s, expr):
        r = s.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r: raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")
    def goto(s, url, wait=1.2):
        s.call("Page.navigate", url=url); time.sleep(wait)
    def key(s, key, code=None, vk=0, text=None):
        for typ in ("keyDown", "keyUp"):
            p = dict(type=typ, key=key, code=code or key, windowsVirtualKeyCode=vk, nativeVirtualKeyCode=vk)
            if text and typ == "keyDown": p["text"] = text
            s.call("Input.dispatchKeyEvent", **p)
    def click(s, x, y):
        for typ in ("mousePressed", "mouseReleased"):
            s.call("Input.dispatchMouseEvent", type=typ, x=x, y=y, button="left", clickCount=1)
    def shot(s, path, clip=None):
        import base64
        p = {"format": "png"}
        if clip: p["clip"] = dict(clip, scale=1)
        open(path, "wb").write(base64.b64decode(s.call("Page.captureScreenshot", **p)["data"]))
    def viewport(s, w, h, mobile):
        s.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=mobile)
