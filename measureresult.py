import random
from textwrap import dedent


class MeasureResult:
    def __init__(self):
        self._secondaryParams = None
        self.headers = list()
        self._raw = list()
        self._report = dict()
        self.ready = False

        self.data1 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]
        self.data2 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]
        self.data3 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]
        self.data4 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [random.randint(0, 50) for _ in range(10)]]

    def __bool__(self):
        return self.ready

    def _process(self):
        self.ready = True

    def _process_point(self, data):
        self._report = {
            'p_lo': data['p_lo'],
            'f_lo': data['f_lo'],
            'p_rf': data['p_rf'],
            'f_rf': data['f_rf'],
            'u_src': data['u_src'],
            'i_src': data['i_src'],
            'ui': data['ch1_amp'],
            'uq': data['ch2_amp'],
            'phase': data['phase'],
            'freq': data['ch1_freq'],
            'f_tune': data['f_rf'] - data['f_lo'],
            'aerr': data['ch1_amp'] - data['ch2_amp'],
        }

    def clear(self):
        self._secondaryParams.clear()
        self.headers.clear()
        self._raw.clear()
        self._report.clear()
        self.ready = False

    def set_secondary_params(self, params):
        self._secondaryParams = dict(**params)

    def add_point(self, data):
        self._raw.append(data)
        self._process_point(data)

    @property
    def report(self):
        return dedent("""        Генераторы:
        Pгет={p_lo}дБм   Fгет={f_lo}ГГц
        Pвх={p_rf}дБм   Fвх={f_rf}ГГц
        Fпч={f_tune}МГц
        
        Источник питания:
        U={u_src}В   I={i_src}мА

        Осциллограф:
        F={freq}ГГц
        UI={ui}мВ   UQ={uq}мВ
        αош={aerr}мВ   Δφ={phase}º
        
        Расчётные параметры:
                   
        """.format(**self._report))
