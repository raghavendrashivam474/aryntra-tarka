"""
integrations/timeout.py

Centralised timeout configuration for all external integration requests.

Plugins declare a TimeoutPolicy rather than passing raw seconds to HTTP
calls.  This keeps timeout behaviour consistent and makes it easy to
adjust defaults platform-wide without touching individual plugins.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONNECT_SECONDS: float = 5.0
DEFAULT_READ_SECONDS: float    = 10.0
DEFAULT_TOTAL_SECONDS: float   = 15.0


# ---------------------------------------------------------------------------
# TimeoutPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeoutPolicy:
    """
    Immutable timeout configuration for a single integration request.

    Attributes
    ----------
    connect_seconds:
        Maximum time allowed to establish a TCP connection.
    read_seconds:
        Maximum time allowed to receive the response body after
        the connection is established.
    total_seconds:
        Hard ceiling on the entire request lifecycle.
        If the request has not completed within this window it is
        cancelled regardless of individual phase timings.

    Usage
    -----
    policy = TimeoutPolicy()                         # platform defaults
    policy = TimeoutPolicy(total_seconds=30.0)       # relaxed for slow APIs
    policy = TimeoutPolicy(connect_seconds=2.0,
                           read_seconds=5.0,
                           total_seconds=7.0)        # tighter bounds
    """

    connect_seconds: float = field(default=DEFAULT_CONNECT_SECONDS)
    read_seconds:    float = field(default=DEFAULT_READ_SECONDS)
    total_seconds:   float = field(default=DEFAULT_TOTAL_SECONDS)

    def __post_init__(self) -> None:
        """Validate that all timeout values are positive."""
        for name, value in [
            ("connect_seconds", self.connect_seconds),
            ("read_seconds",    self.read_seconds),
            ("total_seconds",   self.total_seconds),
        ]:
            if value <= 0:
                raise ValueError(
                    f"TimeoutPolicy.{name} must be positive, got {value}"
                )

    def as_httpx_timeout(self) -> dict[str, float]:
        """
        Return a dictionary compatible with httpx.Timeout keyword arguments.

        Example
        -------
        import httpx
        policy = TimeoutPolicy()
        timeout = httpx.Timeout(**policy.as_httpx_timeout())
        """
        return {
            "connect": self.connect_seconds,
            "read":    self.read_seconds,
            "write":   self.total_seconds,
            "pool":    self.total_seconds,
        }


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def default_timeout() -> TimeoutPolicy:
    """Return the platform-default TimeoutPolicy."""
    return TimeoutPolicy()


def relaxed_timeout() -> TimeoutPolicy:
    """
    Return a more generous TimeoutPolicy for providers known to be slow.

    Intended for: large data providers, translation services, map APIs.
    """
    return TimeoutPolicy(
        connect_seconds=10.0,
        read_seconds=30.0,
        total_seconds=40.0,
    )


def strict_timeout() -> TimeoutPolicy:
    """
    Return a tight TimeoutPolicy for latency-sensitive integrations.

    Intended for: real-time feeds, currency rates, flight status.
    """
    return TimeoutPolicy(
        connect_seconds=2.0,
        read_seconds=4.0,
        total_seconds=6.0,
    )
