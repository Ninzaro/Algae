"""Pure, vectorized quantitative indicators for technical analysis and systematic signal generation.

All routines accept lists, numpy arrays, or pandas Series and produce clean, typed outputs
without side effects.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True, slots=True)
class BollingerBands:
    upper: list[float]
    middle: list[float]
    lower: list[float]
    bandwidth: list[float]
    percent_b: list[float]


@dataclass(frozen=True, slots=True)
class MacdResult:
    macd_line: list[float]
    signal_line: list[float]
    histogram: list[float]


@dataclass(frozen=True, slots=True)
class VolumeProfileBin:
    price_low: float
    price_high: float
    price_mid: float
    volume: float


@dataclass(frozen=True, slots=True)
class VolumeProfileResult:
    poc: float  # Point of Control (price level with highest volume)
    vah: float  # Value Area High
    val: float  # Value Area Low
    total_volume: float
    bins: list[VolumeProfileBin]


@dataclass(frozen=True, slots=True)
class SupertrendResult:
    trend: list[int]  # 1 for bullish (long), -1 for bearish (short)
    upper_band: list[float]
    lower_band: list[float]
    supertrend: list[float]


def sma(values: Sequence[float], window: int) -> list[float]:
    """Simple Moving Average."""
    n = len(values)
    if n == 0 or window <= 0:
        return []
    if window > n:
        return [float("nan")] * n

    result: list[float] = [float("nan")] * (window - 1)
    current_sum = sum(values[:window])
    result.append(current_sum / window)

    for i in range(window, n):
        current_sum += values[i] - values[i - window]
        result.append(current_sum / window)

    return result


def ema(values: Sequence[float], window: int, smoothing: float = 2.0) -> list[float]:
    """Exponential Moving Average."""
    n = len(values)
    if n == 0 or window <= 0:
        return []
    if window > n:
        return [float("nan")] * n

    result: list[float] = [float("nan")] * (window - 1)
    # Seed EMA with initial SMA
    initial_sma = sum(values[:window]) / window
    result.append(initial_sma)

    multiplier = smoothing / (window + 1.0)
    current_ema = initial_sma

    for i in range(window, n):
        current_ema = (values[i] - current_ema) * multiplier + current_ema
        result.append(current_ema)

    return result


def atr(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    window: int = 14,
) -> list[float]:
    """Average True Range (Wilder's Smoothing)."""
    n = len(close)
    if n == 0 or len(high) != n or len(low) != n or window <= 0:
        return []
    if n < window:
        return [float("nan")] * n

    tr: list[float] = [high[0] - low[0]]
    for i in range(1, n):
        h_l = high[i] - low[i]
        h_pc = abs(high[i] - close[i - 1])
        l_pc = abs(low[i] - close[i - 1])
        tr.append(max(h_l, h_pc, l_pc))

    if n < window:
        return [float("nan")] * n

    result: list[float] = [float("nan")] * (window - 1)
    # Initial ATR is simple average of first `window` TRs
    initial_atr = sum(tr[:window]) / window
    result.append(initial_atr)

    current_atr = initial_atr
    for i in range(window, n):
        current_atr = (current_atr * (window - 1) + tr[i]) / window
        result.append(current_atr)

    return result


def bollinger_bands(
    values: Sequence[float],
    window: int = 20,
    num_std: float = 2.0,
) -> BollingerBands:
    """Bollinger Bands with Upper, Middle, Lower, Bandwidth, and %B."""
    n = len(values)
    if n == 0 or window <= 0:
        return BollingerBands([], [], [], [], [])

    mid = sma(values, window)
    upper: list[float] = []
    lower: list[float] = []
    bandwidth: list[float] = []
    pct_b: list[float] = []

    for i in range(n):
        if i < window - 1 or mid[i] != mid[i]:  # NaN check
            upper.append(float("nan"))
            lower.append(float("nan"))
            bandwidth.append(float("nan"))
            pct_b.append(float("nan"))
            continue

        window_vals = values[i - window + 1 : i + 1]
        m = mid[i]
        var = sum((x - m) ** 2 for x in window_vals) / window
        std = sqrt(max(var, 0.0))

        u = m + num_std * std
        lower_val = m - num_std * std
        bw = (u - lower_val) / m if m != 0 else 0.0
        pb = (values[i] - lower_val) / (u - lower_val) if (u - lower_val) != 0 else 0.5

        upper.append(u)
        lower.append(lower_val)
        bandwidth.append(bw)
        pct_b.append(pb)

    return BollingerBands(
        upper=upper,
        middle=mid,
        lower=lower,
        bandwidth=bandwidth,
        percent_b=pct_b,
    )


def rsi(values: Sequence[float], window: int = 14) -> list[float]:
    """Relative Strength Index (Wilder's Smoothing). Output bounded [0, 100]."""
    n = len(values)
    if n <= window or window <= 0:
        return [float("nan")] * n

    gains: list[float] = [0.0]
    losses: list[float] = [0.0]
    for i in range(1, n):
        change = values[i] - values[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    result: list[float] = [float("nan")] * window
    avg_gain = sum(gains[1 : window + 1]) / window
    avg_loss = sum(losses[1 : window + 1]) / window

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(window + 1, n):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))

    return result


def macd(
    values: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> MacdResult:
    """Moving Average Convergence Divergence (MACD)."""
    n = len(values)
    if n == 0 or fast <= 0 or slow <= 0 or fast >= slow or signal_period <= 0:
        return MacdResult([], [], [])

    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)

    macd_line: list[float] = []
    for f, s in zip(fast_ema, slow_ema, strict=True):
        if f != f or s != s:  # NaN check
            macd_line.append(float("nan"))
        else:
            macd_line.append(f - s)

    # Valid macd values after slow window
    valid_macd_start = slow - 1
    valid_macd = macd_line[valid_macd_start:]
    sig_raw = ema(valid_macd, signal_period)

    signal_line: list[float] = [float("nan")] * valid_macd_start + sig_raw
    histogram: list[float] = []

    for m, sig in zip(macd_line, signal_line, strict=True):
        if m != m or sig != sig:
            histogram.append(float("nan"))
        else:
            histogram.append(m - sig)

    return MacdResult(macd_line=macd_line, signal_line=signal_line, histogram=histogram)


def supertrend(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    period: int = 10,
    multiplier: float = 3.0,
) -> SupertrendResult:
    """Supertrend indicator. Returns trend (+1/-1), upper band, lower band, and trailing stop line."""
    n = len(close)
    if n == 0 or len(high) != n or len(low) != n or period <= 0:
        return SupertrendResult([], [], [], [])

    atr_vals = atr(high, low, close, window=period)
    trend: list[int] = [1] * n
    upper_band: list[float] = [0.0] * n
    lower_band: list[float] = [0.0] * n
    st: list[float] = [0.0] * n

    for i in range(n):
        hl2 = (high[i] + low[i]) / 2.0
        curr_atr = atr_vals[i]

        if curr_atr != curr_atr:  # NaN warmup
            upper_band[i] = hl2
            lower_band[i] = hl2
            st[i] = hl2
            trend[i] = 1
            continue

        basic_upper = hl2 + multiplier * curr_atr
        basic_lower = hl2 - multiplier * curr_atr

        if i == 0 or atr_vals[i - 1] != atr_vals[i - 1]:
            upper_band[i] = basic_upper
            lower_band[i] = basic_lower
            trend[i] = 1
            st[i] = lower_band[i]
            continue

        # Final Upper Band
        if basic_upper < upper_band[i - 1] or close[i - 1] > upper_band[i - 1]:
            upper_band[i] = basic_upper
        else:
            upper_band[i] = upper_band[i - 1]

        # Final Lower Band
        if basic_lower > lower_band[i - 1] or close[i - 1] < lower_band[i - 1]:
            lower_band[i] = basic_lower
        else:
            lower_band[i] = lower_band[i - 1]

        # Trend and Supertrend value
        prev_trend = trend[i - 1]
        if prev_trend == 1:
            if close[i] < lower_band[i]:
                trend[i] = -1
                st[i] = upper_band[i]
            else:
                trend[i] = 1
                st[i] = lower_band[i]
        else:
            if close[i] > upper_band[i]:
                trend[i] = 1
                st[i] = lower_band[i]
            else:
                trend[i] = -1
                st[i] = upper_band[i]

    return SupertrendResult(
        trend=trend,
        upper_band=upper_band,
        lower_band=lower_band,
        supertrend=st,
    )


def donchian_channel(
    high: Sequence[float],
    low: Sequence[float],
    window: int = 20,
) -> tuple[list[float], list[float], list[float]]:
    """Donchian Channel: Upper Band (Highest High), Middle Band, Lower Band (Lowest Low)."""
    n = len(high)
    if n == 0 or len(low) != n or window <= 0:
        return [], [], []

    upper: list[float] = [float("nan")] * (window - 1)
    lower: list[float] = [float("nan")] * (window - 1)
    mid: list[float] = [float("nan")] * (window - 1)

    for i in range(window - 1, n):
        h = max(high[i - window + 1 : i + 1])
        low_val = min(low[i - window + 1 : i + 1])
        upper.append(h)
        lower.append(low_val)
        mid.append((h + low_val) / 2.0)

    return upper, mid, lower


def volume_profile(
    price: Sequence[float],
    volume: Sequence[float],
    num_bins: int = 24,
    value_area_pct: float = 0.70,
) -> VolumeProfileResult:
    """Calculates Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL)."""
    n = len(price)
    if n == 0 or len(volume) != n or num_bins <= 0:
        return VolumeProfileResult(0.0, 0.0, 0.0, 0.0, [])

    min_p = min(price)
    max_p = max(price)
    total_vol = sum(volume)

    if min_p == max_p or total_vol == 0:
        single_bin = VolumeProfileBin(min_p, max_p, min_p, total_vol)
        return VolumeProfileResult(min_p, max_p, min_p, total_vol, [single_bin])

    bin_width = (max_p - min_p) / num_bins
    bin_vols = [0.0] * num_bins

    for p, v in zip(price, volume, strict=True):
        idx = int((p - min_p) / bin_width)
        if idx >= num_bins:
            idx = num_bins - 1
        bin_vols[idx] += v

    bins = [
        VolumeProfileBin(
            price_low=min_p + i * bin_width,
            price_high=min_p + (i + 1) * bin_width,
            price_mid=min_p + (i + 0.5) * bin_width,
            volume=bin_vols[i],
        )
        for i in range(num_bins)
    ]

    # POC is bin with highest volume
    max_idx = max(range(num_bins), key=lambda i: bin_vols[i])
    poc = bins[max_idx].price_mid

    # Value area accumulation around POC
    target_vol = total_vol * value_area_pct
    accumulated_vol = bin_vols[max_idx]
    up_idx = max_idx
    down_idx = max_idx

    while accumulated_vol < target_vol and (up_idx < num_bins - 1 or down_idx > 0):
        next_up_vol = bin_vols[up_idx + 1] if up_idx < num_bins - 1 else 0.0
        next_down_vol = bin_vols[down_idx - 1] if down_idx > 0 else 0.0

        if next_up_vol >= next_down_vol and up_idx < num_bins - 1:
            up_idx += 1
            accumulated_vol += next_up_vol
        elif down_idx > 0:
            down_idx -= 1
            accumulated_vol += next_down_vol
        elif up_idx < num_bins - 1:
            up_idx += 1
            accumulated_vol += next_up_vol
        else:
            break

    val = bins[down_idx].price_low
    vah = bins[up_idx].price_high

    return VolumeProfileResult(
        poc=poc,
        vah=vah,
        val=val,
        total_volume=total_vol,
        bins=bins,
    )


def zscore(values: Sequence[float], window: int = 20) -> list[float]:
    """Rolling Z-Score (standardized distance from moving average)."""
    n = len(values)
    if n == 0 or window <= 0:
        return []
    if window > n:
        return [float("nan")] * n

    mid = sma(values, window)
    result: list[float] = []

    for i in range(n):
        if i < window - 1 or mid[i] != mid[i]:
            result.append(float("nan"))
            continue

        window_vals = values[i - window + 1 : i + 1]
        m = mid[i]
        var = sum((x - m) ** 2 for x in window_vals) / window
        std = sqrt(max(var, 0.0))
        if std == 0:
            result.append(0.0)
        else:
            result.append((values[i] - m) / std)

    return result


def realized_volatility(
    values: Sequence[float],
    window: int = 20,
    annualization_factor: float = 252.0,
) -> list[float]:
    """Annualized rolling realized volatility of returns."""
    n = len(values)
    if n <= 1 or window <= 1:
        return [float("nan")] * n

    # Log/simple returns
    returns: list[float] = [0.0]
    for i in range(1, n):
        prev = values[i - 1]
        returns.append((values[i] - prev) / prev if prev > 0 else 0.0)

    result: list[float] = [float("nan")] * (window - 1)
    ann_mult = sqrt(annualization_factor)

    for i in range(window - 1, n):
        window_ret = returns[i - window + 1 : i + 1]
        mean_ret = sum(window_ret) / window
        var = sum((r - mean_ret) ** 2 for r in window_ret) / (window - 1)
        vol = sqrt(max(var, 0.0)) * ann_mult
        result.append(vol)

    return result
