import random

from textwrap import dedent

KHz = 1_000
MHz = 1_000_000
GHz = 1_000_000_000
mA = 1_000
mV = 1_000


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
            'f_lo': data['f_lo'] / GHz,
            'p_rf': data['p_rf'],
            'f_rf': data['f_rf'] / GHz,
            'u_src': round(data['u_src'], 1),
            'i_src': round(data['i_src'] * mA, 2),
            'ui': round(data['ch1_amp'] * mV, 1),
            'uq': round(data['ch2_amp'] * mV, 1),
            'phase': data['phase'],
            'freq': round(data['ch1_freq'] / GHz, 3),
            'f_tune': (data['f_rf'] - data['f_lo']) / MHz,
            'aerr': round((data['ch1_amp'] - data['ch2_amp']) * mV, 1),
        }

        ln = len(self._report)
        self.data1 = [range(ln), [random.randint(0, 50) for _ in range(ln)]]
        self.data2 = [range(ln), [random.randint(0, 50) for _ in range(ln)]]
        self.data3 = [range(ln), [random.randint(0, 50) for _ in range(ln)]]
        self.data4 = [range(ln), [random.randint(0, 50) for _ in range(ln)]]

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
        Pгет, дБм={p_lo}   Fгет, ГГц={f_lo:0.2f}
        Pвх, дБм={p_rf}   Fвх, ГГц={f_rf:0.2f}
        Fпч, МГц={f_tune:0.2f}
        
        Источник питания:
        U, В={u_src}   I, мА={i_src}

        Осциллограф:
        F, ГГц={freq:0.3f}
        UI, мВ={ui}   UQ, мВ={uq}
        αош, мВ={aerr}   Δφ, º={phase}
        
        Расчётные параметры:
                   
        """.format(**self._report))
