import os
import hashlib
import ecdsa
import multiprocessing
import time
import ctypes
from datetime import datetime
from pymemcache.client import base

# --- Configuration ---
host = os.getenv('MEMCACHED_HOST', 'localhost')
MAX_PROCESSES = multiprocessing.cpu_count() or 1
BATCH_SIZE = 1000  # Adjusted for cleaner math, can be higher
MEMCACHED_SERVER = ('localhost', 11211)
B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(data: bytes) -> str:
    n = int.from_bytes(data, 'big')
    b58_string = ''
    while n > 0:
        n, remainder = divmod(n, 58)
        b58_string = B58_ALPHABET[remainder] + b58_string
    pad = 0
    for b in data:
        if b == 0: pad += 1
        else: break
    return B58_ALPHABET[0] * pad + b58_string

def get_address_from_public_key(public_key: bytes) -> str:
    sha256_hash = hashlib.sha256(public_key).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    versioned_hash = b'\x00' + ripemd160_hash
    checksum = hashlib.sha256(hashlib.sha256(versioned_hash).digest()).digest()[:4]
    return base58_encode(versioned_hash + checksum)

def generate_key_batch(batch_size: int) -> list:
    keys = []
    for _ in range(batch_size):
        private_key_bytes = os.urandom(32)
        hex_private_key = private_key_bytes.hex()

        # Derive Public Keys
        signing_key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
        verifying_key = signing_key.get_verifying_key()
        
        # Optimization: Get both raw points once
        public_key_uncompressed = b'\x04' + verifying_key.to_string('uncompressed')[1:]
        public_key_compressed = verifying_key.to_string('compressed')

        address_uncompressed = get_address_from_public_key(public_key_uncompressed)
        address_compressed = get_address_from_public_key(public_key_compressed)

        # Generate WIF (Compressed version by default)
        wif_payload = b'\x80' + private_key_bytes + b'\x01'
        checksum = hashlib.sha256(hashlib.sha256(wif_payload).digest()).digest()[:4]
        wif = base58_encode(wif_payload + checksum)
        
        keys.append([hex_private_key, wif, address_uncompressed, address_compressed])
    return keys

def worker_main(counter):
    """
    Main loop for worker process.
    Note: Client is initialized HERE to avoid socket sharing issues.
    """
    # 1. Initialize DB connection inside the process
    try:
        client = base.Client(MEMCACHED_SERVER)
    except Exception as e:
        print(f"Process {os.getpid()} failed to connect: {e}")
        return

    while True:
        key_batch = generate_key_batch(BATCH_SIZE)
        
        # Create map
        address_map = {}
        for k in key_batch:
            address_map[k[2]] = k # Uncompressed
            address_map[k[3]] = k # Compressed
        
        # Check DB
        try:
            found_keys = client.get_multi(address_map.keys())
            
            if found_keys:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{now}] --- HIT FOUND ---")
                with open('plutus.txt', 'a') as file:
                    for found_addr in found_keys:
                        data = address_map[found_addr]
                        output = (f"Found: {found_addr}\nPriv: {data[0]}\nWIF: {data[1]}\n\n")
                        print(output)
                        file.write(output)
        except Exception:
            # Reconnect logic could go here
            pass
            
        # Update the shared counter
        with counter.get_lock():
            counter.value += BATCH_SIZE

if __name__ == '__main__':
    print(f"--- SCROO (Fixed) ---")
    print(f"Workers: {MAX_PROCESSES}")
    
    # Shared counter for accurate stats
    total_counter = multiprocessing.Value(ctypes.c_ulonglong, 0)
    
    processes = []
    for _ in range(MAX_PROCESSES):
        p = multiprocessing.Process(target=worker_main, args=(total_counter,))
        p.start()
        processes.append(p)

    try:
        start_time = time.time()
        last_count = 0
        
        while True:
            time.sleep(5)
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Read shared counter
            current_total = total_counter.value
            
            # Calculate actual keys per second based on real progress
            keys_since_last = current_total - last_count
            rate = keys_since_last / 5.0
            
            last_count = current_total
            
            print(f"Rate: {rate:,.0f} keys/s | Total Checked: {current_total:,.0f}")

    except KeyboardInterrupt:
        print("\nStopping...")
        for p in processes:
            p.terminate()
            
