from src.emptymiles_testbed.geometry import distance, route_length, sequence_detour
from src.emptymiles_testbed.models import Order


def _order(oid, origin, dest, ready=0.0):
    return Order(id=oid, origin=origin, dest=dest, weight_kg=10.0, ready_time=ready, due_time=ready + 100)


def test_route_length_sums_segments():
    assert route_length([(0, 0), (3, 0), (3, 4)]) == 7.0


def test_sequence_detour_zero_for_no_orders():
    assert sequence_detour((0, 0), (10, 0), []) == 0.0


def test_sequence_detour_is_nonnegative_and_compounds():
    o1 = _order(0, (0, 5), (10, 5), ready=0)
    o2 = _order(1, (5, 8), (6, 8), ready=1)
    one = sequence_detour((0, 0), (10, 0), [o1])
    two = sequence_detour((0, 0), (10, 0), [o1, o2])
    assert one >= 0
    assert two >= one  # adding an order never reduces the detour


def test_detour_free_when_order_lies_on_the_line():
    # pickup/dropoff exactly on the straight route ⇒ ~no detour
    o = _order(0, (3, 0), (7, 0))
    assert sequence_detour((0, 0), (10, 0), [o]) < 1e-9
