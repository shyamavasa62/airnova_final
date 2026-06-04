import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import pickle

# 1. LOAD DATA
from ml.src.data_source import load_effective_dataset

df = load_effective_dataset()

# 2. BASIC CLEANING
df = df.dropna()

# 3. CONVERT DATE
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df = df.dropna()
# 4. FEATURE ENGINEERING
df['day'] = df['Date'].dt.day
df['month'] = df['Date'].dt.month
df['weekend'] = df['Date'].dt.weekday >= 5

# Convert True/False → 1/0
df['weekend'] = df['weekend'].astype(int)

# 5. SELECT FEATURES


df['AQI_future'] = df['AQI'].shift(-1)
df = df.dropna()
X = df[['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'day', 'month', 'weekend']]
y = df['AQI_future']
# 6. TRAIN-TEST SPLIT
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 7. TRAIN MODEL
model = RandomForestRegressor()
model.fit(X_train, y_train)

# 8. PREDICT
predictions = model.predict(X_test)

# 9. EVALUATE
mae = mean_absolute_error(y_test, predictions)
rmse = np.sqrt(mean_squared_error(y_test, predictions))
r2 = r2_score(y_test, predictions)

print("MAE:", mae)
print("RMSE:", rmse)
print("R2 Score:", r2)

import matplotlib.pyplot as plt
import numpy as np

# Convert to numpy (if not already done)
y_test_np = np.array(y_test, dtype=float)
pred_np = np.array(predictions, dtype=float)

plt.figure(figsize=(8,6))

plt.plot(y_test_np[:100], label="Actual AQI")
plt.plot(pred_np[:100], label="Predicted AQI")

plt.legend()
plt.title("Actual vs Predicted AQI (Time Series)")
plt.xlabel("Samples")
plt.ylabel("AQI")

plt.grid(True)

plt.show()
# 10. SAVE MODEL
pickle.dump(model, open("ml/models/aqi_model.pkl", "wb"))

print("Model saved successfully!")