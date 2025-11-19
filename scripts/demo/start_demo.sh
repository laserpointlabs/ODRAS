#!/bin/bash
# Simple script to start the living lattice demo

echo "🔬 Starting ODRAS Living Lattice Demo"
echo "========================================"

# Check if ODRAS is running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "❌ ODRAS is not running on port 8000"
    echo "   Please start ODRAS first: ./odras.sh start"
    exit 1
fi

echo "✅ ODRAS is running"

# Find available port for HTTP server
HTTP_PORT=8082
while netstat -tuln | grep -q ":$HTTP_PORT "; do
    HTTP_PORT=$((HTTP_PORT + 1))
done

WS_PORT=8081
while netstat -tuln | grep -q ":$WS_PORT "; do
    WS_PORT=$((WS_PORT + 1))
done

echo "📡 Using ports: HTTP=$HTTP_PORT, WebSocket=$WS_PORT"

# Start HTTP server for static files in background
cd "$(dirname "$0")"
python3 -m http.server $HTTP_PORT --directory static > /tmp/demo_http.log 2>&1 &
HTTP_PID=$!
echo "✅ HTTP server started (PID: $HTTP_PID) on port $HTTP_PORT"

# Start WebSocket server
echo "🚀 Starting WebSocket server..."
python3 visualization_server.py --ws-port $WS_PORT --websocket-only > /tmp/demo_ws.log 2>&1 &
WS_PID=$!
sleep 2

if ps -p $WS_PID > /dev/null; then
    echo "✅ WebSocket server started (PID: $WS_PID) on port $WS_PORT"
else
    echo "❌ WebSocket server failed to start"
    cat /tmp/demo_ws.log
    kill $HTTP_PID 2>/dev/null
    exit 1
fi

# Update HTML file with correct WebSocket URL
sed -i "s|ws://localhost:8081|ws://localhost:$WS_PORT|g" static/lattice_demo.html

echo ""
echo "✅ Demo servers are running!"
echo ""
echo "📋 Next steps:"
echo "   1. Open browser to: http://localhost:$HTTP_PORT/lattice_demo.html"
echo "   2. Bootstrap projects: python scripts/demo/test_demo_simple.py"
echo ""
echo "To stop servers:"
echo "   kill $HTTP_PID $WS_PID"
echo ""
echo "Press Ctrl+C to stop..."

# Wait for interrupt
trap "kill $HTTP_PID $WS_PID 2>/dev/null; exit" INT TERM
wait
