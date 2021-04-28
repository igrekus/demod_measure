import random

from math import log10, cos, radians
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

        self.data1 = []
        self.data2 = []
        self.data3 = []
        self.data4 = []

    def __bool__(self):
        return self.ready

    def _process(self):
        self.ready = True

    def _process_point(self, data):
        f_lo = data['f_lo'] / GHz
        ui = data['ch1_amp']
        uq = data['ch2_amp']
        p_rf = data['p_rf']
        p_loss = data['loss']
        phase = data['phase']

        p_pch = 30 + 10 * log10(((ui/2) ** 2) / 100)
        kp_loss = p_pch - p_rf + p_loss
        a_err_times = uq / ui
        a_err_db = 20 * (log10(uq) - log10(ui))
        ph_err = phase + 90
        a_zk = 10 * log10((1 + a_err_times ** 2 - 2 * a_err_times * cos(radians(ph_err))) /
                          (1 + a_err_times ** 2 + 2 * a_err_times * cos(radians(ph_err))))
        self._report = {
            'p_lo': data['p_lo'],
            'f_lo': f_lo,
            'p_rf': p_rf,
            'f_rf': data['f_rf'] / GHz,
            'u_src': round(data['u_src'], 1),
            'i_src': round(data['i_src'] * mA, 2),
            'ui': round(data['ch1_amp'] * mV, 1),
            'uq': round(data['ch2_amp'] * mV, 1),
            'phase': phase,
            'freq': round(data['ch1_freq'] / GHz, 3),
            'f_tune': (data['f_rf'] - data['f_lo']) / MHz,
            'a_err': round((data['ch1_amp'] - data['ch2_amp']) * mV, 1),
            'p_pch': round(p_pch, 1),
            'kp_loss': round(kp_loss, 2),
            'a_err_times': round(a_err_times, 2),
            'a_err_db': abs(round(a_err_db, 2)),
            'ph_err': round(ph_err, 2),
            'a_zk': round(a_zk, 2),
        }

        self.data1.append([f_lo, kp_loss])
        self.data2.append([f_lo, a_err_db])
        self.data3.append([f_lo, ph_err])
        self.data4.append([f_lo, a_zk])

    def clear(self):
        self._secondaryParams.clear()
        self.headers.clear()
        self._raw.clear()
        self._report.clear()

        self.data1.clear()
        self.data2.clear()
        self.data3.clear()
        self.data4.clear()

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
        αош, мВ={a_err}   Δφ, º={phase}
        
        Расчётные параметры:
        Pпч, дБм={p_pch}   Кп, дБм={kp_loss}
        αош, раз={a_err_times}   αош, дБ={a_err_db}
        φош, º={ph_err}   αзк, дБ={a_zk}
        """.format(**self._report))
