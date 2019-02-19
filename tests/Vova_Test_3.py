from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
import argparse
import datetime

# The above could be sent to an independent module
import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.indicators as btind
from backtrader.analyzers import SQN



from backtrader.feeds import GenericCSVData

class GenericCSV_PE(GenericCSVData):

    # Add a 'pe' line to the inherited ones from the base class
    lines = ('pe',)

    # openinterest in GenericCSVData has index 7 ... add 1
    # add the parameter to the parameters inherited from the base class
    params = (('pe', 7),)



class WriteQuotesInLog(bt.Strategy):
    '''This strategy buys/sells upong the close price crossing
    upwards/downwards a Simple Moving Average.

    It can be a long-only strategy by setting the param "onlylong" to True
    '''
    params = dict(
        period=15,
        stake=1,
        printout=False,
        onlylong=False,
        csvcross=False,
        exectype='Market',
        perc1=0.0,
        valid=1
    )

    def start(self):
        pass

    def stop(self):
        pass

    def log(self, txt, dt=None):
        if self.p.printout:
            dt = dt or self.data.datetime[0]
            dt = bt.num2date(dt)
            print(f'{dt.isoformat()}  {txt}')

    def __init__(self):
        # To control operation entries
        self.orderid = None

        # Create SMA on 2nd data
        sma = btind.MovAv.SMA(self.data, period=self.p.period)
        # Create a CrossOver Signal from close an moving average
        self.signal = btind.CrossOver(self.data.close, sma)
        self.signal.csv = self.p.csvcross

        btind.SMA(self.data.pe, period=1, subplot=False)  # A way to draw the new data field on the chart

    def next(self):
        self.log(f'Tick... Close: {self.data.close[0]}, pe: {self.data.pe[0]},  date: {self.data.datetime[0]}')
        if self.orderid:
            # An order is pending ... nothing can be done
            return

        if self.signal > 0.0:  # cross upwards
            if self.position:
                self.log(f'CLOSING SHORT POSITION ({self.position}) at {self.data.close[0]} price')
                self.close()
            else:
                if self.p.exectype == 'Market':
                    self.buy(exectype=bt.Order.Market, size=self.p.stake)

                    self.log(f'BUY CREATE, exectype Market, on {self.data.close[0]} price,'
                             f' vol = {self.p.stake}')

                elif self.p.exectype == 'Limit':

                    price = self.data.close[0] * (1.0 - self.p.perc1 / 100.0) #or on bid1, bid2...

                    if self.p.valid:
                        valid = self.data.datetime.date(0) + datetime.timedelta(days=self.p.valid)
                        txt = 'BUY CREATE, exectype Limit, price %.2f, valid: %s'
                        self.log(txt % (price, valid.strftime('%Y-%m-%d')))
                    else:
                        valid = None
                        txt = 'BUY CREATE, exectype Limit, price %.2f'
                        self.log(txt % price)

                    self.buy(exectype=bt.Order.Limit, price=price, size=self.p.stake, valid=valid)

        elif self.signal < 0.0:
            if self.position:
                self.log(f'CLOSING LONG POSITION ({self.position}) at {self.data.close[0]} price')
                self.close()
            else:
                if not self.p.onlylong:
                    if self.p.exectype == 'Market':
                        self.sell(exectype=bt.Order.Market, size=self.p.stake)

                        self.log(f'BUY CREATE, exectype Market, on {self.data.close[0]} price,'
                                 f' vol = {self.p.stake}')

                    elif self.p.exectype == 'Limit':

                        price = self.data.close[0] * (1.0 + self.p.perc1 / 100.0)  # or on bid1, bid2...

                        if self.p.valid:
                            valid = self.data.datetime.date(0) + datetime.timedelta(days=self.p.valid)
                            txt = 'SELL CREATE, exectype Limit, price %.2f, valid: %s'
                            self.log(txt % (price, valid.strftime('%Y-%m-%d')))
                        else:
                            valid = None
                            txt = 'SELL CREATE, exectype Limit, price %.2f'
                            self.log(txt % price)

                        self.sell(exectype=bt.Order.Limit, price=price, size=self.p.stake, valid=valid)

    def notify_order(self, order):
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            self.log(f'.. Order {order.Status[order.status]}, waiting...')  # : {order} - print whole order instance
            return  # Await further notifications

        if order.status == order.Completed:
            if order.isbuy():
                buytxt = 'BUY COMPLETED, %.2f' % order.executed.price
                self.log(buytxt, order.executed.dt)
            else:
                selltxt = 'SELL COMPLETED, %.2f' % order.executed.price
                self.log(selltxt, order.executed.dt)

        elif order.status in [order.Expired, order.Canceled, order.Margin]:
            self.log('.. Order is %s ,' % order.Status[order.status])
            pass  # Simply log

        # Allow new orders
        self.orderid = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log('TRADE PROFIT, GROSS %.2f, NET %.2f' %
                     (trade.pnl, trade.pnlcomm))

        elif trade.justopened:
            self.log('TRADE OPENED, SIZE %2d' % trade.size)


def runstrategy():
    args = parse_args()

    # Create a cerebro
    cerebro = bt.Cerebro()

    # Get the dates from the args
    fromdate = datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
    todate = datetime.datetime.strptime(args.todate, '%Y-%m-%d')

    # Create the 1st data
    # data = btfeeds.BacktraderCSVData(
    #     dataname=args.data,
    #     fromdate=fromdate,
    #     todate=todate)

    data = bt.feeds.GenericCSVData(
        dataname=args.data,
        dtformat='%Y-%m-%dT%H:%M:%S.%f',
        timeframe=bt.TimeFrame.Ticks,
        fromdate=fromdate,
        todate=todate
    )


    data = GenericCSV_PE(
        dataname=args.data,
        dtformat='%Y-%m-%dT%H:%M:%S.%f',
        timeframe=bt.TimeFrame.Ticks,
        fromdate=fromdate,
        todate=todate
    )

    data.plotinfo.plotmaster = data

    # Add the 1st data to cerebro

    # cerebro.adddata(data)

    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=60)

    # Add the strategy
    cerebro.addstrategy(WriteQuotesInLog,
                        period=args.period,
                        onlylong=args.onlylong,
                        csvcross=args.csvcross,
                        stake=args.stake,
                        printout=args.printout,
                        exectype=args.exectype,
                        perc1=args.perc1,
                        valid=args.valid
                        )

    broker = bt.brokers.AlgBroker()
    cerebro.setbroker(broker)
    # Add the commission - only stocks like a for each operation
    cerebro.broker.setcash(args.cash)

    # Add the commission - only stocks like a for each operation
    cerebro.broker.setcommission(commission=args.comm,
                                 mult=args.mult,
                                 margin=args.margin)

    cerebro.addanalyzer(SQN)

    cerebro.addwriter(bt.WriterFile, csv=args.writercsv, rounding=2, out=args.log_dir)

    # And run it
    print(cerebro.getbroker())
    cerebro.run()

    # Plot if requested
    if args.plot:
        cerebro.plot(numfigs=args.numfigs, volume=False, zdown=False)


def parse_args():
    parser = argparse.ArgumentParser(description='MultiData Strategy')

    parser.add_argument('--data', '-d',
                        default='C:\\Users\\User\\PycharmProjects\\backtrader\\data\\JISL_pe.csv',
                        help='data to add to the system')

    parser.add_argument('--fromdate', '-f',
                        default='2018-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate', '-t',
                        default='2019-2-10',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--period', default=15, type=int,
                        help='Period to apply to the Simple Moving Average')

    parser.add_argument('--onlylong', '-ol', action='store_true',
                        help='Do only long operations')

    parser.add_argument('--printout', '-pr', action='store_true',
                        help='Print out log in console')

    parser.add_argument('--writercsv', '-wcsv', action='store_true',
                        help='Tell the writer to produce a csv stream')

    parser.add_argument('--log_dir', default='logs\Vova_Test_3_result',
                        help='Log file destination')

    parser.add_argument('--csvcross', action='store_true',
                        help='Output the CrossOver signals to CSV')

    parser.add_argument('--cash', default=100000, type=int,
                        help='Starting Cash')

    parser.add_argument('--comm', default=2, type=float,
                        help='Commission for operation')

    parser.add_argument('--mult', default=10, type=int,
                        help='Multiplier for futures')

    parser.add_argument('--margin', default=2000.0, type=float,
                        help='Margin for each future')

    parser.add_argument('--stake', default=1, type=int,
                        help='Stake to apply in each operation')

    parser.add_argument('--plot', '-p', action='store_true',
                        help='Plot the read data')

    parser.add_argument('--numfigs', '-n', default=1,
                        help='Plot using numfigs figures')

    parser.add_argument('--exectype', '-e', required=False, default='Market',
                        help=('Execution Type: Market (default), Close, Limit,'
                              ' Stop, StopLimit'))

    parser.add_argument('--perc1', '-p1', required=False, default=0.01,
                        type=float,
                        help=('%% distance from close price at order creation'
                              ' time for the limit/trigger price in Limit/Stop'
                              ' orders'))

    parser.add_argument('--valid', '-v', required=False, default=0, type=int,
                        help='Validity for Limit sample: default 0 days')

    return parser.parse_args()


if __name__ == '__main__':
    sys.argv = [sys.argv[0], '-p', '-wcsv', '-pr', '--stake', '1', '-e', 'Market']

    runstrategy()