# High-Performance Key Generation System

## Overview
This project is a Proof of Concept (PoC) demonstrating high-throughput data generation and database lookups using Python's `multiprocessing` capabilities. 

It simulates a "Bitcoin Key Finder" to showcase specific engineering challenges:
1.  **Concurrency:** Managing CPU-bound tasks across multiple cores without race conditions.
2.  **Fast I/O:** Utilizing Memcached for low-latency lookups (sub-millisecond).
3.  **Containerization:** Fully Dockerized environment for easy deployment.

**Note:** This is an educational project exploring cryptography and system performance. Due to the mathematical magnitude of the 256-bit key space, this script is not intended for actual key recovery.

## Tech Stack
* **Language:** Python 3.11
* **Cryptography:** `ecdsa` (SECP256k1 curve), SHA-256, RIPEMD-160
* **Database:** Memcached (Key-Value Store)
* **DevOps:** Docker & Docker Compose

## How It Works
1.  **Generation:** The system spawns worker processes based on available CPU cores.
2.  **Compute:** Each worker generates batches of ECDSA private keys and derives the corresponding Public Addresses.
3.  **Verification:** Addresses are cross-referenced against a local Memcached instance containing target data.
4.  **Reporting:** Real-time metrics (Keys/sec) are calculated using shared memory counters to ensure thread safety.

## How to Run

### Prerequisites
* Docker & Docker Compose installed

### Quick Start
1.  Clone the repo:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/distributed-keygen-demo.git](https://github.com/YOUR_USERNAME/distributed-keygen-demo.git)
    cd distributed-keygen-demo
    ```

2.  Start the cluster:
    ```bash
    docker-compose up --build
    ```

3.  View the output:
    You will see the workers initialize and the real-time rate display:
    ```text
    Rate: 12,500 keys/s | Total Checked: 1,500,000
    ```
