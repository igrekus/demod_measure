from PyQt6 import uic
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtWidgets import QWidget, QDoubleSpinBox, QCheckBox

from deviceselectwidget import DeviceSelectWidget


class MeasureTask(QRunnable):

    def __init__(self, fn, end, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.end = end
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(*self.args, **self.kwargs)
        self.end()


class MeasureWidget(QWidget):

    selectedChanged = pyqtSignal(int)
    sampleFound = pyqtSignal()
    measureComplete = pyqtSignal()
    measureStarted = pyqtSignal()

    def __init__(self, parent=None, controller=None):
        super().__init__(parent=parent)

        self._ui = uic.loadUi('measurewidget.ui', self)
        self._controller = controller
        self._threads = QThreadPool()

        self._devices = DeviceSelectWidget(parent=self, params=self._controller.deviceParams)
        self._ui.layParams.insertWidget(0, self._devices)
        self._devices.selectedChanged.connect(self.on_selectedChanged)

        self._selectedDevice = self._devices.selected

    def check(self):
        print('checking...')
        self._modeDuringCheck()
        self._threads.start(MeasureTask(self._controller.check,
                                        self.checkTaskComplete,
                                        self._selectedDevice))

    def checkTaskComplete(self):
        print('check complete')
        if not self._controller.present:
            print('sample not found')
            # QMessageBox.information(self, 'Ошибка', 'Не удалось найти образец, проверьте подключение')
            self._modePreCheck()
            return

        print('found sample')
        self._modePreMeasure()
        self.sampleFound.emit()

    def measure(self):
        print('measuring...')
        self._modeDuringMeasure()
        self._threads.start(MeasureTask(self._controller.measure,
                                        self.measureTaskComplete,
                                        self._selectedDevice))

    def measureTaskComplete(self):
        print('measure complete')
        if not self._controller.hasResult:
            print('error during measurement')
            return

        self._modePreCheck()
        self.measureComplete.emit()

    @pyqtSlot()
    def on_instrumentsConnected(self):
        self._modePreCheck()

    @pyqtSlot()
    def on_btnCheck_clicked(self):
        print('checking sample presence')
        self.check()

    @pyqtSlot()
    def on_btnMeasure_clicked(self):
        print('start measure')
        self.measureStarted.emit()
        self.measure()

    @pyqtSlot(int)
    def on_selectedChanged(self, value):
        self._selectedDevice = value
        self.selectedChanged.emit(value)

    def _modePreConnect(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._devices.enabled = True

    def _modePreCheck(self):
        self._ui.btnCheck.setEnabled(True)
        self._ui.btnMeasure.setEnabled(False)
        self._devices.enabled = True

    def _modeDuringCheck(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._devices.enabled = False

    def _modePreMeasure(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(True)
        self._devices.enabled = False

    def _modeDuringMeasure(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._devices.enabled = False


class MeasureWidgetWithSecondaryParameters(MeasureWidget):
    secondaryChanged = pyqtSignal(dict)

    def __init__(self, parent=None, controller=None):
        super().__init__(parent=parent, controller=controller)

        self._params = 0

        self._spinPowHetMin = QDoubleSpinBox(parent=self)
        self._spinPowHetMin.setMinimum(-50)
        self._spinPowHetMin.setMaximum(50)
        self._spinPowHetMin.setSingleStep(1)
        self._spinPowHetMin.setValue(-10)
        self._spinPowHetMin.setSuffix(' дБм')
        self._devices._layout.addRow('Pгет мин=', self._spinPowHetMin)

        self._spinPowHetMax = QDoubleSpinBox(parent=self)
        self._spinPowHetMax.setMinimum(-50)
        self._spinPowHetMax.setMaximum(50)
        self._spinPowHetMax.setSingleStep(1)
        self._spinPowHetMax.setValue(10)
        self._spinPowHetMax.setSuffix(' дБм')
        self._devices._layout.addRow('Pгет макс=', self._spinPowHetMax)

        self._spinPowHetDelta = QDoubleSpinBox(parent=self)
        self._spinPowHetDelta.setMinimum(-50)
        self._spinPowHetDelta.setMaximum(50)
        self._spinPowHetDelta.setSingleStep(1)
        self._spinPowHetDelta.setValue(1)
        self._spinPowHetDelta.setSuffix(' дБм')
        self._devices._layout.addRow('ΔPгет=', self._spinPowHetDelta)

        self._spinFhetMin = QDoubleSpinBox(parent=self)
        self._spinFhetMin.setMinimum(0)
        self._spinFhetMin.setMaximum(40)
        self._spinFhetMin.setSingleStep(1)
        self._spinFhetMin.setValue(1)
        self._spinFhetMin.setSuffix(' ГГц')
        self._devices._layout.addRow('Fгет.мин=', self._spinFhetMin)

        self._spinFhetMax = QDoubleSpinBox(parent=self)
        self._spinFhetMax.setMinimum(0)
        self._spinFhetMax.setMaximum(40)
        self._spinFhetMax.setSingleStep(1)
        self._spinFhetMax.setValue(3)
        self._spinFhetMax.setSuffix(' ГГц')
        self._devices._layout.addRow('Fгет.макс=', self._spinFhetMax)

        self._spinFhetDelta = QDoubleSpinBox(parent=self)
        self._spinFhetDelta.setMinimum(0)
        self._spinFhetDelta.setMaximum(40)
        self._spinFhetDelta.setSingleStep(0.1)
        self._spinFhetDelta.setValue(0.1)
        self._spinFhetDelta.setSuffix(' ГГц')
        self._devices._layout.addRow('ΔFгет=', self._spinFhetDelta)

        self._spinPowIn = QDoubleSpinBox(parent=self)
        self._spinPowIn.setMinimum(-50)
        self._spinPowIn.setMaximum(50)
        self._spinPowIn.setSingleStep(1)
        self._spinPowIn.setValue(-10)
        self._spinPowIn.setSuffix(' дБм')
        self._devices._layout.addRow('Pвх.=', self._spinPowIn)

        self._spinFinMin = QDoubleSpinBox(parent=self)
        self._spinFinMin.setMinimum(0)
        self._spinFinMin.setMaximum(40)
        self._spinFinMin.setSingleStep(1)
        self._spinFinMin.setValue(1)
        self._spinFinMin.setSuffix(' ГГц')
        self._devices._layout.addRow('Fвх.мин=', self._spinFinMin)

        self._spinFinMax = QDoubleSpinBox(parent=self)
        self._spinFinMax.setMinimum(0)
        self._spinFinMax.setMaximum(40)
        self._spinFinMax.setSingleStep(1)
        self._spinFinMax.setValue(3)
        self._spinFinMax.setSuffix(' ГГц')
        self._devices._layout.addRow('Fвх.макс=', self._spinFinMax)

        self._spinFinDelta = QDoubleSpinBox(parent=self)
        self._spinFinDelta.setMinimum(0)
        self._spinFinDelta.setMaximum(40)
        self._spinFinDelta.setSingleStep(0.1)
        self._spinFinDelta.setValue(0.1)
        self._spinFinDelta.setSuffix(' ГГц')
        self._devices._layout.addRow('ΔFвх.=', self._spinFinDelta)

        self._spinUsrc = QDoubleSpinBox(parent=self)
        self._spinUsrc.setMinimum(4.75)
        self._spinUsrc.setMaximum(5.25)
        self._spinUsrc.setSingleStep(0.25)
        self._spinUsrc.setValue(5)
        self._spinUsrc.setSuffix(' В')
        self._devices._layout.addRow('Uпит.=', self._spinUsrc)

        self._checkOscAvg = QCheckBox(parent=self)
        self._checkOscAvg.setChecked(False)
        self._devices._layout.addRow('Avg on/off', self._checkOscAvg)

        self._spinLoss = QDoubleSpinBox(parent=self)
        self._spinLoss.setMinimum(0)
        self._spinLoss.setMaximum(20)
        self._spinLoss.setSingleStep(0.1)
        self._spinLoss.setValue(0.82)
        self._spinLoss.setSuffix(' дБ')
        self._devices._layout.addRow('Loss=', self._spinLoss)

        self._connectSignals()

    def _connectSignals(self):
        self._spinPowHetMin.valueChanged.connect(self.on_params_changed)
        self._spinPowHetMax.valueChanged.connect(self.on_params_changed)
        self._spinPowHetDelta.valueChanged.connect(self.on_params_changed)
        self._spinFhetMin.valueChanged.connect(self.on_params_changed)
        self._spinFhetMax.valueChanged.connect(self.on_params_changed)
        self._spinFhetDelta.valueChanged.connect(self.on_params_changed)

        self._spinPowIn.valueChanged.connect(self.on_params_changed)
        self._spinFinMin.valueChanged.connect(self.on_params_changed)
        self._spinFinMax.valueChanged.connect(self.on_params_changed)
        self._spinFinDelta.valueChanged.connect(self.on_params_changed)

        self._spinUsrc.valueChanged.connect(self.on_params_changed)

        self._checkOscAvg.toggled.connect(self.on_params_changed)

        self._spinLoss.valueChanged.connect(self.on_params_changed)

    def _modePreConnect(self):
        super()._modePreConnect()

    def _modePreCheck(self):
        super()._modePreCheck()

    def _modeDuringCheck(self):
        super()._modeDuringCheck()

    def _modePreMeasure(self):
        super()._modePreMeasure()

    def _modeDuringMeasure(self):
        super()._modeDuringMeasure()

    def check(self):
        print('subclass checking...')
        self._modeDuringCheck()
        self._threads.start(MeasureTask(self._controller.check,
                                        self.checkTaskComplete,
                                        [self._selectedDevice, self._params]))

    def measure(self):
        print('subclass measuring...')
        self._modeDuringMeasure()
        self._threads.start(MeasureTask(self._controller.measure,
                                        self.measureTaskComplete,
                                        [self._selectedDevice, self._params]))

    def on_params_changed(self, value):
        params = {
            'Phet_min': self._spinPowHetMin.value(),
            'Phet_max': self._spinPowHetMax.value(),
            'Phet_delta': self._spinPowHetDelta.value(),
            'Fhet_min': self._spinFhetMin.value(),
            'Fhet_max': self._spinFhetMax.value(),
            'Fhet_delta': self._spinFhetDelta.value(),

            'Pin': self._spinPowIn.value(),
            'Fin_min': self._spinFinMin.value(),
            'Fin_max': self._spinFinMax.value(),
            'Fin_delta': self._spinFinDelta.value(),

            'Usrc': self._spinUsrc.value(),

            'OscAvg': self._checkOscAvg.isChecked(),

            'Loss': self._spinLoss.value(),
        }
        self.secondaryChanged.emit(params)
