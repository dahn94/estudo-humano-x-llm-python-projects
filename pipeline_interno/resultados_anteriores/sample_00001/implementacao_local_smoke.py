def bisection(function, a, b):
    """Encontra uma raiz em [a, b] pelo método da bisseção."""
    fa = function(a)
    fb = function(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise ValueError("could not find root in given interval.")

    tolerance = 1e-7
    while b - a > tolerance:
        midpoint = (a + b) / 2
        fm = function(midpoint)
        if fm == 0:
            return midpoint
        if fa * fm < 0:
            b = midpoint
        else:
            a = midpoint
            fa = fm
    return (a + b) / 2

