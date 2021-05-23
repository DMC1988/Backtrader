import backtrader as bt
import numpy as np
import math


class CandleStrat(bt.Strategy):
    '''Candle Stick Strategy.
    Count three successive down trend candle sticks and then buy on the fourth one.
    Then, after an @exitbars count of candle sticks, sell at market price.

    Parameters
    -----------
    exitbars: Number of candle sticks to count and the sell at market price.
    orderPercentage: Cash to invest, cash = cashInBroker*orderPercentage
    '''

    params = (
        ('exitbars', 5),
        ('orderPercentage',0.99),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy '''
        dt = dt or self.datas[0].datetime.date(0)
        # Print dates
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        self.order = None  # Variable for pending orders tracking
        self.buyprice = None  # Variable for buy price traking
        self.buycomm = None  # Variable for commission tracking

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Possible order status, don't do anything at least the order is completed.
            return

        if order.status in [order.Completed]:
            # If orders ar completed do:
            if order.isbuy():
                self.log('BUY EXECUTED, Size: {}, Price: {:.2f}, Cost: {:.2f}, Comm: {:.2f}'.format(order.executed.size,
                                                                                          order.executed.price,
                                                                                          order.executed.value,
                                                                                          order.executed.comm))
            elif order.issell():
               self.log('SELL EXECUTED, Size: {}, Price: {:.2f}, Cost: {:.2f}, Comm: {:.2f}'.format(order.executed.size,
                                                                                          order.executed.price,
                                                                                          order.executed.value,
                                                                                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Message if the orders weren't completed.
            self.log('Order Canceled/Margin/Rejected')

        self.bar_executed = len(self)

        # After one order is completed turn the order status to none, no orders pending.
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        # Show results of a trade.
        self.log('OPERATION PROFIT, GROSS {:.2f}, NET: {:.2f}'.format(trade.pnl, trade.pnlcomm))


    # Here comes the core of the strategy.
    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, {}'.format( self.dataclose[0]))

        if self.order:
            # If there is a pending order don't do anything
            return

        if not self.position:
            if self.dataclose[0] < self.dataclose[-1]:
                # current close less than previous close

                if self.dataclose[-1] < self.dataclose[-2]:
                    # previous close less than the previous close

                    amountToinvest = (self.params.orderPercentage * self.broker.cash)
                    self.size = math.floor(amountToinvest / self.dataclose[0])

                    # BUY with default parameters
                    self.log('BUY CREATE, {}'.format(self.dataclose[0]))
                    self.order= self.buy(size=self.size)

        else:
            # If we are in the market we already own stocks.
            # Check if extibars has passed and then sell
            if len(self) >= (self.bar_executed + self.params.exitbars):
                self.log('SELL CREATE {}'.format(self.dataclose[0]))
                self.order = self.sell(size=self.size)

class BuyAndHold_More_Fund(bt.Strategy):
    params = dict(
        monthly_cash=100.0,  # amount of cash to buy every month
    )

    def start(self):
        # Activate the fund mode and set the default value at 100
        self.broker.set_fundmode(fundmode=True, fundstartval=100.00)

        self.cash_start = self.broker.get_cash()
        self.val_start = 100.0

        # Add a timer which will be called on the 1st trading day of the month
        self.add_timer(
            bt.timer.SESSION_END,  # when it will be called
            monthdays=[1],  # called on the 1st day of the month
            monthcarry=True,  # called on the 2nd day if the 1st is holiday
        )

    def notify_timer(self, timer, when, *args, **kwargs):
        # Add the influx of monthly cash to the broker
        self.broker.add_cash(self.p.monthly_cash)

        # buy available cash
        target_value = self.broker.get_value() + self.p.monthly_cash
        self.order_target_value(target=target_value)

        dt = self.datas[0].datetime.date(0)
        print('{} Cash Added Shares {}'.format(dt, math.floor(self.broker.get_fundshares())))

    def stop(self):
        # calculate the actual returns
        self.froi = self.broker.get_fundvalue() - self.val_start
        print('Fund Value: {:.2f}%'.format(self.froi))

class smaStrategy(bt.Strategy):
    ''' Simple Moving Average up cross strategy
    Buy when closing price crosses upward simple moving average.
    Sell when closing price crosses downward simple moving average.

    Parameters
    ----------
    maperiod: int
    Data needed for sma calculation.
    orderPercentage: float
    Cash to invest., cash = cash_total*orderPercentage
    '''

    params = (
        ('maPeriod', 15),
        ('orderPercentage', 0.95),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        self.broker.set_fundmode(fundmode=True, fundstartval=100.00)
        self.val_start = 100.0

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maPeriod)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Size: {}, Price: {:.2f}, Cost: {:.2f}, Comm {:.2f}'.format(order.executed.size,
                                                                                         order.executed.price,
                                                                                         order.executed.value,
                                                                                         order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Size:{}, Price: {:.2f}, Cost: {:.2f}, Comm {:.4f}'.format(order.executed.size,
                                                                                         order.executed.price,
                                                                                         order.executed.value,
                                                                                         order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS {:.2f}, NET {:.2f}'.format(trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, {:.2f}'.format(self.dataclose[0]))

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] > self.sma[0]:
                # Money to invest.
                amountToinvest = (self.params.orderPercentage * self.broker.cash)
                self.size = math.floor(amountToinvest / self.data.close)

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, {:.2f}'.format(self.dataclose[0]))

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy(size=self.size)

        else:

            if self.dataclose[0] < self.sma[0]:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, {:.2f}'.format(self.dataclose[0]))

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell(size=self.size)

    def stop(self):
        # calculate the actual returns
        self.froi = self.broker.get_fundvalue() - self.val_start
        print('Fund Value: {:.2f}%'.format(self.froi))

class wmaStrategy(bt.Strategy):
    '''
    Stan Weinstein Weighted Moving Average Crossing Strategy

    Strategy based on weekly weighted moving average.
    Buys when closing price crosses upward the wma at a larger volume than monthly average.
    Buys when closing price crosses downward the wma at a larger volume than monthly average.

    Parameters
    ----------
    wmaPriceperiod: int
    Data needed for wma calculation.
    wmaVolumePeriod: int
    Data needed for average volume calculation.
    volReltship: float
    Relationship between this week volume ant previous month volume
    orderPercentage: float
    Cash to invest., cash = cash_total*orderPercentage
    '''

    params = (
        ('wmaPriceperiod', 30),
        ('wmaVolumePeriod', 4),
        ('volReltship', 1.05),
        ('orderPercentage', 0.99),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
       # Tracking of daily and weekly close price and volume
        self.datacloseD = self.datas[0].close
        self.datavolumeD = self.datas[0].volume

        self.datacloseS = self.datas[1].close
        self.datavolumeS = self.datas[1].volume

        self.broker.set_fundmode(fundmode=True, fundstartval=100.00)
        self.val_start = 100.0

        # Tracking of pending orders data.
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Weighted Moving Average calculation
        self.wma = bt.indicators.WeightedMovingAverage(
            self.datas[1], period=self.params.wmaPriceperiod)


    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Don´t do anything if orders are different than completed
            return

        # If orders are completed do:
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Size {}, Price: {:.2f}, Cost: {:.2f}, Comm {:.2f}'.format(
                                                                                         order.executed.size,
                                                                                         order.executed.price,
                                                                                         order.executed.value,
                                                                                         order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

            else:  # Sell
                self.log('SELL EXECUTED, Size {}, Price: {:.2f}, Cost: {:.2f}, Comm {:.2f}'.format(
                                                                                         order.executed.size,
                                                                                         order.executed.price,
                                                                                         order.executed.value,
                                                                                         order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # After order is completed reset status
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        # After a trade is closed show me the results.
        self.log('OPERATION PROFIT, GROSS {:.2f}, NET {:.2f}'.format(trade.pnl, trade.pnlcomm))

    def next(self):
        # Show daily close price and volume
        self.log('Close, {:.2f}'.format(self.datacloseD[0]))
        self.log('Volume, {:.2f}'.format(self.datavolumeD[0]))

        # Check if this week volume is greater than de volume of previous month
        self.isVolAlto = ((self.datavolumeS[0]) / (np.mean(self.datavolumeS.get(size=self.params.wmaVolumePeriod,
                                                                                ago=-1)))) > self.params.volReltship

        if self.order:
            # If there are pending orders don´t do anything
            return

        # Check if we are in the market
        if not self.position:

            # If we are not in the market buy when closing price crosses upward wma and the volume is large.
            if (self.datacloseS[0] > self.wma[0]) and self.isVolAlto:
                # Money to invest.
                amountToinvest = (self.params.orderPercentage * self.broker.cash)
                self.size = math.floor(amountToinvest / self.datacloseD[0])

                self.log('BUY CREATE, {:.2f}'.format(self.datacloseD[0]))

                # Buy on daily time frame at market value.
                self.order = self.buy(data=self.datas[0], size=self.size)

        else:
            # If we are in the market sell when closing price crosses downward wma and volume is large.
            if (self.datacloseS[0] < 0.98*self.wma[0] and self.isVolAlto):

                self.log('SELL CREATE, {:.2f}'.format(self.datacloseD[0]))

                # Sell on daily time frame at market value.
                self.order = self.sell(data=self.datas[0], size=self.size)

    def stop(self):
        # calculate the actual returns
        self.froi = self.broker.get_fundvalue() - self.val_start
        print('Fund Value: {:.2f}%'.format(self.froi))

class GoldenCross(bt.Strategy):
    '''Golden Cross Strategy
    Strategy based on 50 and 200 simple moving average.
    Buy when sma50 crosses upward the sma200.
    Sell when sma50 crosses downward the sma200

    Parameters
    ----------
    fast: int
    Data for sma50 calculation.

    slow: int
    Data for sma200 calculation

    orderPercentage: float
    Cash to invest., cash = cash_total*orderPercentage
    '''

    params = (
        ('fast', 50),
        ('slow', 200),
        ('orderPercentage', 0.95))

    def __init__(self):
        #Needed indicators.

        self.fastMovingAverage = bt.indicators.SimpleMovingAverage(self.data.close, period = self.params.fast,
                                                   plotname = '50 day moving average')

        self.slowMovingAverage = bt.indicators.SimpleMovingAverage(self.data.close, period = self.params.slow,
                                                   plotname = '200 day moving average')

        self.crossover = bt.indicators.CrossOver(self.fastMovingAverage, self.slowMovingAverage)



    def next(self):
        if self.position.size == 0:
            if self.crossover > 0:
                # Money to invest.
                amountToinvest = (self.params.orderPercentage * self.broker.cash)
                self.size = math.floor(amountToinvest / self.data.close)

                print('Buy {} shares at {}'.format(self.size, self.data.close[0]))
                self.buy(size=self.size)

        if self.position.size > 0:
            if (self.crossover < 0):
                print('Sell {} shares at {}'.format(self.size, self.data.close[0]))
                self.sell(size=self.size)

class BuyTheDip(bt.Strategy):
    params = (
        ('maPeriod', 9 ),
        ('orderPercentage', 0.95),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
       # Tracking of daily and weekly close price and volume
        self.datacloseD = self.datas[0].close

        self.broker.set_fundmode(fundmode=True, fundstartval=100.00)
        self.val_start = 100.0

        # Tracking of pending orders data.
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.compra = 0

        # Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maPeriod)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Don´t do anything if orders are different than completed
            return

        # If orders are completed do:
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Size {}, Price: {:.2f}, Cost: {:.2f}, Comm {:.2f}'.format(
                                                                                         order.executed.size,
                                                                                         order.executed.price,
                                                                                         order.executed.value,
                                                                                         order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # After order is completed reset status
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        # After a trade is closed show me the results.
        self.log('OPERATION PROFIT, GROSS {:.2f}, NET {:.2f}'.format(trade.pnl, trade.pnlcomm))

    def next(self):
        # Show daily close price and volume
        self.log('Close, {:.2f}'.format(self.datacloseD[0]))

        if self.order:
            # If there are pending orders don´t do anything
            return

        # If we are not in the market buy when closing price crosses upward wma and the volume is large.

        while abs(self.sma[-2] - self.sma[0]) > 0.01*self.sma[-2]:
            self.compra = 1
            return
        if self.compra ==1:
            self.broker.add_cash(100)
            # Money to invest.
            amountToinvest = (self.params.orderPercentage * self.broker.cash)
            self.size = math.floor(amountToinvest / self.datacloseD[0])

            self.log('BUY CREATE, {:.2f}'.format(self.datacloseD[0]))

            # Buy on daily time frame at market value.
            self.order = self.buy(data=self.datas[0], size=self.size)
            self.compra = 0

    def stop(self):
        # calculate the actual returns
        self.froi = self.broker.get_fundvalue() - self.val_start
        print('Fund Value: {:.2f}%'.format(self.froi))

