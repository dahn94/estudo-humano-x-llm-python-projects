from implementacao_local_smoke import bisection


def assert_close(actual, expected, tolerance=1e-6):
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"esperado {expected}, obtido {actual}")


def main():
    assert_close(bisection(lambda x: x**3 - 1, -5, 5), 1.0)
    assert_close(bisection(lambda x: x**2 - 4 * x + 3, 0, 2), 1.0)
    assert_close(bisection(lambda x: x**2 - 4 * x + 3, 2, 4), 3.0)

    for function, a, b in (
        (lambda x: x**3 - 1, 2, 1000),
        (lambda x: x**2 - 4 * x + 3, 4, 1000),
    ):
        try:
            bisection(function, a, b)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError esperado para intervalo sem raiz")

    print("5/5 testes passaram")


if __name__ == "__main__":
    main()

