#!/bin/zsh
# Persistent isolated acceptance only. Never touches the normal database/.env.
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_OUT="$TASK_ROOT/evidence/phase2_admin_e2e"
mkdir -p "$TASK_OUT"
cd "$TASK_ROOT"

# --restart stops only processes whose recorded PID and command match this harness.
if [[ "${1:-}" == "--restart" ]]; then
  for task_role in backend frontend; do
    task_pid_file="$TASK_OUT/$task_role.pid"
    if [[ -f "$task_pid_file" ]]; then
      task_pid="$(cat "$task_pid_file")"
      if kill -0 "$task_pid" 2>/dev/null; then
        task_command="$(ps -p "$task_pid" -o command=)"
        if [[ "$task_role" == backend && "$task_command" == *phase2_admin_e2e_test_server.py* ]] || [[ "$task_role" == frontend && "$task_command" == *"vite --host 127.0.0.1 --port 5177 --strictPort"* ]]; then
          kill "$task_pid"
        else
          print -u2 "Recorded $task_role process does not belong to this acceptance harness. Nothing was stopped."
          exit 1
        fi
      fi
    fi
  done
  sleep 1
fi

"$TASK_ROOT/backend/.venv/bin/python" - <<'PY'
import json, os, socket, subprocess, time, urllib.request
from pathlib import Path
root = Path.cwd()
out = root / 'evidence/phase2_admin_e2e'
services = [
    ('backend', 8004, [str(root/'backend/.venv/bin/python'), str(root/'scripts/phase2_admin_e2e_test_server.py')], root, {}),
    ('frontend', 5177, [str(root/'frontend/node_modules/.bin/vite'), '--host', '127.0.0.1', '--port', '5177', '--strictPort'], root/'frontend', {'VITE_API_TARGET': 'http://127.0.0.1:8004'}),
]
for role, port, command, cwd, extra_env in services:
    probe = socket.socket()
    occupied = probe.connect_ex(('127.0.0.1', port)) == 0
    probe.close()
    if occupied:
        pid_path = out/f'{role}.pid'
        valid = False
        if pid_path.exists():
            pid = pid_path.read_text().strip()
            process = subprocess.run(['ps', '-p', pid, '-o', 'command='], text=True, capture_output=True).stdout
            valid = ('phase2_admin_e2e_test_server.py' in process if role == 'backend' else 'vite --host 127.0.0.1 --port 5177 --strictPort' in process)
        if not valid:
            raise SystemExit(f'Port {port} is occupied by another task. No process was stopped.')
        continue
    env = os.environ.copy()
    env.update(extra_env)
    log = open(out/f'{role}.log', 'ab')
    child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (out/f'{role}.pid').write_text(str(child.pid))
    log.close()

for _ in range(40):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8004/api/health', timeout=1) as response:
            if response.headers.get('X-SANZO-Test-Harness') != 'phase2_admin_e2e':
                raise SystemExit('Backend identity does not match this acceptance harness.')
            health = json.load(response)
        with urllib.request.urlopen('http://127.0.0.1:5177/api/health', timeout=1) as response:
            if response.headers.get('X-SANZO-Test-Harness') != 'phase2_admin_e2e':
                raise SystemExit('Frontend proxy does not match this acceptance harness.')
            frontend_health = json.load(response)
        if health != frontend_health:
            raise SystemExit('Backend and frontend health do not match.')
        (out/'health.json').write_text(json.dumps(health, ensure_ascii=False, indent=2))
        print('Isolated Admin: http://localhost:5177/admin')
        print('Customer: http://localhost:5177/  |  Staff: http://localhost:5177/staff')
        print('TEST provider; actual SDK and business Tools. No paid AI/TTS.')
        break
    except (OSError, ValueError):
        time.sleep(.25)
else:
    raise SystemExit('Acceptance services did not become ready. Check isolated backend.log/frontend.log.')
PY
