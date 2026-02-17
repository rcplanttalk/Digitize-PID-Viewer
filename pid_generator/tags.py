"""Tag builders for P&ID components (§13)."""

from pid_generator.constants import PIPE_SIZES, PIPE_SPEC_CODES


def build_pipe_tag(size: int, spec: str, seq: int) -> str:
    """Return a pipe tag string, e.g. ``'8-AB-0042'``.

    Args:
        size: Nominal pipe size in inches; must be in PIPE_SIZES.
        spec: Pipe spec code; must be in PIPE_SPEC_CODES.
        seq:  Unique sequence number for this pipe run.
    """
    if size not in PIPE_SIZES:
        msg = f"size {size} not in PIPE_SIZES {PIPE_SIZES}"
        raise ValueError(msg)
    if spec not in PIPE_SPEC_CODES:
        msg = f"spec '{spec}' not in PIPE_SPEC_CODES {PIPE_SPEC_CODES}"
        raise ValueError(msg)
    return f"{size}-{spec}-{seq:04d}"


def build_component_tag(prefix: str, seq: int) -> str:
    """Return a component tag string, e.g. ``'GV-042'``.

    Args:
        prefix: Component prefix (valve, instrument, or equipment prefix).
        seq:    Unique sequence number within this prefix group per diagram.
    """
    return f"{prefix}-{seq:03d}"
