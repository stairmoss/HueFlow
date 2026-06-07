import psutil
import os
import json
import time

def check_memory():
    process = psutil.Process(os.getpid())
    # memory_info().rss is resident set size in bytes
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"Current Memory Usage: {mem_mb:.2f} MB")
    return mem_mb

print("Starting memory check script...")
check_memory()

# Delay import to see the memory jump from the library vs the model
print("\nImporting AI engine...")
from core.inference import ColorGraderInference
check_memory()

print("\nInitializing Model...")
grader = ColorGraderInference()
check_memory()

print("\nRunning inference...")
start = time.time()
result = grader.analyze_image("dummy.jpg")
print("Inference time: ", time.time() - start)
print("Result:", json.dumps(result, indent=2))
check_memory()

print("\nDone.")
# 