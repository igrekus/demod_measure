import ast
import time

import numpy as np

from pprint import pprint
from os.path import isfile
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

from instr.instrumentfactory import mock_enabled, OscilloscopeFactory, GeneratorFactory, SourceFactory, \
    MultimeterFactory, AnalyzerFactory
from measureresult import MeasureResult


# TODO add attenuation field -- calculate each pow point + att power

class InstrumentController(QObject):
    pointReady = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.requiredInstruments = {
            'Осциллограф': OscilloscopeFactory('GPIB1::7::INSTR'),
            'Анализатор': OscilloscopeFactory('GPIB1::18::INSTR'),
            'P LO': GeneratorFactory('GPIB1::6::INSTR'),
            'P RF': GeneratorFactory('GPIB1::20::INSTR'),
            'Источник': SourceFactory('GPIB1::3::INSTR'),
            'Мультиметр': MultimeterFactory('GPIB1::22::INSTR'),
        }

        if isfile('./instr.ini'):
            with open('./instr.ini', mode='rt', encoding='utf-8') as f:
                addrs = ast.literal_eval(''.join(f.readlines()))
                self.requiredInstruments = {
                    'Осциллограф': OscilloscopeFactory(addrs['Осциллограф']),
                    'Анализатор': AnalyzerFactory(addrs['Анализатор']),
                    'P LO': GeneratorFactory(addrs['P LO']),
                    'P RF': GeneratorFactory(addrs['P RF']),
                    'Источник': SourceFactory(addrs['Источник']),
                    'Мультиметр': MultimeterFactory(addrs['Мультиметр']),
                }

        self.deviceParams = {
            'Демодулятор': {
                'F': 1,
            },
        }

        self.secondaryParams = {
            'Plo_min': -10.0,
            'Plo_max': -10.0,
            'Plo_delta': 1.0,
            'Flo_min': 0.1,
            'Flo_max': 3.0,
            'Flo_delta': 0.1,
            'half_f_lo': False,
            'Prf': -10.0,
            'Frf_min': 0.11,
            'Frf_max': 3.1,
            'Frf_delta': 0.1,
            'Usrc': 5.0,
            'OscAvg': True,
            'loss': 0.82,
            'scale_y': 0.7,
        }

        if isfile('./params.ini'):
            with open('./params.ini', 'rt', encoding='utf-8') as f:
                self.secondaryParams = ast.literal_eval(''.join(f.readlines()))

        self._calibrated_pows_lo = dict()
        if isfile('./cal_lo.ini'):
            with open('./cal_lo.ini', mode='rt', encoding='utf-8') as f:
                self._calibrated_pows_lo = ast.literal_eval(''.join(f.readlines()))

        self._calibrated_pows_rf = dict()
        if isfile('./cal_rf.ini'):
            with open('./cal_rf.ini', mode='rt', encoding='utf-8') as f:
                self._calibrated_pows_rf = ast.literal_eval(''.join(f.readlines()))

        self._instruments = dict()
        self.found = False
        self.present = False
        self.hasResult = False
        self.only_main_states = False

        self.result = MeasureResult()

    def __str__(self):
        return f'{self._instruments}'

    def connect(self, addrs):
        print(f'searching for {addrs}')
        for k, v in addrs.items():
            self.requiredInstruments[k].addr = v
        self.found = self._find()

    def _find(self):
        self._instruments = {
            k: v.find() for k, v in self.requiredInstruments.items()
        }
        return all(self._instruments.values())

    def check(self, token, params):
        print(f'call check with {token} {params}')
        device, secondary = params
        self.present = self._check(token, device, secondary)
        print('sample pass')

    def _check(self, token, device, secondary):
        print(f'launch check with {self.deviceParams[device]} {self.secondaryParams}')
        self._init()
        return True

    def calibrate(self, token, params):
        print(f'call calibrate with {token} {params}')
        return self._calibrate(token, self.secondaryParams)

    def _calibrateLO(self, token, secondary):
        print('run calibrate LO with', secondary)

        gen_lo = self._instruments['P LO']
        sa = self._instruments['Анализатор']

        secondary = self.secondaryParams

        # TODO:
        """
        - измерительное оборудование: генератор гетеродина, генератор РЧ и анализатор спектра
        - панель оператора: 
            поле для ввода значения мощности обоих генераторов
            поле начальной, конечной частоты и шага для генератора гетеродина
            поле начальной, конечной частоты и шага для генератора РЧ

        - алгоритм: 
            оператор подключает кабель между генератором гетеродина и АС, задает значения полей;
            нажимает кнопку "Кабель Гет. калиб."; 
            провести измерение мощности по заданному циклу, рассчитать значение потерь в кабеле: Потери = Рвх - Рвых; 
            создать файл-массив "Частота - Потери"; 
            по завершении цикла оператор подключает кабель между генератором РЧ и АС; 
            повторить цикл измерения потерь в кабеле по аналогии с гетеродином; сохранить в файл.

        - в программе измерения параметров демодулятора учесть потери в кабелях при выдаче мощности Гет и РЧ.

        Установка линии ТЗ в измерительные графики:
        - панель оператора:
        поле ввода значения Кпр согласно ТЗ - на графике Кпр(fгет) отображается горизонтальная прямая линия в соответствии с данным значением;
        поле ввода значения αош согласно ТЗ - на графике αош(fгет) отображается горизонтальная прямая линия в соответствии с данным значением;
        поле ввода значения φош согласно ТЗ - на графике φош(fгет) отображается горизонтальная прямая линия в соответствии с данным значением;
        поле ввода значения αзк согласно ТЗ - на графике αзк(fгет) отображается горизонтальная прямая линия в соответствии с данным значением;
        поле ввода значения Р1дБ.вх согласно ТЗ - на графике Рвых(Рвх) отображается вертикальная прямая линия в соответствии с данным значением;
        поле ввода значения Iпот согласно ТЗ - на графике Iпот(Uпит) отображается горизонтальная прямая линия в соответствии с данным значением.

        """

        pow_lo = secondary['Plo_min']

        freq_lo_start = secondary['Flo_min']
        freq_lo_end = secondary['Flo_max']
        freq_lo_step = secondary['Flo_delta']

        freq_lo_values = [round(x, 3) for x in
                          np.arange(start=freq_lo_start, stop=freq_lo_end + 0.0001, step=freq_lo_step)]

        sa.send(':CAL:AUTO OFF')
        sa.send(':SENS:FREQ:SPAN 1MHz')
        sa.send(f'DISP:WIND:TRAC:Y:RLEV 10')
        sa.send(f'DISP:WIND:TRAC:Y:PDIV 5')

        gen_lo.send(f':OUTP:MOD:STAT OFF')
        gen_lo.send(f'SOUR:POW {pow_lo}dbm')

        sa.send(':CALC:MARK1:MODE POS')

        result = {}
        for freq in freq_lo_values:

            if token.cancelled:
                gen_lo.send(f'OUTP:STAT OFF')
                time.sleep(0.5)

                gen_lo.send(f'SOUR:POW {pow_lo}dbm')

                gen_lo.send(f'SOUR:FREQ {freq_lo_start}GHz')
                raise RuntimeError('calibration cancelled')

            gen_lo.send(f'SOUR:FREQ {freq}GHz')
            gen_lo.send(f'OUTP:STAT ON')

            if not mock_enabled:
                time.sleep(0.25)

            sa.send(f':SENSe:FREQuency:CENTer {freq}GHz')
            sa.send(f':CALCulate:MARKer1:X:CENTer {freq}GHz')

            if not mock_enabled:
                time.sleep(0.25)

            pow_read = float(sa.query(':CALCulate:MARKer:Y?'))

            if mock_enabled:
                pow_read = 10

            result[freq] = pow_read

        with open('cal_lo.ini', mode='wt', encoding='utf-8') as f:
            pprint(result, stream=f)

        return True

    def _calibrateRF(self, token, secondary):
        print('run calibrate RF with', secondary)

        gen_rf = self._instruments['P RF']
        sa = self._instruments['Анализатор']

        secondary = self.secondaryParams

        pow_rf = secondary['Prf']

        freq_rf_start = secondary['Frf_min']
        freq_rf_end = secondary['Frf_max']
        freq_rf_step = secondary['Frf_delta']

        freq_rf_values = [round(x, 3) for x in
                          np.arange(start=freq_rf_start, stop=freq_rf_end + 0.0001, step=freq_rf_step)]

        sa.send(':CAL:AUTO OFF')
        sa.send(':SENS:FREQ:SPAN 1MHz')
        sa.send(f'DISP:WIND:TRAC:Y:RLEV 10')
        sa.send(f'DISP:WIND:TRAC:Y:PDIV 5')

        # gen_rf.send(f':OUTP:MOD:STAT OFF')
        gen_rf.send(f'SOUR:POW {pow_rf}dbm')

        sa.send(':CALC:MARK1:MODE POS')

        result = {}
        for freq in freq_rf_values:

            if token.cancelled:
                gen_rf.send(f'OUTP:STAT OFF')
                time.sleep(0.5)

                gen_rf.send(f'SOUR:POW {pow_rf}dbm')

                gen_rf.send(f'SOUR:FREQ {freq_rf_start}GHz')
                raise RuntimeError('calibration cancelled')

            gen_rf.send(f'SOUR:FREQ {freq}GHz')
            gen_rf.send(f'OUTP:STAT ON')

            if not mock_enabled:
                time.sleep(0.25)

            sa.send(f':SENSe:FREQuency:CENTer {freq}GHz')
            sa.send(f':CALCulate:MARKer1:X:CENTer {freq}GHz')

            if not mock_enabled:
                time.sleep(0.25)

            pow_read = float(sa.query(':CALCulate:MARKer:Y?'))

            if mock_enabled:
                pow_read = 10

            result[freq] = pow_read

        with open('cal_rf.ini', mode='wt', encoding='utf-8') as f:
            pprint(result, stream=f)

        return True

    def measure(self, token, params):
        print(f'call measure with {token} {params}')
        device, _ = params
        try:
            self.result.set_secondary_params(self.secondaryParams)
            self._measure(token, device)
            # self.hasResult = bool(self.result)
            self.hasResult = True  # HACK
        except RuntimeError as ex:
            print('runtime error:', ex)

    def _measure(self, token, device):
        param = self.deviceParams[device]
        secondary = self.secondaryParams
        print(f'launch measure with {token} {param} {secondary}')

        self._clear()
        self._measure_s_params(token, param, secondary)
        return True

    def _clear(self):
        self.result.clear()

    def _init(self):
        self._instruments['P LO'].send('*RST')
        self._instruments['P RF'].send('*RST')
        self._instruments['Осциллограф'].send('*RST')
        self._instruments['Источник'].send('*RST')
        self._instruments['Мультиметр'].send('*RST')
        # self._instruments['Анализатор'].send('*RST')

    def _measure_s_params(self, token, param, secondary):
        gen_lo = self._instruments['P LO']
        gen_rf = self._instruments['P RF']
        osc = self._instruments['Осциллограф']
        src = self._instruments['Источник']
        mult = self._instruments['Мультиметр']
        # sa = self._instruments['Анализатор']

        src_u = secondary['Usrc']
        src_i = 200  # mA
        pow_lo_start = secondary['Plo_min']
        pow_lo_end = secondary['Plo_max']
        pow_lo_step = secondary['Plo_delta']
        freq_lo_start = secondary['Flo_min']
        freq_lo_end = secondary['Flo_max']
        freq_lo_step = secondary['Flo_delta']
        freq_lo_half = secondary['half_f_lo']

        pow_rf = secondary['Prf']
        freq_rf_start = secondary['Frf_min']
        freq_rf_end = secondary['Frf_max']
        freq_rf_step = secondary['Frf_delta']

        loss = secondary['loss']

        osc_avg = 'ON' if secondary['OscAvg'] else 'OFF'

        osc_scale = secondary['scale_y']

        src.send(f'APPLY p6v,{src_u}V,{src_i}mA')

        osc.send(f':ACQ:AVERage {osc_avg}')

        osc.send(f':CHANnel1:DISPlay ON')
        osc.send(f':CHANnel2:DISPlay ON')

        osc.send(':CHAN1:SCALE 0.05')  # V
        osc.send(':CHAN2:SCALE 0.05')
        osc.send(':TIMEBASE:SCALE 10E-8')  # ms / div

        osc.send(':TRIGger:MODE EDGE')
        osc.send(':TRIGger:EDGE:SOURCe CHANnel1')
        osc.send(':TRIGger:LEVel CHANnel1,0')
        osc.send(':TRIGger:EDGE:SLOPe POSitive')

        osc.send(':MEASure:VAMPlitude channel1')
        osc.send(':MEASure:VAMPlitude channel2')
        osc.send(':MEASure:PHASe CHANnel1,CHANnel2')
        osc.send(':MEASure:FREQuency CHANnel1')

        # pow_lo_end = -5.0
        # pow_lo_step = 5

        pow_lo_values = [round(x, 3) for x in np.arange(start=pow_lo_start, stop=pow_lo_end + 0.002, step=pow_lo_step)] \
            if pow_lo_start != pow_lo_end else [pow_lo_start]
        freq_lo_values = [round(x, 3) for x in
                          np.arange(start=freq_lo_start, stop=freq_lo_end + 0.0001, step=freq_lo_step)]
        freq_rf_values = [round(x, 3) for x in
                          np.arange(start=freq_rf_start, stop=freq_rf_end + 0.0001, step=freq_rf_step)]

        gen_lo.send(f':OUTP:MOD:STAT OFF')
        # gen_rf.send(f':OUTP:MOD:STAT OFF')

        if mock_enabled:
            # with open('./mock_data/meas_1_-10-5db.txt', mode='rt', encoding='utf-8') as f:
            with open('./mock_data/meas_1_-10db.txt', mode='rt', encoding='utf-8') as f:
                index = 0
                mocked_raw_data = ast.literal_eval(''.join(f.readlines()))

        res = []
        for pow_lo in pow_lo_values:

            for freq_lo, freq_rf in zip(freq_lo_values, freq_rf_values):

                if freq_lo_half:
                    freq_lo /= 2

                if token.cancelled:
                    gen_lo.send(f'OUTP:STAT OFF')
                    gen_rf.send(f'OUTP:STAT OFF')
                    time.sleep(0.5)
                    src.send('OUTPut OFF')

                    gen_rf.send(f'SOUR:POW {pow_rf}dbm')
                    gen_lo.send(f'SOUR:POW {pow_lo_start}dbm')

                    gen_rf.send(f'SOUR:FREQ {freq_rf_start}GHz')
                    gen_lo.send(f'SOUR:FREQ {freq_rf_start}GHz')
                    raise RuntimeError('measurement cancelled')

                gen_lo.send(f'SOUR:POW {pow_lo + self._calibrated_pows_lo.get(freq_lo, 0)}dbm')
                gen_rf.send(f'SOUR:POW {pow_rf + self._calibrated_pows_rf.get(freq_rf, 0)}dbm')

                gen_lo.send(f'SOUR:FREQ {freq_lo}GHz')
                gen_rf.send(f'SOUR:FREQ {freq_rf}GHz')

                # TODO hoist out of the loops
                src.send('OUTPut ON')

                gen_lo.send(f'OUTP:STAT ON')
                gen_rf.send(f'OUTP:STAT ON')

                osc.send(':CDISplay')

                # time.sleep(0.5)
                if not mock_enabled:
                    time.sleep(2)

                if mock_enabled:
                    _, stats = mocked_raw_data[index]
                else:
                    stats = osc.query(':MEASure:RESults?')

                stats_split = stats.split(',')
                osc_ch1_amp = float(stats_split[18])
                osc_ch2_amp = float(stats_split[25])
                osc_phase = float(stats_split[11])
                osc_ch1_freq = float(stats_split[4])

                timebase = (1 / (abs(freq_rf - freq_lo) * 10_000_000)) * 0.01
                osc.send(f':TIMEBASE:SCALE {timebase}')  # ms / div
                osc.send(f':CHANnel1:OFFSet 0')
                osc.send(f':CHANnel2:OFFSet 0')

                if not mock_enabled:
                    # second measure point goes out of OSC display range resulting in incorrect measurement
                    # this is correct device under measurement behaviour, not a bug
                    if osc_ch1_amp < 1_000_000 and osc_ch2_amp < 1_000_000:
                        # if reading is correct, scale OSC display as usual
                        rng = osc_ch1_amp + 0.3 * osc_ch1_amp
                        osc.send(f':CHANnel1:RANGe {rng}')
                        osc.send(f':CHANnel2:RANGe {rng}')
                    else:
                        # if not, reset OSC display range to guaranteed safe level
                        # and iterate OSC range scaling a few times
                        # to get the correct reading
                        while osc_ch1_amp > 1_000_000 or osc_ch2_amp > 1_000_000:
                            osc.send(f':CHANnel1:RANGe {osc_scale}')
                            osc.send(f':CHANnel2:RANGe {osc_scale}')

                            osc.send(':CDIS')

                            time.sleep(2)
                            osc_ch1_amp = float(osc.query(':MEASure:VAMPlitude? channel1'))
                            osc_ch2_amp = float(osc.query(':MEASure:VAMPlitude? channel2'))
                            rng = osc_ch1_amp + 0.3 * osc_ch1_amp
                            osc.send(f':CHANnel1:RANGe {rng}')
                            osc.send(f':CHANnel2:RANGe {rng}')

                p_lo_read = float(gen_lo.query('SOUR:POW?'))
                f_lo_read = float(gen_lo.query('SOUR:FREQ?'))

                p_rf_read = float(gen_rf.query('SOUR:POW?'))
                f_rf_read = float(gen_rf.query('SOUR:FREQ?'))

                i_src_read = float(mult.query('MEAS:CURR:DC? 1A,DEF'))

                raw_point = {
                    'p_lo': p_lo_read,
                    'f_lo': f_lo_read,
                    'p_rf': p_rf_read,
                    'f_rf': f_rf_read,
                    'u_src': src_u,   # power source voltage
                    'i_src': i_src_read,
                    'ch1_amp': osc_ch1_amp,
                    'ch2_amp': osc_ch2_amp,
                    'phase': osc_phase,
                    'ch1_freq': osc_ch1_freq,
                    'loss': loss,
                }

                if mock_enabled:
                    raw_point, stats = mocked_raw_data[index]
                    raw_point['loss'] = loss
                    index += 1

                print(raw_point, stats)
                self._add_measure_point(raw_point)

                res.append([raw_point, stats])

        gen_lo.send(f'OUTP:STAT OFF')
        gen_rf.send(f'OUTP:STAT OFF')
        time.sleep(0.5)
        src.send('OUTPut OFF')

        gen_rf.send(f'SOUR:POW {pow_rf}dbm')
        gen_lo.send(f'SOUR:POW {pow_lo_start}dbm')

        gen_rf.send(f'SOUR:FREQ {freq_rf_start}GHz')
        gen_lo.send(f'SOUR:FREQ {freq_rf_start}GHz')

        if not mock_enabled:
            with open('out.txt', mode='wt', encoding='utf-8') as f:
                f.write(str(res))

        return res

    def _add_measure_point(self, data):
        print('measured point:', data)
        self.result.add_point(data)
        self.pointReady.emit()

    def saveConfigs(self):
        with open('./params.ini', 'wt', encoding='utf-8') as f:
            pprint(self.secondaryParams, stream=f)

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]


def parse_float_list(lst):
    return [float(x) for x in lst.split(',')]
