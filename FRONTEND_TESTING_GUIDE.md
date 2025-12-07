# Frontend Testing Guide

## Quick Test Cases for Your Dashboard

Now that the CORS issue is fixed, try these transactions in your frontend dashboard:

###  Test Case 1: Normal Transaction (Should Pass)
```
Amount: $500
User ID: user-123
Currency: USD
Merchant: Amazon
Payment Method: credit_card
IP Address: 192.168.1.1
Country: USA
```
**Expected Result:**  NOT FRAUD (Green) - Risk Score: 0.1

---

###  Test Case 2: Suspicious High-Value Transaction (Should Fail)
```
Amount: $15,000
User ID: user-456
Currency: USD
Merchant: Electronics Store
Payment Method: credit_card
IP Address: 10.0.0.1
Country: Nigeria
```
**Expected Result:**  FRAUD DETECTED (Red) - Risk Score: 0.9

---

###  Test Case 3: Edge Case - Exactly at Threshold
```
Amount: $10,000
User ID: user-789
Currency: EUR
Merchant: Luxury Goods
Payment Method: debit_card
IP Address: 172.16.0.1
Country: Germany
```
**Expected Result:**  NOT FRAUD (Green) - Risk Score: 0.1

---

###  Test Case 4: Very High Amount
```
Amount: $50,000
User ID: user-001
Currency: GBP
Merchant: Real Estate
Payment Method: bank_transfer
IP Address: 192.168.0.1
Country: UK
```
**Expected Result:**  FRAUD DETECTED (Red) - Risk Score: 0.9

---

###  Test Case 5: Micro Transaction
```
Amount: $0.99
User ID: user-202
Currency: USD
Merchant: App Store
Payment Method: credit_card
IP Address: 172.16.0.100
Country: USA
```
**Expected Result:**  NOT FRAUD (Green) - Risk Score: 0.1

---

## Current Fraud Detection Rules

The system currently uses a simple rule:
- **Transactions > $10,000** → Flagged as FRAUD (Risk Score: 0.9)
- **Transactions ≤ $10,000** → Considered SAFE (Risk Score: 0.1)

---

## API Endpoint

Your frontend is correctly configured to call:
```
POST http://localhost:8000/transaction
```

With CORS properly enabled for:
- http://localhost:5173 (Vite)
- http://localhost:3000 (Next.js)

---

## Testing the Frontend

1. **Start your frontend:**
   ```bash
   cd frontend/dashboard
   npm run dev
   ```

2. **Open browser:** http://localhost:5173

3. **Submit test transactions** using the cases above

4. **Observe the results:**
   - Green shield = Safe transaction
   - Red shield = Fraud detected
   - Yellow shield = Circuit breaker open (service unavailable)

---

## Troubleshooting

If you still see CORS errors:
1. Hard refresh the browser (Cmd+Shift+R on Mac)
2. Clear browser cache
3. Try in incognito mode
4. Check browser console for specific errors

If the backend is not responding:
```bash
# Check if services are running
docker-compose ps

# Restart services if needed
docker-compose restart gateway
```

---

## Backend Logs

To see what's happening on the backend:
```bash
# Gateway logs
docker logs sentinel-gateway -f

# Brain service logs
docker logs sentinel-brain -f

# All logs
docker-compose logs -f
```

---

**Happy Testing! **
