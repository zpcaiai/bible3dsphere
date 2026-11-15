"""Read only the caller's allowlisted health-stage records from HF's SSE logs.

HF_TOKEN stays in the CI environment. Unrelated server logs are neither printed
nor written. Five seconds is an absolute diagnostic collection window, never a
replacement for the health probe's own five-second deadline.
"""
from collections import Counter
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
import uuid

FIELDS = frozenset(('kind', 'request_id', 'phase', 'event', 'pid', 'thread_id',
                    'epoch_ns', 'monotonic_ns', 'elapsed_ms', 'status',
                    'error_type', 'path', 'endpoint_sha256', 'load1'))
PHASES = frozenset(('request', 'pool.acquire', 'pool.discard', 'db.connect', 'db.pre_ping',
                    'db.query', 'db.retry_wait', 'db.rollback', 'pool.release'))


def select_records(payload, wanted, depth=0):
    """Parse provider envelopes, retaining exact flat diagnostic JSON only."""
    if depth > 8:
        return []
    if isinstance(payload, dict):
        return [row for value in payload.values()
                for row in select_records(value, wanted, depth + 1)]
    if isinstance(payload, list):
        return [row for value in payload for row in select_records(value, wanted, depth + 1)]
    if not isinstance(payload, str) or len(payload) > 1024 * 1024:
        return []
    text = payload.removeprefix('data:').strip()
    if text.startswith(('{', '[')):
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, (dict, list)) and not (
                isinstance(decoded, dict) and decoded.get('kind') == 'readiness_stage'):
            return select_records(decoded, wanted, depth + 1)
    start = text.find('{')
    if start < 0:
        return []
    try:
        obj, end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError:
        return []
    if not isinstance(obj, dict) or obj.get('kind') != 'readiness_stage':
        return []
    if obj.get('request_id') not in wanted or not set(obj) <= FIELDS:
        return []
    if obj.get('phase') not in PHASES or obj.get('event') not in ('start', 'end', 'error'):
        return []
    if obj.get('path') not in (None, '/health/live', '/health/ready', '/api/health/db'):
        return []
    if any(not isinstance(obj.get(k), int) or isinstance(obj.get(k), bool) or obj[k] <= 0
           for k in ('pid', 'thread_id', 'epoch_ns', 'monotonic_ns')):
        return []
    if any(not isinstance(value, (str, int, float, type(None))) for value in obj.values()):
        return []
    if text[end:].strip():
        return []
    return [{'record': obj, 'raw_record': text[start:end]}]


class CollectionWindowEnded(TimeoutError):
    """An explicitly bounded SSE observation window."""


def capture(wanted, required_id):
    assert required_id in wanted
    assert all(str(uuid.UUID(value)) == value for value in wanted)
    token = os.environ.get('HF_TOKEN', '')
    if not token:
        print(json.dumps({'status': 'NOT_RUN', 'reason': 'EXISTING_HF_TOKEN_UNAVAILABLE'}))
        return 1
    request = urllib.request.Request(
        'https://huggingface.co/api/spaces/StephenZao/biblesphere/logs/run',
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'text/event-stream'})
    started = time.monotonic()
    rows = []
    seen = set()
    http_status = None
    count = 0
    error_type = None
    def deadline(_signum, _frame):
        raise CollectionWindowEnded()
    old = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 5)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            http_status = response.status
            assert http_status == 200
            while count < 1024 * 1024:
                line = response.readline(65536)
                if not line:
                    break
                count += len(line)
                for row in select_records(line.decode('utf-8', errors='replace'), wanted):
                    key = row['raw_record']
                    if key not in seen:
                        seen.add(key)
                        rows.append(row)
                ended = {r['record']['request_id'] for r in rows
                         if r['record']['phase'] == 'request' and r['record']['event'] in ('end', 'error')}
                if ended == wanted:
                    break
    except urllib.error.HTTPError as exc:
        http_status = exc.code
        error_type = type(exc).__name__
    except Exception as exc:
        error_type = type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    counts = Counter(r['record']['request_id'] for r in rows)
    out = {'pid': os.getpid(), 'http_status': http_status, 'windowSeconds': 5,
           'elapsedSeconds': time.monotonic() - started, 'bytesInspectedNotRetained': count,
           'error_type': error_type, 'requestedIDs': sorted(wanted),
           'matchingCounts': dict(counts), 'selected': rows,
           'scope': 'Only allowlisted own health-stage JSON; unrelated logs and credentials excluded'}
    print(json.dumps(out, sort_keys=True), flush=True)
    # This validates capture only; it never declares the timed-out probe passed.
    return 0 if http_status == 200 and counts[required_id] else 1


if __name__ == '__main__':
    raise SystemExit(capture(set(sys.argv[1].split(',')), sys.argv[2]))
