import os
import time
from pymemcache.client import base

# Connect to the Memcached container
host = os.getenv('MEMCACHED_HOST', 'memcached')
client = base.Client((host, 11211))
filename = '/data/all_bitcoin_addresses.txt'

def load_data():
    print(f"--- STARTING BIG DATA LOAD from {filename} ---")
    
    if not os.path.exists(filename):
        print(f"ERROR: {filename} not found inside container!")
        return

    count = 0
    start_time = time.time()
    batch_data = {}
    BATCH_SIZE = 5000  # Smaller batch size for stability

    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Clean the line (remove spaces/newlines)
                address = line.strip()
                
                # Skip empty lines or headers
                if len(address) < 25: 
                    continue

                # Prepare for DB (Key=Address, Value='1')
                batch_data[address] = '1'
                count += 1

                # Upload batch every 5000 lines
                if count % BATCH_SIZE == 0:
                    try:
                        client.set_multi(batch_data)
                        batch_data = {} # Clear memory
                        # Print progress every 100k lines to keep logs clean
                        if count % 100000 == 0:
                            print(f"Loaded {count:,.0f} addresses...", flush=True)
                    except Exception as e:
                        print(f"Retrying connection... ({e})")
                        time.sleep(1)

            # Upload leftovers
            if batch_data:
                client.set_multi(batch_data)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

    duration = time.time() - start_time
    print(f"\n--- SUCCESS: Loaded {count:,.0f} addresses in {duration:.1f}s ---")

if __name__ == '__main__':
    # Give Memcached 10 seconds to wake up
    print("Waiting for database...")
    time.sleep(10)
    load_data()
