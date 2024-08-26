# Bitcoin-Order-Books

This repository includes a Python script and an HTML file.\
The Python script subscribes to the websocket streams of some of the most liquid crypto exchanges (using the **websockets** library), and concurrently (using the **asyncio** library) reads incoming order book data.\
Can locally host the front-end of the application using the HTML file - displays the state for each exchange's order book, as well as the aggregate Bitcoin order book, using **ChartJS**
