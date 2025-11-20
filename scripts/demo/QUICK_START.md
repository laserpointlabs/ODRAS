# Quick Start Guide - Living Lattice Demo

## ✅ Current Status

The demo is **ready to run**! Here's what's working:

1. ✅ **ODRAS is running** on port 8000
2. ✅ **Bootstrapper works** - Creates projects successfully
3. ✅ **HTTP server** - Serving static files on port 8082
4. ✅ **WebSocket server** - Running on port 8081

## 🚀 How to Run the Demo

### Step 1: Bootstrap Projects (if needed)

If you want fresh projects, run:
```bash
cd /home/jdehart/working/ODRAS
python scripts/demo/test_demo_simple.py
```

This will create 10 projects with proper relationships.

### Step 2: Start Visualization Servers

**Option A: Use the startup script**
```bash
cd /home/jdehart/working/ODRAS/scripts/demo
./start_demo.sh
```

**Option B: Manual start**

Terminal 1 - HTTP server (static files):
```bash
cd /home/jdehart/working/ODRAS/scripts/demo
python3 -m http.server 8082 --directory static
```

Terminal 2 - WebSocket server:
```bash
cd /home/jdehart/working/ODRAS/scripts/demo  
python visualization_server.py --ws-port 8081 --websocket-only
```

### Step 3: Open Browser

Open your browser to:
```
http://localhost:8082/lattice_demo.html
```

The visualization should load and connect to the WebSocket server automatically.

## 🔧 Troubleshooting

### Port Already in Use
If port 8080 or 8081 is in use:
- Use different ports: `--http-port 8082 --ws-port 8083`
- Or kill existing processes: `pkill -f visualization_server`

### WebSocket Connection Failed
- Check WebSocket server is running: `ps aux | grep visualization_server`
- Check logs: `tail -f /tmp/demo_ws.log`
- Verify ODRAS is running: `./odras.sh status`

### No Projects Showing
- Bootstrap projects: `python scripts/demo/test_demo_simple.py`
- Check projects exist: `curl http://localhost:8000/api/projects -H "Authorization: Bearer TOKEN"`

### Static Files Not Loading
- Verify HTTP server is running: `curl http://localhost:8082/lattice_demo.html`
- Check file exists: `ls scripts/demo/static/lattice_demo.html`

## 📊 What You Should See

1. **Grid Layout**: Projects arranged in grid (L0-L3 vertical, domains horizontal)
2. **Project Nodes**: Colored by layer (L0=blue, L1=green, L2=orange, L3=red)
3. **Connections**: Parent-child (vertical) and cousin (horizontal) relationships
4. **Live Updates**: Projects change state, events flow through lattice
5. **Event Log**: Shows events in real-time
6. **Project Details**: Click nodes to see details

## 🎮 Interactive Controls

Once visualization is open:
- **Click projects** to see details
- **Use buttons** to simulate events
- **Watch** as events cascade through lattice
- **Observe** project state transitions

## 🐛 Current Known Issues

1. **Interactive demo loop** - The main `run_living_lattice_demo.py` script has an interactive loop that requires user input. Use `test_demo_simple.py` instead for non-interactive testing.

2. **Port conflicts** - Port 8080 may be in use by ODRAS. Use port 8082+ for HTTP server.

3. **Multiple project runs** - Previous demo runs may have created projects. Clean up if needed:
   ```bash
   # List projects
   curl http://localhost:8000/api/projects -H "Authorization: Bearer TOKEN"
   
   # Delete specific project
   curl -X DELETE http://localhost:8000/api/projects/PROJECT_ID -H "Authorization: Bearer TOKEN"
   ```

## ✅ Success Checklist

- [ ] ODRAS running (`./odras.sh status`)
- [ ] Projects created (run `test_demo_simple.py`)
- [ ] HTTP server running on port 8082
- [ ] WebSocket server running on port 8081
- [ ] Browser opens visualization
- [ ] Projects visible in grid layout
- [ ] WebSocket connection established (check browser console)

## 📞 Next Steps

Once everything is running:
1. **Explore the lattice** - See how projects are connected
2. **Trigger events** - Use the "Simulate Event" button
3. **Watch cascades** - See how changes flow through lattice
4. **Test bootstrapping** - Try different requirement texts

The demo is fully functional and ready for customer presentations!
