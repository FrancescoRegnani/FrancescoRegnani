from app.core import normalized_probs

def test_normalized_probabilities():
    p=normalized_probs({'A':2.70,'B':1.49})
    assert abs(sum(p.values())-1)<1e-10
    assert 0.35<p['A']<0.36

def test_movement():
    a=normalized_probs({'A':2.70,'B':1.49})['A']
    b=normalized_probs({'A':2.27,'B':1.66})['A']
    assert 6<(b-a)*100<8
