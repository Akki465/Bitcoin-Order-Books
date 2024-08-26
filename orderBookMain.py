import asyncio
import json
from sortedcontainers import SortedDict
import websockets

class OrderBook:
    def __init__(self):
        self.bids = SortedDict(lambda price: -price)  # Bids sorted in descending order
        self.asks = SortedDict()  # Asks sorted in ascending order

    async def update(self, side, price, quantity):
        if quantity == 0:
            if price in self.bids:
                del self.bids[price]
            elif price in self.asks:
                del self.asks[price]
        else:
            if side == 'bid':
                self.bids[price] = quantity
            elif side == 'ask':
                self.asks[price] = quantity

class AggregateOrderBook:
    def __init__(self):
        self.bids = SortedDict(lambda price: -price)
        self.asks = SortedDict()

    async def update(self, side, price, quantity):
        if quantity == 0:
            if price in self.bids:
                del self.bids[price]
            elif price in self.asks:
                del self.asks[price]
        else:
            if side == 'bid':
                if price in self.bids:
                    self.bids[price] += quantity
                else:
                    self.bids[price] = quantity
            elif side == 'ask':
                if price in self.asks:
                    self.asks[price] += quantity
                else:
                    self.asks[price] = quantity

async def binance_ws(order_book, aggregate_order_book, stop_event):
    uri = "wss://stream.binance.com/ws/btcusdt@depth@100ms"
    async with websockets.connect(uri) as websocket:
        while not stop_event.is_set():
            data = await websocket.recv()
            data = json.loads(data)
            for update in data['b']:  # Bids
                await order_book.update('bid', float(update[0]), float(update[1]))
                await aggregate_order_book.update('bid', float(update[0]), float(update[1]))
            for update in data['a']:  # Asks
                await order_book.update('ask', float(update[0]), float(update[1]))
                await aggregate_order_book.update('ask', float(update[0]), float(update[1]))

async def bybit_ws(order_book, aggregate_order_book, stop_event):
    uri = "wss://stream.bybit.com/v5/public/spot"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"op": "subscribe", "args": ["orderbook.50.BTCUSDT"]}))
        while not stop_event.is_set():
            data = await websocket.recv()
            data = json.loads(data)
            if 'data' in data:
                for update in data['data']['b']:
                    await order_book.update('bid', float(update[0]), float(update[1]))
                    await aggregate_order_book.update('bid', float(update[0]), float(update[1]))
                for update in data['data']['a']:
                    await order_book.update('ask', float(update[0]), float(update[1]))
                    await aggregate_order_book.update('ask', float(update[0]), float(update[1]))

async def okx_ws(order_book, aggregate_order_book, stop_event):
    uri = "wss://ws.okx.com:8443/ws/v5/public"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"op": "subscribe", "args": [{"channel": "books", "instId": "BTC-USDT"}]}))
        while not stop_event.is_set():
            data = await websocket.recv()
            data = json.loads(data)
            if 'data' in data:
                for update in data['data'][0]['bids']:
                    await order_book.update('bid', float(update[0]), float(update[1]))
                    await aggregate_order_book.update('bid', float(update[0]), float(update[1]))
                for update in data['data'][0]['asks']:
                    await order_book.update('ask', float(update[0]), float(update[1]))
                    await aggregate_order_book.update('ask', float(update[0]), float(update[1]))

async def order_book_server(websocket, path, order_books, aggregate_order_book):
    while True:
        await asyncio.sleep(1)  # Send updates every 2 seconds
        data = {
            'binance': {
                'bids': filter_bids(order_books['binance'].bids),
                'asks': filter_asks(order_books['binance'].asks)
            },
            'bybit': {
                'bids': filter_bids(order_books['bybit'].bids),
                'asks': filter_asks(order_books['bybit'].asks)
            },
            'okx': {
                'bids': filter_bids(order_books['okx'].bids),
                'asks': filter_asks(order_books['okx'].asks)
            },
            'aggregate': {
                'bids': filter_bids(aggregate_order_book.bids),
                'asks': filter_asks(aggregate_order_book.asks)
            }
        }
        await websocket.send(json.dumps(data))

def filter_bids(bids):
    highest_bid = next(iter(bids), None)
    if highest_bid is not None:
        return [(price, quantity) for price, quantity in bids.items() if price >= highest_bid * 0.99]
    return []

def filter_asks(asks):
    lowest_ask = next(iter(asks), None)
    if lowest_ask is not None:
        return [(price, quantity) for price, quantity in asks.items() if price <= lowest_ask * 1.01]
    return []

async def main():
    binance_order_book = OrderBook()
    bybit_order_book = OrderBook()
    okx_order_book = OrderBook()
    aggregate_order_book = AggregateOrderBook()

    order_books = {
        'binance': binance_order_book,
        'bybit': bybit_order_book,
        'okx': okx_order_book
    }

    stop_event = asyncio.Event()

    binance_task = asyncio.create_task(binance_ws(binance_order_book, aggregate_order_book, stop_event))
    bybit_task = asyncio.create_task(bybit_ws(bybit_order_book, aggregate_order_book, stop_event))
    okx_task = asyncio.create_task(okx_ws(okx_order_book, aggregate_order_book, stop_event))

    server = await websockets.serve(lambda ws, path: order_book_server(ws, path, order_books, aggregate_order_book), 'localhost', 8765)

    await asyncio.gather(binance_task, bybit_task, okx_task)

    await server.wait_closed()

asyncio.run(main())