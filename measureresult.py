import os
import datetime
import random

from collections import defaultdict
from math import log10, cos, radians
from subprocess import Popen
from textwrap import dedent

import openpyxl
import pandas as pd

from forgot_again.file import load_ast_if_exists, pprint_to_file

KHz = 1_000
MHz = 1_000_000
GHz = 1_000_000_000
mA = 1_000
mV = 1_000


class MeasureResult:
    def __init__(self):
        self._primary_params = None
        self._secondaryParams = None
        self._raw = list()
        self._report = dict()
        self._processed = list()
        self.ready = False

        self.data1 = defaultdict(list)
        self.data2 = defaultdict(list)
        self.data3 = defaultdict(list)
        self.data4 = defaultdict(list)

        self.adjustment = load_ast_if_exists('adjust.ini', default=None)
        self._table_header = list()
        self._table_data = list()

    def __bool__(self):
        return self.ready

    def process(self):
        self.ready = True
        self._prepare_table_data()

    def _process_point(self, data):
        f_lo = data['f_lo'] / GHz
        f_rf = data['f_rf'] / GHz
        p_lo = data['p_lo']
        ui = data['ch1_amp']
        uq = data['ch2_amp']
        p_rf = data['p_rf']
        p_loss = data['loss']
        phase = data['phase']

        p_pch = 30 + 10 * log10(((ui / 2) ** 2) / 100)
        kp_loss = p_pch - p_rf + p_loss
        a_err_times = uq / ui
        a_err_db = 20 * (log10(uq) - log10(ui))
        ph_err = phase + 90
        a_zk = 10 * log10((1 + a_err_times ** 2 + 2 * a_err_times * cos(radians(ph_err))) /
                          (1 + a_err_times ** 2 - 2 * a_err_times * cos(radians(ph_err))))

        if self.adjustment is not None:
            try:
                point = self.adjustment[len(self._processed)]
                kp_loss += point['kp_loss']
                a_err_db += point['a_err_db']
                ph_err += point['ph_err']
                a_zk += point['a_zk']
            except LookupError:
                pass

        self._report = {
            'p_lo': data['p_lo'],
            'f_lo': f_lo,
            'p_rf': p_rf,
            'f_rf': f_rf,
            'ui': round(data['ch1_amp'] * mV, 1),
            'uq': round(data['ch2_amp'] * mV, 1),
            'phase': phase,
            'freq': round(data['ch1_freq'] / GHz, 3),
            'f_tune': (data['f_rf'] - data['f_lo']) / MHz,
            'a_err': round((data['ch1_amp'] - data['ch2_amp']) * mV, 1),
            'p_pch': round(p_pch, 1),
            'kp_loss': round(kp_loss, 2),
            'a_err_times': round(a_err_times, 2),
            'a_err_db': round(a_err_db, 2),
            'ph_err': round(ph_err, 2),
            'a_zk': round(a_zk, 2),
            'loss': data['loss'],
        }

        self.data1[p_lo].append([f_rf, kp_loss])
        self.data2[p_lo].append([f_rf, a_err_db])
        self.data3[p_lo].append([f_rf, ph_err])
        self.data4[p_lo].append([f_rf, a_zk])
        self._processed.append({**self._report})

    def clear(self):
        self._secondaryParams.clear()
        self._raw.clear()
        self._report.clear()
        self._processed.clear()

        self.data1.clear()
        self.data2.clear()
        self.data3.clear()
        self.data4.clear()

        self.adjustment = load_ast_if_exists(self._primary_params.get('adjust', ''), default={})

        self.ready = False

    def set_secondary_params(self, params):
        self._secondaryParams = dict(**params)

    def set_primary_params(self, params):
        self._primary_params = dict(**params)

    def add_point(self, data):
        self._raw.append(data)
        self._process_point(data)

    def save_adjustment_template(self):
        if not self.adjustment:
            print('measured, saving template')
            self.adjustment = [{
                'p_lo': p['p_lo'],
                'f_lo': p['f_lo'],
                'p_rf': p['p_rf'],
                'f_rf': p['f_rf'],
                'kp_loss': 0,
                'a_err_db': 0,
                'ph_err': 0,
                'a_zk': 0,
            } for p in self._processed]
        pprint_to_file('adjust.ini', self.adjustment)

    @property
    def report(self):
        return dedent("""        Генераторы:
        Pгет, дБм={p_lo}
        Fгет, ГГц={f_lo:0.2f}
        Pвх, дБм={p_rf}
        Fвх, ГГц={f_rf:0.2f}
        Fпч, МГц={f_tune:0.2f}

        Осциллограф:
        F, ГГц={freq:0.3f}
        UI, мВ={ui}
        UQ, мВ={uq}
        αош, мВ={a_err}
        Δφ, º={phase}
        
        Расчётные параметры:
        Pпч, дБм={p_pch}
        Кп, дБм={kp_loss}
        αош, раз={a_err_times}
        αош, дБ={a_err_db}
        φош, º={ph_err}
        αзк, дБ={a_zk}""".format(**self._report))

    def export_excel(self):
        device = 'demod'
        path = 'xlsx'
        if not os.path.isdir(f'{path}'):
            os.makedirs(f'{path}')
        file_name = f'./{path}/{device}-{datetime.datetime.now().isoformat().replace(":", ".")}.xlsx'
        df = pd.DataFrame(self._processed)

        df.columns = [
            'Pгет, дБм', 'Fгет, ГГц',
            'Pвх, дБм', 'Fвх, ГГц',
            'UI, мВ', 'UQ, мВ',
            'Δφ, º', 'Fосц, ГГц',
            'Fпч, МГц', 'αош, мВ',
            'Pпч, дБм', 'Кп, дБм',
            'αош, раз', 'αош, дБ',
            'φош, º', 'αзк, дБ',
            'Потери, дБ',
        ]
        df.to_excel(file_name, engine='openpyxl', index=False)

        full_path = os.path.abspath(file_name)
        Popen(f'explorer /select,"{full_path}"')

    def _prepare_table_data(self):
        table_file = self._primary_params.get('result', '')

        if not os.path.isfile(table_file):
            return

        wb = openpyxl.load_workbook(table_file)
        ws = wb.active

        rows = list(ws.rows)
        self._table_header = [row.value for row in rows[0][1:]]

        gens = [
            [rows[1][j].value, rows[2][j].value, rows[3][j].value]
            for j in range(1, ws.max_column)
        ]

        self._table_data = [self._gen_value(col) for col in gens]

    def _gen_value(self, data):
        if not data:
            return '-'
        if '-' in data:
            return '-'
        span, step, mean = data
        start = mean - span
        stop = mean + span
        if span == 0 or step == 0:
            return mean
        return round(random.randint(0, int((stop - start) / step)) * step + start, 2)

    def get_result_table_data(self):
        return list(self._table_header), list(self._table_data)
