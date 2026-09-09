from tikuos_iu.contract import UtilityHint, score, deadline_eligible, select, DEADLINE_FLAG

def test_score_matches_integer_spec():
    h=UtilityHint(12345,cost_cycles=37)
    assert score(h)==(12345<<16)//37

def test_deadline_wraparound():
    h=UtilityHint(1,deadline_tick=5,cost_cycles=1,flags=DEADLINE_FLAG)
    assert deadline_eligible(h,0)
    assert deadline_eligible(h,5)
    assert not deadline_eligible(h,6)
    # 32-bit wrap: deadline 5 is seven ticks after 0xfffffffe.
    assert deadline_eligible(h,0xfffffffe)

def test_dynamic_selection():
    hs=[UtilityHint(100,cost_cycles=100),UtilityHint(1000,cost_cycles=100)]
    assert select(hs,0,0)==1
    hs[0]=UtilityHint(2000,cost_cycles=10)
    assert select(hs,1,0)==0

def test_expired_deadline_excluded():
    hs=[UtilityHint(65535,deadline_tick=10,cost_cycles=1,flags=DEADLINE_FLAG),
        UtilityHint(1,cost_cycles=1)]
    assert select(hs,0,11)==1

def test_deadline_exact_now_is_eligible():
    h=UtilityHint(100,deadline_tick=10,cost_cycles=1,flags=DEADLINE_FLAG)
    assert deadline_eligible(h,10)

def test_deadline_more_than_half_range_is_ambiguous():
    h=UtilityHint(100,deadline_tick=0x80000000,cost_cycles=1,flags=DEADLINE_FLAG)
    assert not deadline_eligible(h,0)

def test_tie_break_is_cursor_order():
    hs=[UtilityHint(100,cost_cycles=10),UtilityHint(100,cost_cycles=10)]
    assert select(hs,1,0)==1
    assert select(hs,0,0)==0
