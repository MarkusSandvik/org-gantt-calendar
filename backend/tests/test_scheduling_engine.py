"""Unit tests for the pure propagation algorithm — no DB, no FastAPI. These
exist ahead of the API-layer tests deliberately: this is the "important
business logic" the project's testing principles call out (date
calculations, dependency propagation, lag handling)."""

import datetime as dt

from app.models.enums import SchedulableType
from app.services.scheduling import ScheduleNode, compute_propagation

D0 = dt.date(2026, 1, 1)

A = (SchedulableType.ACTIVITY, 1)
B = (SchedulableType.ACTIVITY, 2)
C = (SchedulableType.ACTIVITY, 3)
D = (SchedulableType.ACTIVITY, 4)
M = (SchedulableType.MILESTONE, 1)


def node(key, start: dt.date, duration_days: int) -> ScheduleNode:
    return ScheduleNode(key, start, start + dt.timedelta(days=duration_days))


def test_simple_chain_propagates_forward_preserving_duration():
    nodes = {
        A: node(A, D0, 9),  # Jan 1 - Jan 10
        B: node(B, D0 + dt.timedelta(days=10), 9),  # Jan 11 - Jan 20
    }
    adjacency = {A: [(B, 0)]}

    delay = dt.timedelta(days=4)
    new_a_end = nodes[A].end_date + delay
    changes = compute_propagation(nodes, adjacency, A, nodes[A].start_date, new_a_end)

    assert changes[A] == (nodes[A].start_date, new_a_end)
    b_duration = nodes[B].end_date - nodes[B].start_date
    assert changes[B] == (new_a_end, new_a_end + b_duration)


def test_lag_days_are_honored_and_a_satisfied_lag_does_not_push():
    a_start, a_duration = D0, 9
    lag = 2
    # B currently starts exactly at A's end + lag: already satisfied.
    b_start = a_start + dt.timedelta(days=a_duration + lag)
    nodes = {A: node(A, a_start, a_duration), B: node(B, b_start, 8)}
    adjacency = {A: [(B, lag)]}

    # Re-applying the same end date changes nothing for B.
    changes = compute_propagation(nodes, adjacency, A, a_start, nodes[A].end_date)
    assert B not in changes

    # Pushing A's end out by 1 day means B must move forward by exactly 1 day too.
    new_end = nodes[A].end_date + dt.timedelta(days=1)
    changes2 = compute_propagation(nodes, adjacency, A, a_start, new_end)
    assert changes2[B][0] == b_start + dt.timedelta(days=1)


def test_pulling_a_predecessor_earlier_does_not_cascade():
    nodes = {
        A: node(A, D0 + dt.timedelta(days=5), 5),
        B: node(B, D0 + dt.timedelta(days=15), 5),
    }
    adjacency = {A: [(B, 0)]}

    earlier_start = D0
    earlier_end = earlier_start + dt.timedelta(days=2)
    changes = compute_propagation(nodes, adjacency, A, earlier_start, earlier_end)

    assert changes[A] == (earlier_start, earlier_end)
    assert B not in changes  # B's current start already satisfies the earlier requirement


def test_diamond_dependency_converges_on_the_larger_of_two_pushes():
    # A feeds both B and C, which both feed D. Pushing A out should push
    # both B and C, and D should end up driven by whichever of the two
    # pushes it further forward, not the first edge relaxed.
    nodes = {
        A: node(A, D0, 9),  # duration 9
        B: node(B, D0 + dt.timedelta(days=10), 4),  # short chain via B
        C: node(C, D0 + dt.timedelta(days=10), 14),  # long chain via C
        D: node(D, D0 + dt.timedelta(days=30), 4),
    }
    adjacency = {A: [(B, 0), (C, 0)], B: [(D, 0)], C: [(D, 0)]}

    new_a_end = nodes[A].end_date + dt.timedelta(days=10)
    changes = compute_propagation(nodes, adjacency, A, nodes[A].start_date, new_a_end)

    expected_b_end = new_a_end + (nodes[B].end_date - nodes[B].start_date)
    expected_c_end = new_a_end + (nodes[C].end_date - nodes[C].start_date)
    assert changes[B][1] == expected_b_end
    assert changes[C][1] == expected_c_end

    expected_d_start = max(expected_b_end, expected_c_end)
    assert changes[D][0] == expected_d_start


def test_milestone_as_successor_moves_as_a_zero_duration_node():
    activity_start = D0
    nodes = {
        A: node(A, activity_start, 9),
        M: ScheduleNode(M, D0 + dt.timedelta(days=9), D0 + dt.timedelta(days=9)),
    }
    adjacency = {A: [(M, 3)]}

    new_end = nodes[A].end_date + dt.timedelta(days=5)
    changes = compute_propagation(nodes, adjacency, A, activity_start, new_end)

    assert changes[M][0] == changes[M][1] == new_end + dt.timedelta(days=3)


def test_milestone_as_predecessor_pushes_its_successor():
    milestone_date = D0
    nodes = {
        M: ScheduleNode(M, milestone_date, milestone_date),
        A: node(A, milestone_date + dt.timedelta(days=1), 5),
    }
    adjacency = {M: [(A, 0)]}

    new_date = milestone_date + dt.timedelta(days=7)
    changes = compute_propagation(nodes, adjacency, M, new_date, new_date)

    assert changes[A][0] == new_date
    a_duration = nodes[A].end_date - nodes[A].start_date
    assert changes[A][1] == new_date + a_duration


def test_no_dependents_means_only_the_changed_node_is_reported():
    nodes = {A: node(A, D0, 9)}
    adjacency: dict = {}

    new_end = nodes[A].end_date + dt.timedelta(days=2)
    changes = compute_propagation(nodes, adjacency, A, nodes[A].start_date, new_end)

    assert list(changes.keys()) == [A]
