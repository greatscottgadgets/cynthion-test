class Range:
    def __init__(self, lo, hi):
        assert hi >= lo
        self.lo = lo
        self.hi = hi

    def __add__(self, other):
        if isinstance(other, Range):
            return Range(self.lo + other.lo, self.hi + other.hi)
        else:
            return Range(self.lo + other, self.hi + other)

    def __radd__(self, other):
        return Range(other + self.lo, other + self.hi)

    def __mul__(self, other):
        if isinstance(other, Range):
            return Range(self.lo * other.lo, self.hi * other.hi)
        else:
            return Range(self.lo * other, self.hi * other)

    def __rmul__(self, other):
        return Range(self.lo * other, self.hi * other)

    def __neg__(self):
        return Range(-self.hi, -self.lo)

    def __sub__(self, other):
        return Range(self.lo - other.hi, self.hi - other.lo)

    def __rsub__(self, other):
        return Range(other - self.hi, other - self.lo)

    def __truediv__(self, other):
        return Range(self.lo / other.hi, self.hi / other.lo)

    def __rtruediv__(self, other):
        return Range(other / self.hi, other / self.lo)
