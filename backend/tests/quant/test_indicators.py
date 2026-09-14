"""Unit tests for pure quantitative indicators."""

import math

import pytest

from alphaforge.quant.indicators import (
    atr,
    bollinger_bands,
    donchian_channel,
    ema,
    macd,
    realized_volatility,
    rsi,
    sma,
    supertrend,
    volume_profile,
    zscore,
)


def test_sma_calculation() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = sma(values, window=3)
    assert len(result) == 5
    assert math.isnan(result[0])
    assert math.isnan(result[1])
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)
    assert result[4] == pytest.approx(4.0)


def test_ema_calculation() -> None:
    values = [10.0, 11.0, 12.0, 13.0, 14.0]
    result = ema(values, window=3)
    assert len(result) == 5
    assert math.isnan(result[0])
    assert math.isnan(result[1])
    assert result[2] == pytest.approx(11.0)
    # multiplier = 2 / (3 + 1) = 0.5
    # ema[3] = (13 - 11) * 0.5 + 11 = 12.0
    assert result[3] == pytest.approx(12.0)


def test_atr_calculation() -> None:
    high = [10.0, 12.0, 11.0, 13.0, 15.0]
    low = [9.0, 10.0, 9.5, 11.0, 13.5]
    close = [9.5, 11.5, 10.0, 12.5, 14.0]
    result = atr(high, low, close, window=3)
    assert len(result) == 5
    assert math.isnan(result[0])
    assert math.isnan(result[1])
    assert result[2] > 0
    assert result[3] > 0
    assert result[4] > 0


def test_bollinger_bands() -> None:
    values = [100.0 + i for i in range(30)]
    bb = bollinger_bands(values, window=20, num_std=2.0)
    assert len(bb.upper) == 30
    assert len(bb.lower) == 30
    assert len(bb.middle) == 30
    assert len(bb.bandwidth) == 30
    assert len(bb.percent_b) == 30

    # For valid index: upper > middle > lower
    for i in range(19, 30):
        assert bb.upper[i] > bb.middle[i] > bb.lower[i]
        assert bb.bandwidth[i] > 0
        assert 0.0 <= bb.percent_b[i] <= 1.0


def test_rsi_extremes() -> None:
    # Strictly increasing prices -> RSI near 100
    increasing = [float(i) for i in range(1, 30)]
    rsi_inc = rsi(increasing, window=14)
    assert rsi_inc[-1] == pytest.approx(100.0)

    # Strictly decreasing prices -> RSI near 0
    decreasing = [float(30 - i) for i in range(30)]
    rsi_dec = rsi(decreasing, window=14)
    assert rsi_dec[-1] == pytest.approx(0.0)


def test_macd_calculation() -> None:
    values = [10.0 + (i * 0.5) for i in range(50)]
    res = macd(values, fast=12, slow=26, signal_period=9)
    assert len(res.macd_line) == 50
    assert len(res.signal_line) == 50
    assert len(res.histogram) == 50

    # After warmup, macd line should be positive for trending series
    assert res.macd_line[-1] > 0


def test_supertrend_bullish_and_bearish() -> None:
    # Strong upward trend
    high = [10.0 + i * 2.0 for i in range(25)]
    low = [8.0 + i * 2.0 for i in range(25)]
    close = [9.5 + i * 2.0 for i in range(25)]

    st = supertrend(high, low, close, period=10, multiplier=2.0)
    assert len(st.trend) == 25
    assert st.trend[-1] == 1  # Bullish
    assert st.supertrend[-1] < close[-1]

    # Strong downward reversal
    high_rev = high + [high[-1] - i * 3.0 for i in range(1, 20)]
    low_rev = low + [low[-1] - i * 3.0 for i in range(1, 20)]
    close_rev = close + [close[-1] - i * 3.0 for i in range(1, 20)]

    st_rev = supertrend(high_rev, low_rev, close_rev, period=10, multiplier=2.0)
    assert st_rev.trend[-1] == -1  # Bearish
    assert st_rev.supertrend[-1] > close_rev[-1]


def test_donchian_channel() -> None:
    high = [10.0, 15.0, 12.0, 18.0, 14.0]
    low = [8.0, 9.0, 7.0, 11.0, 10.0]
    upper, mid, lower = donchian_channel(high, low, window=3)
    assert math.isnan(upper[0])
    assert math.isnan(upper[1])
    assert upper[2] == 15.0  # max(10, 15, 12)
    assert lower[2] == 7.0   # min(8, 9, 7)
    assert mid[2] == 11.0    # (15 + 7) / 2
    assert upper[3] == 18.0
    assert lower[3] == 7.0


def test_volume_profile() -> None:
    prices = [100.0, 101.0, 102.0, 101.0, 100.0, 101.0, 101.0]
    volumes = [10.0, 50.0, 15.0, 40.0, 10.0, 60.0, 30.0]
    vp = volume_profile(prices, volumes, num_bins=5, value_area_pct=0.70)
    assert vp.total_volume == sum(volumes)
    assert 100.0 <= vp.poc <= 102.0
    assert vp.val <= vp.poc <= vp.vah


def test_zscore_and_volatility() -> None:
    values = [10.0, 10.5, 9.5, 10.2, 9.8, 10.1, 10.4, 9.6, 10.0, 10.2]
    zs = zscore(values, window=5)
    assert len(zs) == len(values)
    assert not math.isnan(zs[-1])

    vol = realized_volatility(values, window=5)
    assert len(vol) == len(values)
    assert not math.isnan(vol[-1])
    assert vol[-1] > 0
