import backtrader as bt
import datetime as dt
import strategies as strg


cerebro = bt.Cerebro()

# Get data from Yahoo Finance
data = bt.feeds.YahooFinanceData(
    dataname='KO',    # Ticker
    timeframe=bt.TimeFrame.Days, compression=1,
    # Do not pass values before this date
    fromdate=dt.datetime(2007, 1, 1),
    # Do not pass values after this date
    todate=dt.datetime(2021, 5, 20),
    reverse=False)

data.plotinfo.plotlog = True  # Semilog plot.
cerebro.adddata(data)  # Load daily stock data to cerebro
#cerebro.resampledata(data, timeframe=bt.TimeFrame.Weeks)  # Resampling data to week interval

cerebro.broker.setcash(1000)  # Available cash to invest
cerebro.addstrategy(strg.BuyAndHold_More_Fund)  # Load strategy to cerebro

print('Starting Portfolio Value: {}'.format(cerebro.broker.getvalue()))

cerebro.run()  # Run Strategy

print('Final Portfolio Value: {}'.format(cerebro.broker.getvalue()))

# Plot
cerebro.plot()
