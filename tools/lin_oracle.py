"""Independent electrical oracle for the committed LIN_BREAK_SYNC_ENTRY scope.

Only the resolved receive line, lifecycle boundaries, public FIFO endpoints,
host reads, and output-enable masks enter this module.  It neither imports a
MOTIF decoder nor consumes an execution graph, counter, timer, or primitive
trace.  Samples are consecutive core observations: index ``t`` describes the
held line level at observation ``t``.  LOW intervals use half-open [start, end)
coordinates, so their sample count is exactly end - start.

The adopted contract is experiments/temporal_qualification/unseen/
selected_workload.json (selection commit 5f67d888df07a7e76f814a8df9984394a951f7ac).
Its source is LIN 2.2A, sections 2.3.1--2.3.1.2, printed pages 29--31.  FIFO
latency and token value are experiment criteria, not LIN response requirements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class LinContract:
    """Nominal sample-grid contract; explicit small values support unit fixtures.

    Qualification must construct this with ``from_selection``.  That method
    rejects changed adopted constants; a direct constructor is useful for
    independent, small electrical examples without changing the selection.
    """

    bit_cycles: int = 2500
    break_observations: int = 27500
    sync_value: int = 0x55
    token_value: int = 0x55
    posttraffic_high_cycles: int = 5000
    latency_bit_periods: int = 2

    def __post_init__(self) -> None:
        for name in ("bit_cycles", "break_observations", "posttraffic_high_cycles"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.latency_bit_periods, int) or self.latency_bit_periods < 0:
            raise ValueError("latency_bit_periods must be a nonnegative integer")
        for name in ("sync_value", "token_value"):
            value = getattr(self, name)
            if not isinstance(value, int) or not 0 <= value <= 255:
                raise ValueError(f"{name} must be a byte")

    @classmethod
    def from_selection(cls, selection: Mapping[str, object]) -> LinContract:
        """Validate adopted numeric constants directly from the immutable JSON.

        The qualification runner remains responsible for checking the selection
        file's committed LF-normalized SHA-256 and the frozen semantic manifest.
        This check prevents a runner from silently passing alternate constants.
        """
        if selection.get("workload") != "LIN_BREAK_SYNC_ENTRY":
            raise ValueError("selection is not LIN_BREAK_SYNC_ENTRY")
        electrical = selection.get("bounded_electrical_scope")
        host = selection.get("host_and_oracle_inputs")
        if not isinstance(electrical, Mapping) or not isinstance(host, Mapping):
            raise ValueError("selection lacks the adopted electrical/host contract")
        adopted = {
            "core_period_ns": 20,
            "nominal_bit_cycles": 2500,
            "nominal_bit_us": 50,
            "nominal_rate_bps": 20000,
            "receive_pin": 2,
            "inactive_pin_byte": 255,
            "receiver_threshold_observations": 27500,
            "master_generated_minimum_break_cycles": 32500,
            "delimiter_cycles": 3000,
            "sync_value": 85,
            "accepted_public_token": 85,
        }
        for name, value in adopted.items():
            if electrical.get(name) != value:
                raise ValueError(f"selected constant {name} changed from {value}")
        for name, value in {"initial_high_cycles": 20000, "posttraffic_high_cycles": 5000}.items():
            if host.get(name) != value:
                raise ValueError(f"selected constant {name} changed from {value}")
        return cls()


@dataclass(frozen=True)
class ExpectedToken:
    value: int
    break_start: int
    break_end: int
    byte_start: int
    stop_start: int
    stop_end: int
    earliest: int
    latest: int
    epoch: int


@dataclass(frozen=True)
class FifoSample:
    """Public RX FIFO occupancy/head immediately after core observation cycle."""

    cycle: int
    count: int
    head: int | None = None


@dataclass(frozen=True)
class HostRead:
    """External pop at cycle, carrying the PRE-edge public head (None if empty)."""

    cycle: int
    value: int | None


@dataclass(frozen=True)
class ObservedAcceptance:
    cycle: int
    public_head: int | None


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    cycle: int | None = None


@dataclass(frozen=True)
class Evaluation:
    expected: tuple[ExpectedToken, ...]
    observed_acceptances: tuple[ObservedAcceptance, ...]
    errors: tuple[Violation, ...]

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["passed"] = self.passed
        return result


def _electrical_samples(line_levels: Sequence[int]) -> tuple[int, ...]:
    levels = tuple(line_levels)
    for cycle, level in enumerate(levels):
        if level not in (0, 1):
            raise ValueError(f"receive line is not resolved LOW/HIGH at cycle {cycle}")
    return levels


def _epoch_boundaries(lifecycle_cuts: Iterable[int], length: int) -> tuple[int, ...]:
    cuts = set(lifecycle_cuts)
    if any(not isinstance(cut, int) or isinstance(cut, bool) or not 0 <= cut <= length
           for cut in cuts):
        raise ValueError("lifecycle cuts must be integer sample boundaries within the trace")
    return tuple(sorted({0, length, *cuts}))


def _low_runs(levels: Sequence[int], begin: int, end: int) -> list[tuple[int, int]]:
    runs = []
    cursor = begin
    while cursor < end:
        if levels[cursor] == 1:
            cursor += 1
            continue
        low_start = cursor
        while cursor < end and levels[cursor] == 0:
            cursor += 1
        runs.append((low_start, cursor))
    return runs


def reference(
    line_levels: Sequence[int],
    lifecycle_cuts: Iterable[int] = (),
    contract: LinContract = LinContract(),
) -> tuple[ExpectedToken, ...]:
    """Find expected tokens solely from maximal LOW runs and nominal byte centers.

    Each lifecycle cut occurs before the sample at that index and starts a new
    epoch, including when LOW is held through the cut.  A qualified LOW requires
    a HIGH release in the same epoch.  Its immediately following LOW transition
    is the only candidate byte start.  If that LOW itself reaches the break
    threshold, it is a fresh separated break and replaces the pending header.
    A wrong byte or stop never retains the old qualification for a later 0x55.

    The byte sample at cell k is floor(start + (k + 1/2) B), k=0..9.  No autobaud,
    maximum break duration, or strict delimiter-duration rejection is added.
    """
    levels = _electrical_samples(line_levels)
    boundaries = _epoch_boundaries(lifecycle_cuts, len(levels))
    expected = []
    bit = contract.bit_cycles
    for epoch, (begin, end) in enumerate(zip(boundaries, boundaries[1:])):
        runs = _low_runs(levels, begin, end)
        for index, (low_start, low_end) in enumerate(runs):
            if low_end - low_start < contract.break_observations or low_end == end:
                continue
            if index + 1 == len(runs):
                continue  # No subsequent falling transition in this epoch.
            byte_start, first_low_end = runs[index + 1]
            if first_low_end - byte_start >= contract.break_observations:
                continue  # A new break replaces the old pending byte.
            centers = [byte_start + ((2 * cell + 1) * bit) // 2 for cell in range(10)]
            if centers[-1] >= end:
                continue  # Lifecycle/end-of-trace interrupts this prefix.
            if levels[centers[0]] != 0 or levels[centers[9]] != 1:
                continue
            value = sum(levels[centers[cell + 1]] << cell for cell in range(8))
            if value != contract.sync_value:
                continue
            stop_start = byte_start + 9 * bit
            stop_end = byte_start + 10 * bit
            expected.append(ExpectedToken(
                value=contract.token_value,
                break_start=low_start,
                break_end=low_end,
                byte_start=byte_start,
                stop_start=stop_start,
                stop_end=stop_end,
                earliest=stop_start,
                latest=stop_end + contract.latency_bit_periods * bit,
                epoch=epoch,
            ))
    return tuple(expected)


def evaluate(
    line_levels: Sequence[int],
    lifecycle_cuts: Iterable[int],
    contract: LinContract,
    fifo_samples: Sequence[FifoSample],
    host_reads: Sequence[HostRead],
    target_oe: Sequence[int],
    traffic_end: int,
) -> Evaluation:
    """Check the bounded public behavior against the independent electrical scan.

    FIFO and OE observations must cover every line sample, starting at cycle 0.
    ``traffic_end`` is the first cycle after controller traffic.  Host pops must
    wait the adopted HIGH margin; each pop is checked against the previous FIFO
    row.  Positive occupancy changes (including a write simultaneous with an
    external pop) identify acceptance timestamps.  The FIFO starts empty.

    Only the first witness of each violation code is retained, so a persistent
    wrong head or asserted OE does not produce an unbounded error receipt.
    """
    cuts = tuple(lifecycle_cuts)
    expected = reference(line_levels, cuts, contract)
    length = len(line_levels)
    if not isinstance(traffic_end, int) or not 0 <= traffic_end <= length:
        raise ValueError("traffic_end must be a sample boundary within the trace")
    errors: list[Violation] = []
    seen_codes: set[str] = set()

    def fail(code: str, message: str, cycle: int | None = None) -> None:
        if code not in seen_codes:
            errors.append(Violation(code, message, cycle))
            seen_codes.add(code)

    drain_start = traffic_end + contract.posttraffic_high_cycles
    if length < drain_start:
        fail("short_observation", "Trace ends before the required posttraffic HIGH margin")
    if any(level != 1 for level in line_levels[traffic_end:min(drain_start, length)]):
        fail("nonhigh_margin", "Posttraffic observation margin is not continuously HIGH")
    if len(target_oe) != length:
        fail("incomplete_oe_observation", "OE observations do not cover the complete line trace")
    for cycle, oe in enumerate(target_oe):
        if oe != 0:
            fail("output_enabled", f"Receive-only target asserted output-enable mask {oe}", cycle)
            break
    rows = tuple(fifo_samples)
    if len(rows) != length or any(row.cycle != index for index, row in enumerate(rows)):
        fail("incomplete_fifo_observation", "FIFO observations must be dense cycle 0..N-1")
    by_cycle = {row.cycle: row for row in rows}
    reads_by_cycle: dict[int, HostRead] = {}
    previous_read_cycle = -1
    for read in host_reads:
        if not isinstance(read.cycle, int) or read.cycle <= previous_read_cycle:
            fail("unordered_host_reads", "Host reads must have distinct increasing timestamps", read.cycle)
        previous_read_cycle = read.cycle
        reads_by_cycle[read.cycle] = read
        if not drain_start <= read.cycle < length:
            fail("host_read_timing", "Host read occurred outside the posttraffic drain", read.cycle)
        before = by_cycle.get(read.cycle - 1)
        if before is None:
            fail("unobserved_host_read", "PRE-edge FIFO endpoint is absent for host read", read.cycle)
        else:
            public_value = before.head if before.count > 0 else None
            if read.value != public_value:
                fail("host_read_mismatch", "Read value differs from the PRE-edge public FIFO endpoint", read.cycle)
    observed: list[ObservedAcceptance] = []
    previous_count = 0
    cut_set = set(cuts)
    for row in rows:
        if not isinstance(row.count, int) or row.count < 0:
            fail("invalid_fifo_count", "Public FIFO occupancy is not a nonnegative integer", row.cycle)
            continue
        if row.count > 0 and row.head != contract.token_value:
            fail("wrong_public_head", f"Nonempty public FIFO head is {row.head}, expected {contract.token_value}", row.cycle)
        read = reads_by_cycle.get(row.cycle)
        expected_pop = int(read is not None and previous_count > 0)
        produced = row.count - previous_count + expected_pop
        if row.cycle in cut_set and row.count < previous_count and read is None:
            produced = 0  # An external lifecycle event may clear the public FIFO.
        if produced < 0:
            fail("unexpected_fifo_loss", "FIFO occupancy decreased without the corresponding public pop", row.cycle)
        for _ in range(max(0, produced)):
            token_index = len(observed)
            observed.append(ObservedAcceptance(row.cycle, row.head))
            if token_index >= len(expected):
                code = "duplicate_token" if expected else "spurious_token"
                fail(code, "Public FIFO accepted more tokens than the electrical oracle", row.cycle)
            else:
                wanted = expected[token_index]
                if row.cycle < wanted.earliest:
                    fail("early_token", f"Token preceded stop-cell start {wanted.earliest}", row.cycle)
                elif row.cycle > wanted.latest:
                    fail("late_token", f"Token missed latest availability {wanted.latest}", row.cycle)
        previous_count = row.count
    if len(observed) < len(expected):
        fail("missing_token", f"Expected {len(expected)} acceptances, observed {len(observed)}")
    for index, wanted in enumerate(expected):
        if index >= len(host_reads) or host_reads[index].value is None:
            fail("missing_read", f"Expected token {index} was absent from the posttraffic reads")
        elif host_reads[index].value != wanted.value:
            fail("wrong_token", f"Host read token {index} is {host_reads[index].value}, expected {wanted.value}", host_reads[index].cycle)
    if any(read.value is not None for read in host_reads[len(expected):]):
        fail("extra_read_token", "Host drain returned an extra token")
    if rows and rows[-1].count != 0:
        fail("occupancy_remaining", f"Public FIFO retains {rows[-1].count} tokens after drain", rows[-1].cycle)
    return Evaluation(expected, tuple(observed), tuple(errors))
