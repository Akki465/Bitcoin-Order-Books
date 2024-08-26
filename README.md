# Bitcoin-Order-Books

The Python script subscribes to the websocket streams of some of the most liquid crypto exchanges (using the **websockets** library), and concurrently (using the **asyncio** library) reads incoming order book data.\
HTML file displays the bid and ask data (updated every 500ms) of each exchange's order book, as well as the aggregate Bitcoin order book, using **ChartJS**
