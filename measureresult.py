import random


class MeasureResult:
    adjust_dirs = {
        1: 'data/+25',
        2: 'data/+85',
        3: 'data/-60',
    }

    def __init__(self, ):

        self.headers = list()
        self._secondaryParams = dict()
        self.ready = False

    def __bool__(self):
        return self.ready

    def _init(self):
        self._secondaryParams.clear()

    def _process(self):
        self.ready = True

    @property
    def raw_data(self):
        return True

    @raw_data.setter
    def raw_data(self, args):
        print('process result')
        self._init()

        print(args)
        self._process()

    @property
    def stats(self):
        return f'stats'
