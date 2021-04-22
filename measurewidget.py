from PyQt6 import uic
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtWidgets import QWidget, QDoubleSpinBox, QCheckBox

from deviceselectwidget import DeviceSelectWidget


class MeasureTask(QRunnable):

    def __init__(self, fn, end, token, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.end = end
        self.token = token
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(self.token, *self.args, **self.kwargs)
        self.end()


class CancelToken:
    def __init__(self):
        self.cancelled = False


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
        if not self._controller.present:
            print('sample not found')
            # QMessageBox.information(self, 'Ошибка', 'Не удалось найти образец, проверьте подключение')
            self._modePreCheck()
            return False

        print('found sample')
        self._modePreMeasure()
        self.sampleFound.emit()
        return True

    def measure(self):
        print('measuring...')
        self._modeDuringMeasure()
        self._threads.start(MeasureTask(self._controller.measure,
                                        self.measureTaskComplete,
                                        self._selectedDevice))

    def cancel(self):
        pass

    def measureTaskComplete(self):
        if not self._controller.hasResult:
            print('error during measurement')
            return False

        self._modePreCheck()
        self.measureComplete.emit()
        return True

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

    @pyqtSlot()
    def on_btnCancel_clicked(self):
        print('cancel click')
        self.cancel()

    @pyqtSlot(int)
    def on_selectedChanged(self, value):
        self._selectedDevice = value
        self.selectedChanged.emit(value)

    def _modePreConnect(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = True

    def _modePreCheck(self):
        self._ui.btnCheck.setEnabled(True)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = True

    def _modeDuringCheck(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = False

    def _modePreMeasure(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(True)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = False

    def _modeDuringMeasure(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(True)
        self._devices.enabled = False


class MeasureWidgetWithSecondaryParameters(MeasureWidget):
    secondaryChanged = pyqtSignal(dict)

    def __init__(self, parent=None, controller=None):
        super().__init__(parent=parent, controller=controller)

        self._token = CancelToken()

        self._params = 0

        self._spinPloMin = QDoubleSpinBox(parent=self)
        self._spinPloMin.setMinimum(-50)
        self._spinPloMin.setMaximum(50)
        self._spinPloMin.setSingleStep(1)
        self._spinPloMin.setValue(-10)
        self._spinPloMin.setSuffix(' дБм')
        self._devices._layout.addRow('Pгет мин=', self._spinPloMin)

        self._spinPloMax = QDoubleSpinBox(parent=self)
        self._spinPloMax.setMinimum(-50)
        self._spinPloMax.setMaximum(50)
        self._spinPloMax.setSingleStep(1)
        self._spinPloMax.setValue(-10)
        self._spinPloMax.setSuffix(' дБм')
        self._devices._layout.addRow('Pгет макс=', self._spinPloMax)

        self._spinPloDelta = QDoubleSpinBox(parent=self)
        self._spinPloDelta.setMinimum(-50)
        self._spinPloDelta.setMaximum(50)
        self._spinPloDelta.setSingleStep(1)
        self._spinPloDelta.setValue(1)
        self._spinPloDelta.setSuffix(' дБм')
        self._devices._layout.addRow('ΔPгет=', self._spinPloDelta)

        self._spinFloMin = QDoubleSpinBox(parent=self)
        self._spinFloMin.setMinimum(0)
        self._spinFloMin.setMaximum(40)
        self._spinFloMin.setSingleStep(1)
        self._spinFloMin.setValue(0.1)
        self._spinFloMin.setSuffix(' ГГц')
        self._devices._layout.addRow('Fгет.мин=', self._spinFloMin)

        self._spinFloMax = QDoubleSpinBox(parent=self)
        self._spinFloMax.setMinimum(0)
        self._spinFloMax.setMaximum(40)
        self._spinFloMax.setSingleStep(1)
        self._spinFloMax.setValue(3)
        self._spinFloMax.setSuffix(' ГГц')
        self._devices._layout.addRow('Fгет.макс=', self._spinFloMax)

        self._spinFloDelta = QDoubleSpinBox(parent=self)
        self._spinFloDelta.setMinimum(0)
        self._spinFloDelta.setMaximum(40)
        self._spinFloDelta.setSingleStep(0.1)
        self._spinFloDelta.setValue(0.1)
        self._spinFloDelta.setSuffix(' ГГц')
        self._devices._layout.addRow('ΔFгет=', self._spinFloDelta)

        self._spinPrf = QDoubleSpinBox(parent=self)
        self._spinPrf.setMinimum(-50)
        self._spinPrf.setMaximum(50)
        self._spinPrf.setSingleStep(1)
        self._spinPrf.setValue(-10)
        self._spinPrf.setSuffix(' дБм')
        self._devices._layout.addRow('Pвх.=', self._spinPrf)

        self._spinFrfMin = QDoubleSpinBox(parent=self)
        self._spinFrfMin.setMinimum(0)
        self._spinFrfMin.setMaximum(40)
        self._spinFrfMin.setSingleStep(1)
        self._spinFrfMin.setValue(0.11)
        self._spinFrfMin.setSuffix(' ГГц')
        self._devices._layout.addRow('Fвх.мин=', self._spinFrfMin)

        self._spinFrfMax = QDoubleSpinBox(parent=self)
        self._spinFrfMax.setMinimum(0)
        self._spinFrfMax.setMaximum(40)
        self._spinFrfMax.setSingleStep(1)
        self._spinFrfMax.setValue(3.1)
        self._spinFrfMax.setSuffix(' ГГц')
        self._devices._layout.addRow('Fвх.макс=', self._spinFrfMax)

        self._spinFrfDelta = QDoubleSpinBox(parent=self)
        self._spinFrfDelta.setMinimum(0)
        self._spinFrfDelta.setMaximum(40)
        self._spinFrfDelta.setSingleStep(0.1)
        self._spinFrfDelta.setValue(0.1)
        self._spinFrfDelta.setSuffix(' ГГц')
        self._devices._layout.addRow('ΔFвх.=', self._spinFrfDelta)

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
        self._spinPloMin.valueChanged.connect(self.on_params_changed)
        self._spinPloMax.valueChanged.connect(self.on_params_changed)
        self._spinPloDelta.valueChanged.connect(self.on_params_changed)
        self._spinFloMin.valueChanged.connect(self.on_params_changed)
        self._spinFloMax.valueChanged.connect(self.on_params_changed)
        self._spinFloDelta.valueChanged.connect(self.on_params_changed)

        self._spinPrf.valueChanged.connect(self.on_params_changed)
        self._spinFrfMin.valueChanged.connect(self.on_params_changed)
        self._spinFrfMax.valueChanged.connect(self.on_params_changed)
        self._spinFrfDelta.valueChanged.connect(self.on_params_changed)

        self._spinUsrc.valueChanged.connect(self.on_params_changed)

        self._checkOscAvg.toggled.connect(self.on_params_changed)

        self._spinLoss.valueChanged.connect(self.on_params_changed)

    def check(self):
        print('subclass checking...')
        self._modeDuringCheck()
        self._threads.start(
            MeasureTask(
                self._controller.check,
                self.checkTaskComplete,
                self._token,
                [self._selectedDevice, self._params]
            ))

    def checkTaskComplete(self):
        res = super(MeasureWidgetWithSecondaryParameters, self).checkTaskComplete()
        if not res:
            self._token = CancelToken()
        return res

    def measure(self):
        print('subclass measuring...')
        self._modeDuringMeasure()
        self._threads.start(
            MeasureTask(
                self._controller.measure,
                self.measureTaskComplete,
                self._token,
                [self._selectedDevice, self._params]
            ))

    def measureTaskComplete(self):
        res = super(MeasureWidgetWithSecondaryParameters, self).measureTaskComplete()
        if not res:
            self._token = CancelToken()
            self._modePreCheck()
        return res

    def cancel(self):
        print('cancelling task')
        if not self._token.cancelled:
            self._token.cancelled = True

    def on_params_changed(self, value):
        params = {
            'Plo_min': self._spinPloMin.value(),
            'Plo_max': self._spinPloMax.value(),
            'Plo_delta': self._spinPloDelta.value(),
            'Flo_min': self._spinFloMin.value(),
            'Flo_max': self._spinFloMax.value(),
            'Flo_delta': self._spinFloDelta.value(),

            'Prf': self._spinPrf.value(),
            'Frf_min': self._spinFrfMin.value(),
            'Frf_max': self._spinFrfMax.value(),
            'Frf_delta': self._spinFrfDelta.value(),

            'Usrc': self._spinUsrc.value(),

            'OscAvg': self._checkOscAvg.isChecked(),

            'Loss': self._spinLoss.value(),
        }
        self.secondaryChanged.emit(params)
