import telegram
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import io
import pandas as pd
import pandahouse as ph
from datetime import datetime, timedelta

my_token = ''  # here you need to replace it with your bot's token
bot = telegram.Bot(token=my_token)  # getting access

# chat-id can be obtained by sending a message to the bot using the link https://api.telegram.org/bot<your_bot_token>/getUpdates or using the bot.getUpdates() method
chat_id = ''

# connection to Clickhouse database
connection = {'host': '',
              'database':'',
              'user':'',
              'password':''
                             }

# creating an anomaly detection function with parametric values 'a' and 'n'
def check_anomaly(df, metric, a=4, n=5):
    df['q25'] = df[metric].shift(1).rolling(n).quantile(0.25) #creating rolling 25%-quartile of 'n' values before current value
    df['q75'] = df[metric].shift(1).rolling(n).quantile(0.75) #creating rolling 75%-quartile of 'n' values before current value
    df['iqr'] = df['q75'] - df['q25'] # calculating Interquartile range
    df['high'] = df['q75'] + a * df['iqr'] # making the upper bound of distribution with coefficient 'a'
    df['low'] = df['q25'] - a * df['iqr'] # making the lower bound of distribution with coefficient 'a'
    
    df['high'] = df['high'].rolling(n, center = True, min_periods = 1).mean() # smoothing the borders by taking the rolling mean and centering
    df['low'] = df['low'].rolling(n, center = True, min_periods = 1).mean() # smoothing the borders by taking the rolling mean and centering

    if df[metric].iloc[-1] < df['low'].iloc[-1] or df[metric].iloc[-1] > df['high'].iloc[-1]: # condition of alert
        is_alert = True
    else:
        is_alert = False
    return is_alert, df

def run_alert():
    # our query
    q = """SELECT *
            FROM
                (SELECT toStartOfFifteenMinutes(time) AS timestamp,
                           uniqExact(user_id) AS active_users_feed,
                           countIf(user_id, action = 'view') AS Views,
                           countIf(user_id, action = 'like') AS Likes,
                           countIf(user_id, action = 'like') / countIf(user_id, action = 'view') AS CTR
                FROM simulator_20221220.feed_actions
                WHERE time >= today() - 1 AND time < toStartOfFifteenMinutes(now())
                GROUP BY timestamp) AS t1
                JOIN
                (SELECT toStartOfFifteenMinutes(time) AS timestamp,
                            uniqExact(user_id) AS active_users_messenger,
                            count(user_id) AS messages_sent
                FROM simulator_20221220.message_actions
                WHERE time >= today() - 1 AND time < toStartOfFifteenMinutes(now())
                GROUP BY timestamp) AS t2
                USING(timestamp)
            ORDER BY timestamp"""

    #convert query to pandas dataframe
    data = ph.read_clickhouse(q, connection=connection)

    metrics = list(data.columns)[1:] # making a list of our metrics' names

    for metric in metrics: #iterating through every metric
        metric_df = data[['timestamp', metric]].copy()
        is_alert, df = check_anomaly(metric_df, metric)

        if is_alert:
            # making our caption
            msg = (f'An abnormal value was detected in a metric {metric} on a 15 minute time slice\n'
                   f'Current value {df[metric].iloc[-1]:.2f}\n'
                   f'Deviation from the previous value {1 - (df[metric].iloc[-1]/df[metric].iloc[-2]):.2%}\n')

            sns.set(rc={'figure.figsize': (16, 10)})
            sns.set_style("whitegrid")
            plt.title(metric, size=24)
            xformatter = mdates.DateFormatter('%H:%M') # adjusting time format to hours:minutes
            plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)

            ax = sns.lineplot(x=df['timestamp'], y=df[metric])
            ax = sns.lineplot(x=df['timestamp'], y=df['high'])
            ax = sns.lineplot(x=df['timestamp'], y=df['low'])

            ax.set(xlabel = 'time')
            ax.set(ylabel = metric)

            io_object = io.BytesIO()  #creating an empty clipboard file
            plt.savefig(io_object)  #saving chart to clipboard
            io_object.seek(0)  #moving cursor to the beginning
            io_object.name = f'{metric}.png'
            plt.close()

            bot.sendPhoto(chat_id = chat_id, photo = io_object, caption = msg) # sending our plot with caption
    return
run_alert()