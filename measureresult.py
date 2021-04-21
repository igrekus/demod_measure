import random


class MeasureResult:
    def __init__(self):
        self._secondaryParams = None
        self.ready = False
        self.headers = list()
        self._raw = list()

        self.data1 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]
        self.data2 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]
        self.data3 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]
        self.data4 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]

        self._process()

    def __bool__(self):
        return self.ready

    def _init(self):
        self._secondaryParams.clear()

    def _process(self):
        self.ready = True

    def set_secondary_params(self, params):
        self._secondaryParams = dict(**params)

    def add_point(self, data):
        self._raw.append(data)

    @property
    def last_point(self):
        return self._raw[-1]
