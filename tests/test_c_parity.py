from tikuos_iu.contract import UtilityHint, score
from tikuos_iu.cabi import score_exact

def test_python_c_score_parity():
    cases=[(0,1),(1,1),(65535,1),(12345,37),(65535,1000000)]
    for u,c in cases:
        h=UtilityHint(u,cost_cycles=c)
        assert score(h)==score_exact(h)
