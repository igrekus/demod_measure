import ast
import random
import time

import numpy as np

from os.path import isfile
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal

from instr.instrumentfactory import mock_enabled, OscilloscopeFactory, GeneratorFactory, SourceFactory, \
    MultimeterFactory, AnalyzerFactory
from measureresult import MeasureResult


class InstrumentController(QObject):
    pointReady = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.requiredInstruments = {
            'Осциллограф': OscilloscopeFactory('GPIB1::7::INSTR'),
            'P LO': GeneratorFactory('GPIB1::6::INSTR'),
            'P RF': GeneratorFactory('GPIB1::20::INSTR'),
            'Источник': SourceFactory('GPIB1::3::INSTR'),
            'Мультиметр': MultimeterFactory('GPIB1::22::INSTR'),
            'Анализатор': AnalyzerFactory('GPIB1::18::INSTR'),
        }

        self.deviceParams = {
            'Демодулятор': {
                'F': 1,
            },
        }

        if isfile('./params.ini'):
            import ast
            with open('./params.ini', 'rt', encoding='utf-8') as f:
                raw = ''.join(f.readlines())
                self.deviceParams = ast.literal_eval(raw)

        self.secondaryParams = {}

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
        return True

    def measure(self, token, params):
        print(f'call measure with {token} {params}')
        device, _ = params
        try:
            self.result.set_secondary_params(self.secondaryParams)
            self._measure(token, device)
            # self.hasResult = bool(self.result)
            self.hasResult = True   # HACK
        except RuntimeError as ex:
            print('runtime error:', ex)

    def _measure(self, token, device):
        param = self.deviceParams[device]
        secondary = self.secondaryParams
        print(f'launch measure with {token} {param} {secondary}')

        self._clear()
        self._init()
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
        self._instruments['Анализатор'].send('*RST')

    def _measure_s_params(self, token, param, secondary):
        gen_lo = self._instruments['P LO']
        gen_rf = self._instruments['P RF']
        osc = self._instruments['Осциллограф']
        src = self._instruments['Источник']
        mult = self._instruments['Мультиметр']
        sa = self._instruments['Анализатор']

        src_u = secondary['Usrc']
        src_i = 200   # mA
        pow_lo_start = secondary['Plo_min']
        pow_lo_end = secondary['Plo_max']
        pow_lo_step = secondary['Plo_delta']
        freq_lo_start = secondary['Flo_min']
        freq_lo_end = secondary['Flo_max']
        freq_lo_step = secondary['Flo_delta']

        pow_rf = secondary['Prf']
        freq_rf_start = secondary['Frf_min']
        freq_rf_end = secondary['Frf_max']
        freq_rf_step = secondary['Frf_delta']

        loss = secondary['Loss']

        osc_avg = 'ON' if secondary['OscAvg'] else 'OFF'

        src.send(f'APPLY p6v,{src_u}V,{src_i}mA')

        osc.send(f':ACQ:AVERage {osc_avg}')

        osc.send(f':CHANnel1:DISPlay ON')
        osc.send(f':CHANnel2:DISPlay ON')

        osc.send(':CHAN1:SCALE 0.05')   # V
        osc.send(':CHAN2:SCALE 0.05')
        osc.send(':TIMEBASE:SCALE 10E-8')   # ms / div

        osc.send(':TRIGger:MODE EDGE')
        osc.send(':TRIGger:EDGE:SOURCe CHANnel1')
        osc.send(':TRIGger:LEVel CHANnel1,0')
        osc.send(':TRIGger:EDGE:SLOPe POSitive')

        osc.send(':MEASure:VAMPlitude channel1')
        osc.send(':MEASure:VAMPlitude channel2')
        osc.send(':MEASure:PHASe CHANnel1,CHANnel2')
        osc.send(':MEASure:FREQuency CHANnel1')

        pow_lo_values = [round(x, 3) for x in np.arange(start=pow_lo_start, stop=pow_lo_end + 0.2, step=pow_lo_step)]
        freq_lo_values = [round(x, 3) for x in np.arange(start=freq_lo_start, stop=freq_lo_end + 0.2, step=freq_lo_step)]
        freq_rf_values = [round(x, 3) for x in np.arange(start=freq_rf_start, stop=freq_rf_end + 0.2, step=freq_rf_step)]

        gen_rf.send(f'SOUR:POW {pow_rf}dbm')

        if mock_enabled:
            index = 0
            with open('mock_data/meas_1_-10db.txt', mode='rt', encoding='utf-8') as f:
                mocked_raw_data = ast.literal_eval(''.join(f.readlines()))

        res = []
        for pow_lo in pow_lo_values:
            gen_lo.send(f'SOUR:POW {pow_lo}dbm')

            for freq_lo, freq_rf in zip(freq_lo_values, freq_rf_values):
                if token.cancelled:
                    raise RuntimeError('measurement cancelled')

                gen_lo.send(f'SOUR:FREQ {freq_lo}GHz')
                gen_rf.send(f'SOUR:FREQ {freq_rf}GHz')

                # TODO hoist out of the loops
                src.send('OUTPut ON')

                gen_lo.send(f'OUTP:STAT ON')
                gen_rf.send(f'OUTP:STAT ON')

                osc.send(':CDISplay')

                # time.sleep(0.1)
                # if not mock_enabled:
                #     time.sleep(3)

                # label, current, result(-), min, max, mean, std dev, times
                # TODO read mean instead of current
                stats = osc.query(':MEASure:RESults?')

                osc_ch1_amp = float(osc.query(':MEASure:VAMPlitude? channel1'))
                osc_ch2_amp = float(osc.query(':MEASure:VAMPlitude? channel2'))
                osc_phase = float(osc.query(':MEASure:PHASe? CHANnel1,CHANnel2'))
                osc_ch1_freq = float(osc.query(':MEASure:FREQuency? CHANnel1'))

                timebase = (1 / (abs(freq_rf - freq_lo) * 10_000_000)) * 0.01
                osc.send(f':TIMEBASE:SCALE {timebase}')   # ms / div
                osc.send(f':CHANnel1:OFFSet 0')
                osc.send(f':CHANnel2:OFFSet 0')

                rng = osc_ch1_amp + 0.3 * osc_ch1_amp
                osc.send(f':CHANnel1:RANGe {rng}')
                osc.send(f':CHANnel2:RANGe {rng}')

                if not mock_enabled:
                    while rng > 1_000_000:
                        osc.send(f':CHANnel1:RANGe 0.2')
                        osc.send(f':CHANnel2:RANGe 0.2')

                        osc.send(':CDIS')

                        time.sleep(2)
                        osc_ch1_amp = float(osc.query(':MEASure:VAMPlitude? channel1'))
                        rng = osc_ch1_amp + 0.3 * osc_ch1_amp
                        osc.send(f':CHANnel1:RANGe {rng}')
                        osc.send(f':CHANnel2:RANGe {rng}')

                p_lo_read = float(gen_lo.query('SOUR:POW?'))
                f_lo_read = float(gen_lo.query('SOUR:FREQ?'))

                p_rf_read = float(gen_rf.query('SOUR:POW?'))
                f_rf_read = float(gen_rf.query('SOUR:FREQ?'))

                u_src_read = float(src.query('MEAS:VOLT?'))
                i_src_read = float(src.query('MEAS:CURR?'))

                raw_point = {
                    'p_lo': p_lo_read,
                    'f_lo': f_lo_read,
                    'p_rf': p_rf_read,
                    'f_rf': f_rf_read,
                    'u_src': u_src_read,
                    'i_src': i_src_read,
                    'ch1_amp': osc_ch1_amp,
                    'ch2_amp': osc_ch2_amp,
                    'phase': osc_phase,
                    'ch1_freq': osc_ch1_freq,
                    'loss': loss,
                }
                # to show:
                # + p_lo, f_lo
                # + p_rf, f_rf
                # + u_src, i_src
                # + ch1_amp. ch2_amp, ch2_amp - ch1_amp, phase, ch1_freq

                # расчеты:
                # + мощность сигнала пч по каналу 1: Ppch = 30 + 1 * log10(((ch1_amp/2 * 0.001) ^ 2) / 100)
                # + к-т передачи с учетом потерь: Kp = Ppch - Prf + Pbal
                # + амп. ошибка в разах: aerr_times = ch2_amp / chi1_amp
                # + амп. ош в дБ: aerr_db = 20 * log10(ch2_amp * 0.001) - 20 * log10(ch1_amp * 0.001)
                # + фаз. ош в град: pherr = delta_pherr + 90
                # + подавление зерк. канала: azk = 10 * log10((1 + aerr_times ^ 2 - 2 * aerr_times * cos(rad(pherr)))
                # / (1 + aerr_times ^ 2 + 2 * aerr_times * cos(rad(pherr))))

                if mock_enabled:
                    raw_point, stats = mocked_raw_data[index]
                    index += 1
                    raw_point['loss'] = loss

                print(raw_point, stats)
                self._add_measure_point(raw_point)

                res.append([raw_point, stats])

        # with open('out.txt', mode='wt', encoding='utf-8') as f:
        #     f.send(str(res))

        return res

    def _add_measure_point(self, data):
        print('measured point:', data)
        self.result.add_point(data)
        self.pointReady.emit()

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]


def parse_float_list(lst):
    return [float(x) for x in lst.split(',')]


"""
питание питоание из интерфейса, предел по току 200мА

осциллограф - авереджинг
                вкл канал 1
                вкл канал 2
                
                кан оффсет 1 = 0
                кан оффсет 2 = 0
                
                кан 1/2 масштаб 50 мВ (scale)
                
                триггер канал 1 - edge, 0 mV, raising front
                
                add measurement -> vertical -> amplitude -> chan 1        
                add measurement -> vertical -> amplitude -> chan 2
                add measurement -> clock -> phase -> src1 = chan 1, src2 = chan 2
                add measurement -> clock -> freq -> src1 = chan 1

p lo: cycle power (Pmin -> Pmax with deltaP)
                
    p lo: set power - п гет вх
          ф гет мин = ф мин
          ф гет мин = ф макс
          дельта ф = дельта ф
          (свип по шагу -- цикл в коде)
    
        p rf внутр цикл
            п вх - п фх
            ф мин
            ф макс
            дельта ф
            (цикл по частоте рф генератора с шагом)
                            
            считаываем ф ло, ф рф, показываем дельту
            
            src: вкл источник пит
            
            osc: get min-max measure, calc scale factor on each cycle
            
            src: read and show src current, src voltage
            
            osc: get chan 1 v ampl, get chan 2 v amp
            osc: get chan 1 v [hase, get chan 2 v phase - calc delta phase
            osc: get chan 1 freq
            cave to result list  -> plot real time, overlay with different pows
            
            

add measurement delay to gui parameters, clear measurement display for osc to reset avg stats
"""
