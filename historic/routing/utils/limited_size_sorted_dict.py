from sortedcontainers import SortedDict

class LimitedSizeSortedDict(SortedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        SortedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        SortedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(self.size_limit)


if __name__ == "__main__":
    sd = LimitedSizeSortedDict(size_limit=10)
    for i in range(100,1,-1):
        sd[i] = i
    print(sd)
