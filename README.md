# Telegram_alerts_bot
An example of telegram bot sending alerts when some metric has anomalous value

## How does it work?
Gitlab CI/CD triggers the script every 15 minutes (you need to adjust it on their website and create .yaml file)\n
It compares every metric you want to track with its allowable range of values which is between 25%quartile - (a * [IQR](shorturl.at/oDIT2)) and 75%quartile + (a * IQR)
You need to pass the parameters of the coefficient that we multiply IQR with and the number of values for which quartiles are calculated
If the anomaly detected it send the report in telegram with the current value and the percentage of deviation from previous value of this metric accompanied with the handy plot where you can see the daily distribution of this metric with upper and lower boundaries of allowed range
Values are accumulated and represented as 15-minute slices
Current value is the 15-minute slice that happened before the moment of script triggering, e.g. if Gitlab triggered the script at 16:58 the current value will be taken as the accumulated value between 16:30 and 16:45

