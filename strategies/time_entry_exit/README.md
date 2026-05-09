# timed_entry_exit

A simple timed buy-and-sell lifecycle test strategy.

## Purpose

This strategy is designed to test the next stage of the trading system:

1. Start strategy
2. Wait a few seconds
3. Submit one market BUY order
4. Hold for a fixed time
5. Submit one market SELL order
6. Stop

It does not rely on bid/ask quote data, because IB paper delayed quote data may not always populate usable bid/ask values.

## Default behaviour

- Symbol: AAPL.NASDAQ
- Quantity: 1 share
- Buy after: 5 seconds
- Sell after: 60 seconds
- Maximum orders per run: 2

## Safety

The strategy respects the `ENABLE_ORDER_PLACEMENT` environment variable.

If order placement is disabled, it logs what it would have done but does not send orders.

## Logs

Event log:

```text
logs/strategies/timed_entry_exit_events.log