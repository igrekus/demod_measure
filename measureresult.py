import random


class MeasureResult:
    def __init__(self, raw, secondaryParams):
        self.headers = list()
        self._secondaryParams = secondaryParams
        self.ready = False

        self.raw = raw

        self.data1 = [[random.randint(0, 50) for _ in range(10)]]
        self.data2 = [[random.randint(0, 50) for _ in range(10)]]
        self.data3 = [[random.randint(0, 50) for _ in range(10)]]
        self.data4 = [[random.randint(0, 50) for _ in range(10)]]

        self._process()

    def __bool__(self):
        return self.ready

    def _init(self):
        self._secondaryParams.clear()

    def _process(self):
        self.ready = True
