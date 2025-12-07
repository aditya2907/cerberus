# backend/brain/train_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

# 1. Generate "Fake" Training Data
# We create a pattern: High amounts from "High Risk Countries" are fraud.
print("Generating synthetic data...")
n_samples = 1000
data = {
    'amount': np.random.uniform(10, 5000, n_samples),
    'hour': np.random.randint(0, 24, n_samples),
    # Let's map countries to integers: US=0, IE=1, RU=2 (Risky)
    'country_code': np.random.randint(0, 3, n_samples) 
}
df = pd.DataFrame(data)

# Create logic for the "Target" (1 = Fraud, 0 = Safe)
# Rule: If Amount > 2000 AND Country is RU (2), it's Fraud.
df['is_fraud'] = ((df['amount'] > 2000) & (df['country_code'] == 2)).astype(int)

# 2. Train the Model
print("Training Random Forest...")
X = df[['amount', 'hour', 'country_code']]
y = df['is_fraud']

model = RandomForestClassifier(n_estimators=50)
model.fit(X, y)

# 3. Save the Model to a file
joblib.dump(model, 'fraud_model.joblib')
print("Model saved as 'fraud_model.joblib'")