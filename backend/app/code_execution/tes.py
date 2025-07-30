import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA


# create sample df to run this code
data = {
    'Machine ID': ['M1', 'M1', 'M1', 'M2', 'M2', 'M2'],
    'Timestamp': [
        '2023-10-01 00:00:00', '2023-10-01 01:00:00', '2023-10-01 02:00:00',
        '2023-10-01 00:00:00', '2023-10-01 01:00:00', '2023-10-01 02:00:00'
    ],
    'Energy Consumption (kWh)': [100, 150, 200, 80, 120, 160]
}
df = pd.DataFrame(data)
# Assuming df is your DataFrame with columns: 'Machine ID', 'Timestamp', 'Energy Consumption (kWh)'
# Convert 'Timestamp' to datetime if not already

# Ensure Timestamp is datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Identify all machines
machines = df['Machine ID'].unique()

results = []

# For each machine, fit an ARIMA and forecast next 24 hours
for machine in machines:
    df_machine = df[df['Machine ID'] == machine].copy()
    df_machine = df_machine.sort_values('Timestamp')
    df_machine.set_index('Timestamp', inplace=True)
    # Ensure data is continuous hourly (fill missing with NaN then ffill or 0)
    idx = pd.date_range(df_machine.index.min(), df_machine.index.max(), freq='H')
    y = df_machine['Energy Consumption (kWh)'].reindex(idx)
    y = y.fillna(method='ffill').fillna(0)

    # Fit ARIMA (p,d,q)=(1,1,1) as a robust default
    try:
        model = ARIMA(y, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=24)  # Next 24 hours
    except Exception as e:
        # If ARIMA fails (e.g., insufficient data), fill with recent avg
        recent_mean = y[-24:].mean() if len(y) >= 24 else y.mean()
        forecast = pd.Series([recent_mean] * 24,
                             index=pd.date_range(y.index[-1] + pd.Timedelta(hours=1), periods=24, freq='H'))
    forecast_index = pd.date_range(y.index[-1] + pd.Timedelta(hours=1), periods=24, freq='H')
    out = pd.DataFrame({
        'Machine ID': machine,
        'Forecast Timestamp': forecast_index,
        'Forecasted Energy Consumption (kWh)': forecast.values
    })
    results.append(out)

result = pd.concat(results, ignore_index=True)
output = result.to_csv(index=False)
print(output)