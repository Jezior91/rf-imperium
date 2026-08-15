"""RF Imperium — WebSocket Dashboard Server (localhost:8765)"""
import asyncio
import json
import threading
from datetime import datetime


DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<title>RF Imperium Dashboard</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d0d0d; color: #00ff88; font-family: 'Courier New', monospace; padding: 20px; }
h1 { color: #00ccff; font-size: 24px; margin-bottom: 20px; }
.cards { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
.card { background: #1a1a2e; border: 1px solid #333; border-radius: 8px;
        padding: 16px; min-width: 160px; flex: 1; }
.card label { font-size: 11px; color: #888; text-transform: uppercase; }
.card .val { font-size: 22px; color: #00ff88; margin-top: 4px; }
.card .unit { font-size: 11px; color: #555; }
#log { height: 320px; overflow-y: auto; background: #111; padding: 10px;
       font-size: 11px; border: 1px solid #222; border-radius: 4px; }
.log-entry { color: #ccc; padding: 2px 0; border-bottom: 1px solid #1a1a1a; }
.log-entry .proto { color: #00ff88; font-weight: bold; }
.log-entry .freq { color: #00ccff; }
.log-entry .pwr { color: #ff8800; }
.status { color: #555; font-size: 11px; margin-top: 8px; }
#status { color: #ff4444; }
.connected { color: #00ff88 !important; }
</style>
</head>
<body>
<h1>&#128225; RF IMPERIUM Dashboard</h1>
<div class="cards">
  <div class="card"><label>Czestotliwosc</label>
    <div class="val" id="freq">--</div><div class="unit">MHz</div></div>
  <div class="card"><label>Moc</label>
    <div class="val" id="power">--</div><div class="unit">dBm</div></div>
  <div class="card"><label>Protokol</label>
    <div class="val" id="protocol" style="font-size:16px">--</div></div>
  <div class="card"><label>Sygnaly</label>
    <div class="val" id="count">0</div><div class="unit">razem</div></div>
  <div class="card"><label>Sample Rate</label>
    <div class="val" id="srate">--</div><div class="unit">Msps</div></div>
</div>
<h3 style="margin-bottom:8px;color:#888">Live Feed</h3>
<div id="log"></div>
<p class="status">Status: <span id="status">Laczenie...</span></p>
<script>
let count = 0;
function connect() {
  const ws = new WebSocket('ws://' + location.host + '/ws');
  ws.onopen = () => {
    document.getElementById('status').textContent = 'Polaczono';
    document.getElementById('status').className = 'connected';
  };
  ws.onclose = () => {
    document.getElementById('status').textContent = 'Rozlaczono — ponawianie...';
    document.getElementById('status').className = '';
    setTimeout(connect, 2000);
  };
  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.freq) document.getElementById('freq').textContent = d.freq;
    if (d.power) document.getElementById('power').textContent = d.power;
    if (d.protocol) document.getElementById('protocol').textContent = d.protocol;
    if (d.srate) document.getElementById('srate').textContent = d.srate;
    if (d.signal) {
      count++;
      document.getElementById('count').textContent = count;
      const log = document.getElementById('log');
      const div = document.createElement('div');
      div.className = 'log-entry';
      div.innerHTML = d.signal;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
      if (log.children.length > 200) log.removeChild(log.children[0]);
    }
  };
}
connect();
</script>
</body>
</html>"""


class DashboardServer:
    def __init__(self, port=8765):
        self.port = port
        self.running = False
        self._loop = None
        self._thread = None
        self._clients: set = set()
        self._latest: dict = {}

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        try:
            from aiohttp import web
        except ImportError:
            print("aiohttp not installed — dashboard disabled")
            return

        app = web.Application()
        app.router.add_get("/", self._index)
        app.router.add_get("/ws", self._ws_handler)
        app.router.add_get("/api/status", self._api_status)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        print(f"[Dashboard] http://localhost:{self.port}")
        while self.running:
            await asyncio.sleep(1)
        await runner.cleanup()

    async def _index(self, request):
        from aiohttp import web
        return web.Response(text=DASHBOARD_HTML, content_type="text/html")

    async def _ws_handler(self, request):
        from aiohttp import web
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._clients.add(ws)
        try:
            async for _ in ws:
                pass
        finally:
            self._clients.discard(ws)
        return ws

    async def _api_status(self, request):
        from aiohttp import web
        return web.json_response(self._latest)

    def broadcast(self, data: dict):
        self._latest.update(data)
        if not self._loop or not self._clients:
            return
        msg = json.dumps(data)
        for ws in list(self._clients):
            asyncio.run_coroutine_threadsafe(ws.send_str(msg), self._loop)

    def push_signal(self, freq_hz: float, power_dbm: float,
                    protocol: str, decoded=""):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        signal_html = (
            f'<span style="color:#555">[{ts}]</span> '
            f'<span class="freq">{freq_hz/1e6:.4f} MHz</span> '
            f'<span class="proto">{protocol}</span> '
            f'<span class="pwr">{power_dbm:.1f} dBm</span> '
            f'{decoded[:60]}'
        )
        self.broadcast({
            "freq": f"{freq_hz/1e6:.4f}",
            "power": f"{power_dbm:.1f}",
            "protocol": protocol,
            "signal": signal_html,
        })

    def stop(self):
        self.running = False
