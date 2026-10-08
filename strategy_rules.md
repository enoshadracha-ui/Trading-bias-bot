# Trading Bias Bot — Final Strategy Scope

## Daily

The bot first works from the **line-chart structure**.

Key levels:
1. Resistance — A-Shape
2. Support — V-Shape
3. RBS — Resistance Becomes Support
4. SBR — Support Becomes Resistance
5. OCL — Open-Close Level

The latest completed Daily candle must interact with a relevant level and reject/close away from that level.

A bullish rejection establishes the bullish Daily direction.
A bearish rejection establishes the bearish Daily direction.

## 4H

The bot then looks for the confirmation that caused the breakout.

### Inefficient bullish price action

A bullish breakout should be produced by **multiple bullish candles / directional displacement**, and that same movement must contain one or more bullish imbalances/FVGs.

This is the inefficient bullish price action.

### Inefficient bearish price action

The inverse:
multiple bearish candles / directional displacement produce the breakout, and that same movement contains one or more bearish imbalances/FVGs.

### Two confirmation scenarios

Either one is sufficient:

A. Liquidity sweep + breakout, with inefficient price action.

B. Most recent breakout, with inefficient price action.

The bot does not require both.

## Explicitly OUTSIDE the bot

The following are NOT detected:
- retracement
- later opposing movement
- entry setup
- entry price
- stop loss
- take profit
- RRR
- trade execution
- trade management

Those are handled by the trader after the bot produces the bias.

## Final output

BULLISH BIAS
BEARISH BIAS
NO BIAS
