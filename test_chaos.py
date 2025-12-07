#!/usr/bin/env python3
"""
Chaos Testing Script for Sentinel Fraud Detection System

This script sends 100 concurrent requests to the Gateway API to demonstrate
circuit breaker behavior when the Brain service is unavailable or slow.

Usage:
    python test_chaos.py [--url URL] [--requests NUM] [--workers NUM]

Example:
    # Kill the brain container while this runs to see circuit breaker in action
    python test_chaos.py --requests 100 --workers 20
"""

import argparse
import asyncio
import aiohttp
import time
from collections import Counter
from datetime import datetime
import random


class ChaosTestRunner:
    def __init__(self, base_url: str, num_requests: int, workers: int):
        self.base_url = base_url.rstrip('/')
        self.num_requests = num_requests
        self.workers = workers
        self.results = []
        self.start_time = None
        
    async def send_request(self, session: aiohttp.ClientSession, request_id: int):
        """Send a single transaction request to the gateway."""
        url = f"{self.base_url}/transaction"
        
        # Generate random transaction data
        payload = {
            "transaction_id": f"txn_{request_id:06d}",
            "amount": round(random.uniform(10.0, 5000.0), 2),
            "currency": random.choice(["USD", "EUR", "GBP", "JPY"]),
            "user_id": f"user_{random.randint(1000, 9999)}"
        }
        
        try:
            start = time.time()
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=3)) as response:
                elapsed = time.time() - start
                data = await response.json()
                
                # Determine status
                circuit_state = data.get('circuit_state', 'UNKNOWN')
                is_fraud = data.get('is_fraud', False)
                
                if circuit_state == 'OPEN':
                    status = "Circuit Open"
                    color = "\033[93m"  # Yellow
                elif response.status == 200:
                    status = "Success"
                    color = "\033[92m"  # Green
                else:
                    status = f"Error {response.status}"
                    color = "\033[91m"  # Red
                
                result = {
                    'request_id': request_id,
                    'status': status,
                    'circuit_state': circuit_state,
                    'is_fraud': is_fraud,
                    'elapsed': elapsed,
                    'http_status': response.status
                }
                
                self.results.append(result)
                
                # Print result
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                fraud_indicator = " FRAUD" if is_fraud else " SAFE"
                print(f"{color}[{timestamp}] Request #{request_id:3d}: {status:<15} | "
                      f"Circuit: {circuit_state:<6} | {fraud_indicator} | "
                      f"{elapsed*1000:.0f}ms\033[0m")
                
                return result
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            status = "Timeout"
            result = {
                'request_id': request_id,
                'status': status,
                'circuit_state': 'UNKNOWN',
                'is_fraud': False,
                'elapsed': elapsed,
                'http_status': 0
            }
            self.results.append(result)
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\033[91m[{timestamp}] Request #{request_id:3d}: {status:<15} | "
                  f"Circuit: UNKNOWN | ⏱  TIMEOUT | {elapsed*1000:.0f}ms\033[0m")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start if start else 0
            status = f"Exception: {type(e).__name__}"
            result = {
                'request_id': request_id,
                'status': status,
                'circuit_state': 'UNKNOWN',
                'is_fraud': False,
                'elapsed': elapsed,
                'http_status': 0
            }
            self.results.append(result)
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\033[91m[{timestamp}] Request #{request_id:3d}: {status:<15} | "
                  f"Error: {str(e)[:40]}\033[0m")
            
            return result
    
    async def worker(self, session: aiohttp.ClientSession, queue: asyncio.Queue):
        """Worker coroutine to process requests from queue."""
        while True:
            request_id = await queue.get()
            if request_id is None:  # Sentinel value to stop worker
                queue.task_done()
                break
            
            await self.send_request(session, request_id)
            queue.task_done()
            
            # Small delay between requests to avoid overwhelming
            await asyncio.sleep(0.05)
    
    async def run(self):
        """Run the chaos test."""
        print("\n" + "="*80)
        print(" SENTINEL CHAOS TEST - Circuit Breaker Demonstration ")
        print("="*80)
        print(f"Target URL: {self.base_url}")
        print(f"Total Requests: {self.num_requests}")
        print(f"Concurrent Workers: {self.workers}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        print("\n TIP: Kill the brain container now to see circuit breaker in action!")
        print("   Docker: docker-compose stop brain")
        print("   K8s: kubectl scale deployment sentinel-brain --replicas=0\n")
        
        self.start_time = time.time()
        
        # Create queue and add all request IDs
        queue = asyncio.Queue()
        for i in range(1, self.num_requests + 1):
            await queue.put(i)
        
        # Add sentinel values to stop workers
        for _ in range(self.workers):
            await queue.put(None)
        
        # Create session and workers
        async with aiohttp.ClientSession() as session:
            workers = [
                asyncio.create_task(self.worker(session, queue))
                for _ in range(self.workers)
            ]
            
            # Wait for all tasks to complete
            await queue.join()
            
            # Wait for workers to finish
            await asyncio.gather(*workers)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary statistics."""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print(" TEST SUMMARY")
        print("="*80)
        
        # Count statuses
        status_counter = Counter(r['status'] for r in self.results)
        circuit_counter = Counter(r['circuit_state'] for r in self.results)
        
        # Calculate statistics
        success_count = status_counter.get('Success', 0)
        circuit_open_count = status_counter.get('Circuit Open', 0)
        timeout_count = status_counter.get('Timeout', 0)
        error_count = sum(count for status, count in status_counter.items() 
                         if status not in ['Success', 'Circuit Open', 'Timeout'])
        
        total_requests = len(self.results)
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        # Response times
        elapsed_times = [r['elapsed'] for r in self.results if r['elapsed'] > 0]
        avg_response_time = sum(elapsed_times) / len(elapsed_times) if elapsed_times else 0
        min_response_time = min(elapsed_times) if elapsed_times else 0
        max_response_time = max(elapsed_times) if elapsed_times else 0
        
        # Fraud detection stats
        fraud_count = sum(1 for r in self.results if r.get('is_fraud', False))
        
        print(f"\nTotal Requests Sent: {total_requests}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Requests/Second: {total_requests/total_time:.2f}")
        print(f"\n Successful: {success_count} ({success_count/total_requests*100:.1f}%)")
        print(f"  Circuit Open (Fail-Open): {circuit_open_count} ({circuit_open_count/total_requests*100:.1f}%)")
        print(f"⏱  Timeouts: {timeout_count} ({timeout_count/total_requests*100:.1f}%)")
        print(f" Errors: {error_count} ({error_count/total_requests*100:.1f}%)")
        
        print(f"\n Circuit Breaker States:")
        for state, count in circuit_counter.most_common():
            print(f"   {state}: {count} ({count/total_requests*100:.1f}%)")
        
        print(f"\n Response Times:")
        print(f"   Average: {avg_response_time*1000:.0f}ms")
        print(f"   Min: {min_response_time*1000:.0f}ms")
        print(f"   Max: {max_response_time*1000:.0f}ms")
        
        print(f"\n Fraud Detection:")
        print(f"   Flagged as Fraud: {fraud_count}/{total_requests} ({fraud_count/total_requests*100:.1f}%)")
        
        print("\n" + "="*80)
        
        # Verdict
        if circuit_open_count > 0:
            print(" SUCCESS: Circuit breaker activated! System failed open gracefully.")
        elif success_rate > 95:
            print(" SUCCESS: All requests processed successfully.")
        else:
            print("  WARNING: Some requests failed. Check logs for details.")
        
        print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Chaos testing tool for Sentinel Fraud Detection System"
    )
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='Base URL of the Gateway API (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--requests',
        type=int,
        default=100,
        help='Number of requests to send (default: 100)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=20,
        help='Number of concurrent workers (default: 20)'
    )
    
    args = parser.parse_args()
    
    # Run the test
    runner = ChaosTestRunner(args.url, args.requests, args.workers)
    
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\n\n  Test interrupted by user")
        if runner.results:
            runner.print_summary()


if __name__ == "__main__":
    main()
