"""Local educational ride HMI with optional automatic 500 ms scan cycle."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Lock, Thread, Event
from time import monotonic
from urllib.parse import urlparse
import json
from ride_sim import RideStation

HOST, PORT = '127.0.0.1', 8000
ROOT = Path(__file__).resolve().parent
station = RideStation()
lock = Lock()
auto_enabled = False
scan_interval_ms = 500
stop_event = Event()
ton_preset_ms = 2000
# Instruction-monitor TON: runs on controller scans; observational only.
ton_elapsed_ms = 0
ton_done = False
ton_last_scan = None

def monitored_scan(**commands):
    global ton_elapsed_ms, ton_done, ton_last_scan
    now = monotonic()
    # TON input is true while controller remains AWAY. Evaluate pre-scan
    # and post-scan; reset whenever the resulting state is not AWAY.
    previous = ton_last_scan
    station.tick(**commands)
    if station.state == 'AWAY':
        if previous is not None:
            ton_elapsed_ms = min(ton_preset_ms, ton_elapsed_ms + max(0, round((now - previous) * 1000)))
        ton_last_scan = now
        ton_done = ton_elapsed_ms >= ton_preset_ms
    else:
        ton_elapsed_ms = 0
        ton_done = False
        ton_last_scan = None

def instruction_snapshot():
    i = {key: getattr(station, key) for key in INPUTS}
    healthy = all(i[k] for k in ('estop_healthy','plc_comms_ok','sensor_consistent','drive_ready'))
    permissives = station.permissives()
    # Monitor-only instructions, NOT an executable ladder runtime.
    return {'instructions': [
      {'rung': 0, 'type':'XIC','tag':'plc_comms_ok','value':i['plc_comms_ok'],'condition':i['plc_comms_ok']},
      {'rung': 0, 'type':'XIO','tag':'plc_comms_ok','value':i['plc_comms_ok'],'condition':not i['plc_comms_ok']},
      {'rung': 0, 'type':'OTE','tag':'DIAGNOSTICS_OK','value':healthy,'condition':healthy},
      {'rung': 1, 'type':'OTE','tag':'DISPATCH_ENABLE','value':permissives and station.state=='READY','condition':permissives and station.state=='READY'},
      {'rung': 2, 'type':'OTL','tag':'ALARM_LATCH','value':bool(station.alarms),'condition':bool(station.faults())},
      {'rung': 3, 'type':'OTU','tag':'ALARM_LATCH','value':bool(station.alarms),'condition':not station.alarms and not station.faults()},
      {'rung': 4, 'type':'TON','tag':'AWAY_DWELL','value':ton_done,'condition':station.state=='AWAY',
       'preset_ms':ton_preset_ms,'accumulated_ms':ton_elapsed_ms,'done':ton_done}
    ], 'ton':{'en':station.state=='AWAY','tt':station.state=='AWAY' and not ton_done,
             'dn':ton_done,'acc_ms':ton_elapsed_ms,'pre_ms':ton_preset_ms},
      'note':'Instruction monitor is derived from Python state. OTL/OTU visualize existing alarm latch/reset; TON is informational and does not control dispatch or arrival.'}

INPUTS = ('train_present', 'gate_closed', 'restraints_locked', 'block_clear',
          'drive_ready', 'estop_healthy', 'plc_comms_ok', 'sensor_consistent')

def snapshot():
    return {'inputs': {key: getattr(station, key) for key in INPUTS},
            'state': station.state, 'alarms': list(station.alarms),
            'active_faults': station.faults(),
            'ticks': station.tick_count, 'log': list(station.event_log[-100:]),
            'permissives': station.permissives(),
            'dispatch_permitted': station.permissives() and station.state == 'READY',
            'auto_enabled': auto_enabled, 'scan_interval_ms': scan_interval_ms,
            'ladder_monitor': instruction_snapshot()}

def scan_worker():
    while not stop_event.wait(scan_interval_ms / 1000):
        with lock:
            if auto_enabled:
                monitored_scan()

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/status':
            with lock:
                return self.send_json(snapshot())
        if path in ('/', '/dashboard.html'):
            body = (ROOT / 'dashboard.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return self.wfile.write(body)
        self.send_error(404)

    def do_POST(self):
        global station, auto_enabled, ton_elapsed_ms, ton_done, ton_last_scan
        path = urlparse(self.path).path
        if path not in ('/api/scan', '/api/dispatch', '/api/reset', '/api/arrive',
                        '/api/input', '/api/restart', '/api/auto/start', '/api/auto/stop'):
            return self.send_json({'error': 'Unknown endpoint'}, 404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 4096:
                return self.send_json({'error': 'Invalid request length'}, 413)
            payload = json.loads(self.rfile.read(length)) if length else {}
            if not isinstance(payload, dict):
                return self.send_json({'error': 'Expected JSON object'}, 400)
        except (ValueError, UnicodeDecodeError):
            return self.send_json({'error': 'Invalid JSON'}, 400)
        with lock:
            if path == '/api/input':
                name, value = payload.get('name'), payload.get('value')
                if name not in INPUTS or type(value) is not bool:
                    return self.send_json({'error': 'Invalid input name or boolean value'}, 400)
                station.set_input(name, value)
            elif path == '/api/restart':
                auto_enabled = False
                station = RideStation()
                ton_elapsed_ms = 0; ton_done = False; ton_last_scan = None
            elif path == '/api/auto/start':
                auto_enabled = True
            elif path == '/api/auto/stop':
                auto_enabled = False
            elif path == '/api/scan':
                if auto_enabled:
                    return self.send_json({'error': 'Stop AUTO mode before manual SCAN'}, 409)
                monitored_scan()
            else:
                monitored_scan(dispatch=path == '/api/dispatch',
                             reset=path == '/api/reset', arrive=path == '/api/arrive')
            return self.send_json(snapshot())

if __name__ == '__main__':
    Thread(target=scan_worker, daemon=True).start()
    print(f'Ride HMI at http://{HOST}:{PORT}/dashboard.html')
    print('Automatic scanning: 500 ms; starts in MANUAL mode. Ctrl+C to stop.')
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    finally:
        stop_event.set()
