import time

from os.path import isfile
from PyQt6.QtCore import QObject, pyqtSlot

from instr.instrumentfactory import mock_enabled, OscilloscopeFactory, GeneratorFactory, SourceFactory, \
    MultimeterFactory, AnalyzerFactory
from measureresult import MeasureResult


class InstrumentController(QObject):
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

        self.result = None

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

    def check(self, params):
        print(f'call check with {params}')
        device, secondary = params
        self.present = self._check(device, secondary)
        print('sample pass')

    def _check(self, device, secondary):
        print(f'launch check with {self.deviceParams[device]} {self.secondaryParams}')
        return self._runCheck(self.deviceParams[device], self.secondaryParams)

    def _runCheck(self, param, secondary):
        print(f'run check with {param}, {secondary}')
        return True

    def measure(self, params):
        print(f'call measure with {params}')
        device, _ = params
        self.result = MeasureResult(self._measure(device), self.secondaryParams)
        self.hasResult = bool(self.result)

    def _measure(self, device):
        param = self.deviceParams[device]
        secondary = self.secondaryParams
        print(f'launch measure with {param} {secondary}')

        self._clear()
        self._init()

        return self._measure_s_params(param, secondary)

    def _clear(self):
        pass

    def _init(self):
        self._instruments['P LO'].send('*RST')
        self._instruments['P RF'].send('*RST')
        self._instruments['Осциллограф'].send('*RST')
        self._instruments['Источник'].send('*RST')
        self._instruments['Мультиметр'].send('*RST')
        self._instruments['Анализатор'].send('*RST')

    def _measure_s_params(self, param, secondary):
        gen1 = self._instruments['P LO']
        gen2 = self._instruments['P RF']
        osc = self._instruments['Осциллограф']
        src = self._instruments['Источник']
        mult = self._instruments['Мультиметр']
        pna = self._instruments['Анализатор']

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

        return [1, 2, 3]

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]


def parse_float_list(lst):
    return [float(x) for x in lst.split(',')]
