#!/usr/bin/env python3
"""
External Task Worker Runner for ODRAS
Starts the external task worker to process Camunda tasks.
"""

import sys
import os
import logging
import signal
import time

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings
from services.external_task_worker import ExternalTaskWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('external_task_worker.log')
    ]
)

logger = logging.getLogger(__name__)

# Global worker instance for signal handling
worker = None


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global worker
    logger.info(f"Received signal {signum}, shutting down worker...")
    if worker:
        worker.stop()
    sys.exit(0)


def check_camunda_connection(camunda_url: str) -> bool:
    """Check if Camunda is accessible."""
    import requests
    try:
        response = requests.get(f"{camunda_url}/engine", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    """Main function to start the external task worker."""
    global worker
    
    print("🚀 ODRAS External Task Worker")
    print("=" * 40)
    
    # Load settings
    settings = Settings()
    camunda_url = "http://localhost:8080/engine-rest"
    
    # Check Camunda connection
    print("🔍 Checking Camunda connection...")
    if not check_camunda_connection(camunda_url):
        print(f"❌ Cannot connect to Camunda at {camunda_url}")
        print("   Make sure Camunda is running with: docker compose up -d")
        sys.exit(1)
    
    print(f"✅ Connected to Camunda at {camunda_url}")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start worker
    try:
        worker = ExternalTaskWorker(settings)
        
        print("🎯 External Task Worker Topics:")
        for topic in worker.task_handlers.keys():
            print(f"   - {topic}")
        
        print(f"\n🔄 Starting worker with ID: {worker.worker_id}")
        print("   Press Ctrl+C to stop\n")
        
        # Start the worker (this will block)
        worker.start()
        
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        sys.exit(1)
    finally:
        if worker:
            worker.stop()
        print("\n👋 External Task Worker stopped")


if __name__ == "__main__":
    main()




