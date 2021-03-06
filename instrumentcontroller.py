import ast
import time

import numpy as np

from collections import defaultdict
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

from instr.instrumentfactory import mock_enabled, OscilloscopeFactory, GeneratorFactory, SourceFactory, \
    MultimeterFactory, AnalyzerFactory
from measureresult import MeasureResult
from forgot_again.file import load_ast_if_exists, pprint_to_file


class InstrumentController(QObject):
    pointReady = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        addrs = load_ast_if_exists('instr.ini', default={
            'Осциллограф': 'GPIB1::7::INSTR',
            'Анализатор': 'GPIB1::18::INSTR',
            'P LO': 'GPIB1::6::INSTR',
            'P RF': 'GPIB1::20::INSTR',
            'Источник': 'GPIB1::3::INSTR',
            'Мультиметр': 'GPIB1::22::INSTR',
        })

        self.requiredInstruments = {
            'Осциллограф': OscilloscopeFactory(addrs['Осциллограф']),
            'Анализатор': AnalyzerFactory(addrs['Анализатор']),
            'P LO': GeneratorFactory(addrs['P LO']),
            'P RF': GeneratorFactory(addrs['P RF']),
            'Источник': SourceFactory(addrs['Источник']),
            'Мультиметр': MultimeterFactory(addrs['Мультиметр']),
        }

        self.deviceParams = {
            '+25': {
                'adjust': 'adjust_+25.ini',
                'result': 'table_+25.xlsx',
            },
            '-60': {
                'adjust': 'adjust_-60.ini',
                'result': 'table_-60.xlsx',
            },
            '+85': {
                'adjust': 'adjust_+85.ini',
                'result': 'table_+85.xlsx',
            },
        }

        self.secondaryParams = load_ast_if_exists('params.ini', default={
            'Plo_min': -10.0,
            'Plo_max': -10.0,
            'Plo_delta': 1.0,
            'Flo_min': 0.1,
            'Flo_max': 3.0,
            'Flo_delta': 0.1,
            'is_Flo_x2': False,
            'Prf': -10.0,
            'Frf_min': 0.11,
            'Frf_max': 3.1,
            'Frf_delta': 0.1,
            'Usrc': 5.0,
            'UsrcD': 3.3,
            'OscAvg': True,
            'D': False,
            'loss': 0.82,
            'scale_y': 0.2,
            'timebase_coeff': 1.0,
        })

        self._calibrated_pows_lo = load_ast_if_exists('cal_lo.ini', default={})
        self._calibrated_pows_rf = load_ast_if_exists('cal_rf.ini', default={})

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

        pow_lo_start = secondary['Plo_min']
        pow_lo_end = secondary['Plo_max']
        pow_lo_step = secondary['Plo_delta']
        freq_lo_start = secondary['Flo_min']
        freq_lo_end = secondary['Flo_max']
        freq_lo_step = secondary['Flo_delta']
        freq_lo_x2 = secondary['is_Flo_x2']

        pow_lo_values = [round(x, 3) for x in np.arange(start=pow_lo_start, stop=pow_lo_end + 0.002, step=pow_lo_step)] \
            if pow_lo_start != pow_lo_end else [pow_lo_start]
        freq_lo_values = [round(x, 3) for x in
                          np.arange(start=freq_lo_start, stop=freq_lo_end + 0.0001, step=freq_lo_step)]

        sa.send(':CAL:AUTO OFF')
        sa.send(':SENS:FREQ:SPAN 1MHz')
        sa.send(f'DISP:WIND:TRAC:Y:RLEV 10')
        sa.send(f'DISP:WIND:TRAC:Y:PDIV 5')

        gen_lo.send(f':OUTP:MOD:STAT OFF')

        sa.send(':CALC:MARK1:MODE POS')

        result = defaultdict(dict)
        for pow_lo in pow_lo_values:
            gen_lo.send(f'SOUR:POW {pow_lo}dbm')

            for freq in freq_lo_values:

                if freq_lo_x2:
                    freq *= 2

                if token.cancelled:
                    gen_lo.send(f'OUTP:STAT OFF')
                    time.sleep(0.5)

                    gen_lo.send(f'SOUR:POW {pow_lo}dbm')

                    gen_lo.send(f'SOUR:FREQ {freq_lo_start}GHz')
                    raise RuntimeError('calibration cancelled')

                gen_lo.send(f'SOUR:FREQ {freq}GHz')
                gen_lo.send(f'OUTP:STAT ON')

                if not mock_enabled:
                    time.sleep(0.35)

                sa.send(f':SENSe:FREQuency:CENTer {freq}GHz')
                sa.send(f':CALCulate:MARKer1:X:CENTer {freq}GHz')

                if not mock_enabled:
                    time.sleep(0.35)

                pow_read = float(sa.query(':CALCulate:MARKer:Y?'))
                loss = abs(pow_lo - pow_read)
                if mock_enabled:
                    loss = 10

                print('loss: ', loss)
                result[pow_lo][freq] = loss

        result = {k: v for k, v in result.items()}
        pprint_to_file('cal_lo.ini', result)

        gen_lo.send(f'OUTP:STAT OFF')
        sa.send(':CAL:AUTO ON')
        self._calibrated_pows_lo = result
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
                time.sleep(0.35)

            sa.send(f':SENSe:FREQuency:CENTer {freq}GHz')
            sa.send(f':CALCulate:MARKer1:X:CENTer {freq}GHz')

            if not mock_enabled:
                time.sleep(0.35)

            pow_read = float(sa.query(':CALCulate:MARKer:Y?'))
            loss = abs(pow_rf - pow_read)
            if mock_enabled:
                loss = 10

            print('loss: ', loss)
            result[freq] = loss

        pprint_to_file('cal_rf.ini', result)

        gen_rf.send(f'OUTP:STAT OFF')
        sa.send(':CAL:AUTO ON')
        self._calibrated_pows_rf = result
        return True

    def measure(self, token, params):
        print(f'call measure with {token} {params}')
        device, _ = params
        try:
            self.result.set_secondary_params(self.secondaryParams)
            self.result.set_primary_params(self.deviceParams[device])
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
        src_u_d = secondary['UsrcD']
        src_i_d = 100  # mA
        pow_lo_start = secondary['Plo_min']
        pow_lo_end = secondary['Plo_max']
        pow_lo_step = secondary['Plo_delta']
        freq_lo_start = secondary['Flo_min']
        freq_lo_end = secondary['Flo_max']
        freq_lo_step = secondary['Flo_delta']
        freq_lo_x2 = secondary['is_Flo_x2']

        pow_rf = secondary['Prf']
        freq_rf_start = secondary['Frf_min']
        freq_rf_end = secondary['Frf_max']
        freq_rf_step = secondary['Frf_delta']

        loss = secondary['loss']

        osc_avg = 'ON' if secondary['OscAvg'] else 'OFF'
        d = secondary['D']

        osc_scale = secondary['scale_y']
        osc_timebase_coeff = secondary['timebase_coeff']

        src.send(f'APPLY p6v,{src_u}V,{src_i}mA')
        src.send(f'APPLY p25v,{src_u_d}V,{src_i_d}mA')

        osc.send(f':ACQ:AVERage {osc_avg}')

        osc.send(f':CHANnel1:DISPlay ON')
        osc.send(f':CHANnel2:DISPlay ON')

        osc.send(f':CHAN1:SCALE {osc_scale}')  # V
        osc.send(f':CHAN2:SCALE {osc_scale}')
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
        gen_f_mul = 2 if d else 1

        pow_lo_values = [round(x, 3) for x in np.arange(start=pow_lo_start, stop=pow_lo_end + 0.0001, step=pow_lo_step)] \
            if pow_lo_start != pow_lo_end else [pow_lo_start]
        freq_lo_values = [round(x, 3) for x in
                          np.arange(start=freq_lo_start, stop=freq_lo_end + 0.0001, step=freq_lo_step)]
        freq_rf_values = [round(x, 3) for x in
                          np.arange(start=freq_rf_start, stop=freq_rf_end + 0.0001, step=freq_rf_step)]

        gen_lo.send(f':OUTP:MOD:STAT OFF')
        # gen_rf.send(f':OUTP:MOD:STAT OFF')
        gen_lo.send(f':FREQ:MULT {gen_f_mul}')
        gen_rf.send(f':FREQ:MULT {gen_f_mul}')

        low_signal_threshold = 1.1
        range_ratio = 1.2
        upscale_ratio = 1.3

        if mock_enabled:
            # with open('./mock_data/meas_1_-10-5db.txt', mode='rt', encoding='utf-8') as f:
            with open('./mock_data/meas_1_-10db.txt', mode='rt', encoding='utf-8') as f:
                index = 0
                mocked_raw_data = ast.literal_eval(''.join(f.readlines()))

        res = []
        for pow_lo in pow_lo_values:

            for freq_lo, freq_rf in zip(freq_lo_values, freq_rf_values):

                if freq_lo_x2:
                    freq_lo *= 2

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

                gen_lo.send(f'SOUR:POW {round(pow_lo + self._calibrated_pows_lo.get(pow_lo, dict()).get(freq_lo, 0) / 2, 2)}dbm')
                gen_rf.send(f'SOUR:POW {round(pow_rf + self._calibrated_pows_rf.get(freq_rf, 0) / 2, 2)}dbm')

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

                # read amp values
                if mock_enabled:
                    _, stats = mocked_raw_data[index]
                else:
                    stats = osc.query(':MEASure:RESults?')

                stats_split = stats.split(',')
                osc_ch1_amp = float(stats_split[18])
                osc_ch2_amp = float(stats_split[25])
                osc_phase = float(stats_split[11])
                osc_ch1_freq = float(stats_split[4])

                timebase = (1 / (abs(freq_rf - (
                    (freq_lo / 2) if freq_lo_x2 else freq_lo)) * 10_000_000)) * 0.01 * osc_timebase_coeff
                osc.send(f':TIMEBASE:SCALE {timebase}')  # ms / div
                osc.send(f':CHANnel1:OFFSet 0')
                osc.send(f':CHANnel2:OFFSet 0')

                max_amp = osc_ch1_amp if osc_ch1_amp > osc_ch2_amp else osc_ch2_amp

                if not mock_enabled:
                    # check if auto-scale is needed:
                    # some of the measure points go out of OSC display range resulting in incorrect measurement
                    # this is correct external device behaviour, not a program bug
                    if max_amp < 1_000_000:
                        # if reading is correct, check if the signal is too small
                        big_amp, ch_num = (osc_ch1_amp, 1) if osc_ch1_amp > osc_ch2_amp else (osc_ch2_amp, 2)
                        current_scale = float(osc.query(f':CHAN{ch_num}:SCALE?'))

                        # if signal fits in less than 1.5 sections of the display, is is too small, need to
                        # auto scale OSC display up
                        while big_amp / current_scale <= low_signal_threshold:

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

                            target_range = big_amp + big_amp * range_ratio

                            osc.send(f':CHANnel1:RANGe {target_range}')
                            osc.send(f':CHANnel2:RANGe {target_range}')

                            osc.send(':CDIS')

                            time.sleep(2)

                            autofit_stats_split = osc.query(':MEASure:RESults?').split(',')

                            osc_ch1_amp = float(autofit_stats_split[18])
                            osc_ch2_amp = float(autofit_stats_split[25])

                            big_amp, ch_num = (osc_ch1_amp, 1) if osc_ch1_amp > osc_ch2_amp else (osc_ch2_amp, 2)
                            current_scale = float(osc.query(f':CHAN{ch_num}:SCALE?'))
                    # TODO fix this branch for small signal behaviour
                    else:
                        # if reading was not correct, reset OSC display range to safe level (controlled via GUI)
                        # and iterate OSC range scaling a few times
                        # to get the correct reading
                        max_amp = osc_ch1_amp if osc_ch1_amp > osc_ch2_amp else osc_ch2_amp
                        if max_amp > 1_000_000:
                            new_scale = osc_scale * upscale_ratio

                            osc.send(f':CHANnel1:scale {new_scale}')
                            osc.send(f':CHANnel2:scale {new_scale}')

                            osc.send(':CDIS')

                            time.sleep(2)

                            autofit_stats_split = osc.query(':MEASure:RESults?').split(',')
                            osc_ch1_amp = float(autofit_stats_split[18])
                            osc_ch2_amp = float(autofit_stats_split[25])

                            # check if safe level results in too small signal
                            big_amp, ch_num = (osc_ch1_amp, 1) if osc_ch1_amp > osc_ch2_amp else (osc_ch2_amp, 2)

                            while big_amp > 1_000_000:

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

                                new_scale *= upscale_ratio

                                osc.send(f':CHANnel1:scale {new_scale}')
                                osc.send(f':CHANnel2:scale {new_scale}')

                                osc.send(':CDIS')

                                time.sleep(2)

                                autofit_stats_split = osc.query(':MEASure:RESults?').split(',')

                                osc_ch1_amp = float(autofit_stats_split[18])
                                osc_ch2_amp = float(autofit_stats_split[25])

                                big_amp, ch_num = (osc_ch1_amp, 1) if osc_ch1_amp > osc_ch2_amp else (osc_ch2_amp, 2)
                            else:
                                # if safe level is acceptable, select largest signal
                                # and fit the display to 130% of the signal
                                target_range = big_amp * range_ratio
                                osc.send(f':CHANnel1:RANGe {target_range}')
                                osc.send(f':CHANnel2:RANGe {target_range}')

                # read actual amp values after auto-scale (if any occured)
                osc.send(':CDIS')

                if not mock_enabled:
                    time.sleep(2)

                if mock_enabled:
                    _, stats = mocked_raw_data[index]
                else:
                    stats = osc.query(':MEASure:RESults?')
                stats_split = stats.split(',')
                osc_ch1_amp = float(stats_split[18])
                osc_ch2_amp = float(stats_split[25])

                f_lo_read = float(gen_lo.query('SOUR:FREQ?'))
                f_rf_read = float(gen_rf.query('SOUR:FREQ?'))

                i_src_read = float(mult.query('MEAS:CURR:DC? 1A,DEF'))

                raw_point = {
                    'p_lo': pow_lo,
                    'f_lo': f_lo_read,
                    'p_rf': pow_rf,
                    'f_rf': f_rf_read,
                    'u_src': src_u,  # power source voltage
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

                # time.sleep(120)

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
        pprint_to_file('params.ini', self.secondaryParams)

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]
