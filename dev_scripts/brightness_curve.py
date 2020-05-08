import math


B = 0.023


def f(x):
    b = B
    a = 1024 / (math.exp(b * 100) - 1)
    return a * (math.exp(b * x) - 1)


def main():
    print('b =', B)
    for x in range(0, 101, 10):
        print(x, f(x))


if __name__ == "__main__":
    main()
