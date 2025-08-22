# utils/logging_utils.py
def log_mem(tag):
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    print(f"🧠 [MEM] {tag}: {line.strip()}")
                    return
    except Exception:
        pass
