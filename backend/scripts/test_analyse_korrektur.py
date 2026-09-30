import math

from analyse_korrektur import correction_factor


def test_correction_factor():
    # half the error removed -> twice as strong
    assert math.isclose(correction_factor(1.0, 0.5)[0], 2.0)
    # 75 % removed -> 1/0.75 (old formula ctrl/corr gave 4.0)
    assert math.isclose(correction_factor(1.0, 0.25)[0], 1 / 0.75)
    # overshoot (sign flip) -> < 1, not 0
    f, note = correction_factor(1.0, -0.5)
    assert math.isclose(f, 1 / 1.5) and 'Überkompensation' in note
    # pushed the wrong way -> negative
    assert correction_factor(1.0, 1.5)[0] < 0
    # no effect -> undefined
    assert math.isnan(correction_factor(1.0, 1.0)[0])
    # real numbers from corr-paper-full z (ctrl +0.074, corr +0.021): ~1.40, old output 3.53
    assert math.isclose(correction_factor(0.074, 0.021)[0], 0.074 / 0.053)


if __name__ == '__main__':
    test_correction_factor()
    print('ok')
