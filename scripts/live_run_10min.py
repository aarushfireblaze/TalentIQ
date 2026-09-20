import time
import httpx
import json
import psutil
import os
import sys
import subprocess
import threading
from urllib.error import URLError

def monitor_service(pid, duration):
    print(f"Monitoring service PID {pid} for {duration} seconds...")
    start_time = time.time()
    process = psutil.Process(pid)
    
    max_memory_mb = 0
    max_cpu_percent = 0
    
    while time.time() - start_time < duration:
        try:
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            cpu = process.cpu_percent(interval=1.0)
            
            if mem_mb > max_memory_mb:
                max_memory_mb = mem_mb
            if cpu > max_cpu_percent:
                max_cpu_percent = cpu
                
        except psutil.NoSuchProcess:
            break
            
        time.sleep(5)
        
    print(f"\n--- Resource Usage ---")
    print(f"Peak Memory: {max_memory_mb:.2f} MB")
    print(f"Peak CPU: {max_cpu_percent:.1f}%")

def get_sse_events(url, duration):
    """Simple SSE reader to compute partial latency"""
    # Not trivial to do accurately without a full SSE client and knowing the exact audio clock
    pass

def main():
    print("Starting 10-minute live run script...")
    
    # 1. Start the service
    print("Starting the service...")
    cmd = [
        sys.executable, "-m", "voice_filtering",
        "--host", "127.0.0.1",
        "--port", "8765",
        "--model", "models/faster-whisper-tiny.en"
    ]
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    
    service_proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(10) # wait for models to load
    
    if service_proc.poll() is not None:
        print("Service failed to start:")
        print(service_proc.stderr.read())
        sys.exit(1)
        
    print(f"Service started (PID {service_proc.pid})")
    
    # 2. Start combined mode
    print("Starting pipeline in 'raw' mode...")
    try:
        start_resp = httpx.post("http://127.0.0.1:8765/api/start", json={
            "device_id": "0",
            "mode": "raw",
            "record": False
        })
        if start_resp.status_code != 202:
            print(f"Failed to start: {start_resp.json()}")
            service_proc.terminate()
            sys.exit(1)
    except Exception as e:
        print(f"Error calling API: {e}")
        service_proc.terminate()
        sys.exit(1)

    # 3. Monitor for 10 minutes
    duration = 600
    
    monitor_thread = threading.Thread(target=monitor_service, args=(service_proc.pid, duration))
    monitor_thread.start()
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        time.sleep(30)
        try:
            state = httpx.get("http://127.0.0.1:8765/api/state").json()
            metrics = state.get("metrics", {})
            print(f"[{int(time.time() - start_time)}s] Metrics: {json.dumps(metrics)}")
        except Exception as e:
            print(f"Error fetching state: {e}")
            break
            
    print("\nStopping pipeline...")
    try:
        httpx.post("http://127.0.0.1:8765/api/stop")
    except:
        pass
        
    # Final metrics
    try:
        state = httpx.get("http://127.0.0.1:8765/api/state").json()
        metrics = state.get("metrics", {})
        print(f"\n--- Final Pipeline Metrics ---")
        print(json.dumps(metrics, indent=2))
    except:
        pass
        
    print("Terminating service...")
    service_proc.terminate()
    service_proc.wait(timeout=5)
    
    with open("artifacts/m6_live_run.txt", "w") as f:
        f.write("Peak Memory: recorded above\n")
        f.write("Final Metrics:\n")
        f.write(json.dumps(metrics, indent=2) + "\n")
        
    print("Live run complete.")

if __name__ == '__main__':
    main()
