#!/bin/bash
cd /home/admin/server/memex
echo "=== Memex v2.2 inditas ==="
pkill -f memex_gateway.py 2>/dev/null && echo "Regi szerver leallitva" || echo "Nem futott szerver"
sleep 1
if [ ! -f venv/bin/python ]; then
    ln -sf $(which python3) venv/bin/python
fi
# .env betoltes ha letezik
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo ".env betoltve"
fi
nohup venv/bin/python core/memex_gateway.py --mod api --port 8765 >> logs/server.log 2>&1 &
echo "Szerver inditva PID $!"
sleep 3
curl -s http://localhost:8765/info | python3 -c "import sys,json;d=json.load(sys.stdin);print('auto:',d.get('auto'),'claude:',d.get('claude'),'gemini:',d.get('gemini'))"
echo "=== http://192.168.0.64:8765 ==="
