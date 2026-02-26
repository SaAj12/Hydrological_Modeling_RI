"""
Shared conventions for all time-series charts in this project.
- X-axis: 1 Jan 1950 – 31 Dec 2025, year labels every 10 years (matches discharge chart)
- Figure size: 12×4 inches (single panel); multi-panel uses FIG_WIDTH × (FIG_HEIGHT × nrows)
"""
from datetime import datetime

X_MIN = datetime(1950, 1, 1)
X_MAX = datetime(2025, 12, 31, 23, 59, 59)

FIG_WIDTH = 12
FIG_HEIGHT = 4
FIG_SIZE = (FIG_WIDTH, FIG_HEIGHT)


def apply_chart_xaxis(ax, set_limits=True, use_date2num=False):
    """
    Apply standard x-axis: years as labels, 10-year increment.
    If set_limits=True, set xlim to X_MIN–X_MAX (matches discharge chart).
    """
    import matplotlib.dates as mdates
    if set_limits:
        if use_date2num:
            ax.set_xlim(mdates.date2num(X_MIN), mdates.date2num(X_MAX))
        else:
            ax.set_xlim(X_MIN, X_MAX)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(10))
