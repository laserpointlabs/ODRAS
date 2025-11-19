#!/bin/bash
# Complete demo startup script - starts everything needed

set -e

echo "🔬 Starting Complete ODRAS Living Lattice Demo"
echo "================================================"

cd "$(dirname "$0")/../.."

# Check ODRAS is running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "❌ ODRAS is not running!"
    echo "   Start it with: ./odras.sh start"
    exit 1
fi
echo "✅ ODRAS is running"

# Clean up old processes
echo ""
echo "🧹 Cleaning up old processes..."
pkill -9 -f visualization_server 2>/dev/null || true
pkill -9 -f "http.server.*8082" 2>/dev/null || true
sleep 1

# Start HTTP server
echo ""
echo "🌐 Starting HTTP server on port 8082..."
cd scripts/demo
python3 -m http.server 8082 --directory static > /tmp/demo_http.log 2>&1 &
HTTP_PID=$!
sleep 2

if ps -p $HTTP_PID > /dev/null; then
    echo "✅ HTTP server started (PID: $HTTP_PID)"
else
    echo "❌ HTTP server failed to start"
    cat /tmp/demo_http.log
    exit 1
fi

# Start WebSocket server
echo ""
echo "📡 Starting WebSocket server on port 8081..."
python visualization_server.py --ws-port 8081 --websocket-only > /tmp/demo_ws.log 2>&1 &
WS_PID=$!
sleep 3

if ps -p $WS_PID > /dev/null; then
    echo "✅ WebSocket server started (PID: $WS_PID)"
else
    echo "❌ WebSocket server failed to start"
    cat /tmp/demo_ws.log
    kill $HTTP_PID 2>/dev/null || true
    exit 1
fi

# Bootstrap projects
echo ""
echo "🏗️  Bootstrapping projects from requirements..."
cd ../..
python scripts/demo/demo_bootstrap_flow.py
BOOTSTRAP_SUCCESS=$?

echo ""
echo "================================================"
if [ $BOOTSTRAP_SUCCESS -eq 0 ]; then
    echo "✅ DEMO READY!"
    echo "================================================"
    echo ""
    echo "📋 Open in browser:"
    echo "   http://localhost:8082/lattice_demo.html"
    echo ""
    echo "🛑 To stop servers:"
    echo "   kill $HTTP_PID $WS_PID"
    echo ""
    echo "Press Ctrl+C to stop servers..."
    
    # Wait for interrupt
    trap "echo ''; echo '🛑 Stopping servers...'; kill $HTTP_PID $WS_PID 2>/dev/null; exit" INT TERM
    wait
else
    echo "❌ Bootstrap failed - check errors above"
    kill $HTTP_PID $WS_PID 2>/dev/null || true
    exit 1
fi
