import pyqtgraph as pg

from PyQt6.QtWidgets import QGridLayout, QWidget, QLabel
from PyQt6.QtCore import Qt


# https://www.learnpyqt.com/tutorials/plotting-pyqtgraph/
# https://pyqtgraph.readthedocs.io/en/latest/introduction.html#what-is-pyqtgraph


class PrimaryPlotWidget(QWidget):
    label_style = {'color': 'k', 'font-size': '15px'}

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        self._controller = controller   # TODO decouple from controller, use explicit result passing
        self.only_main_states = False

        self._grid = QGridLayout()

        self._win = pg.GraphicsLayoutWidget(show=True)
        self._win.setBackground('w')

        self._stat_label = QLabel('Mouse position:')
        self._stat_label.setAlignment(Qt.Alignment.AlignRight)

        self._grid.addWidget(self._stat_label, 0, 0)
        self._grid.addWidget(self._win, 1, 0)

        self._plot_00 = self._win.addPlot(row=1, col=0)
        # self._plot_00.setTitle('К-т преобразования')

        self._plot_01 = self._win.addPlot(row=1, col=1)
        # self._plot_01.setTitle('αош, дБ')

        self._plot_10 = self._win.addPlot(row=2, col=0)
        # self._plot_10.setTitle('φош, градусы')

        self._plot_11 = self._win.addPlot(row=2, col=1)
        # self._plot_11.setTitle('αзк')

        # # matplotlib colors ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        self._curve_00 = None
        self._curve_01 = None
        self._curve_10 = None
        self._curve_11 = None

        self._plot_00.setLabel('left', 'Кп', **self.label_style)
        self._plot_00.setLabel('bottom', 'Fгет, ГГц', **self.label_style)
        # self._plot_00.setXRange(0, 11, padding=0)
        # self._plot_00.setYRange(20, 55, padding=0)
        self._plot_00.enableAutoRange('x')
        self._plot_00.enableAutoRange('y')
        # self._plot_00.addLegend()
        self._plot_00.showGrid(x=True, y=True)
        self._vb_00 = self._plot_00.vb
        self._vLine_00 = pg.InfiniteLine(angle=90, movable=False)
        self._hLine_00 = pg.InfiniteLine(angle=0, movable=False)
        self._plot_00.addItem(self._vLine_00, ignoreBounds=True)
        self._plot_00.addItem(self._hLine_00, ignoreBounds=True)
        self._proxy_00 = pg.SignalProxy(self._plot_00.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_00)

        self._plot_01.setLabel('left', 'αош, дБ', **self.label_style)
        self._plot_01.setLabel('bottom', 'Fгет, ГГц', **self.label_style)
        # self._plot_01.setXRange(0, 11, padding=0)
        # self._plot_01.setYRange(20, 55, padding=0)
        self._plot_01.enableAutoRange('x')
        self._plot_01.enableAutoRange('y')
        # self._plot_01.addLegend()
        self._plot_01.showGrid(x=True, y=True)
        self._vb_01 = self._plot_01.vb
        self._vLine_01 = pg.InfiniteLine(angle=90, movable=False)
        self._hLine_01 = pg.InfiniteLine(angle=0, movable=False)
        self._plot_01.addItem(self._vLine_01, ignoreBounds=True)
        self._plot_01.addItem(self._hLine_01, ignoreBounds=True)
        self._proxy_01 = pg.SignalProxy(self._plot_01.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_01)

        self._plot_10.setLabel('left', 'φош, градусы', **self.label_style)
        self._plot_10.setLabel('bottom', 'Fгет, ГГц', **self.label_style)
        # self._plot_10.setXRange(0, 11, padding=0)
        # self._plot_10.setYRange(20, 55, padding=0)
        self._plot_10.enableAutoRange('x')
        self._plot_10.enableAutoRange('y')
        # self._plot_10.addLegend()
        self._plot_10.showGrid(x=True, y=True)
        self._vb_10 = self._plot_10.vb
        self._vLine_10 = pg.InfiniteLine(angle=90, movable=False)
        self._hLine_10 = pg.InfiniteLine(angle=0, movable=False)
        self._plot_10.addItem(self._vLine_10, ignoreBounds=True)
        self._plot_10.addItem(self._hLine_10, ignoreBounds=True)
        self._proxy_10 = pg.SignalProxy(self._plot_10.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_10)

        self._plot_11.setLabel('left', 'αзк', **self.label_style)
        self._plot_11.setLabel('bottom', 'Fгет, ГГц', **self.label_style)
        # self._plot_11.setXRange(0, 11, padding=0)
        # self._plot_11.setYRange(20, 55, padding=0)
        self._plot_11.enableAutoRange('x')
        self._plot_11.enableAutoRange('y')
        # self._plot_11.addLegend()
        self._plot_11.showGrid(x=True, y=True)
        self._vb_11 = self._plot_11.vb
        self._vLine_11 = pg.InfiniteLine(angle=90, movable=False)
        self._hLine_11 = pg.InfiniteLine(angle=0, movable=False)
        self._plot_11.addItem(self._vLine_11, ignoreBounds=True)
        self._plot_11.addItem(self._hLine_11, ignoreBounds=True)
        self._proxy_11 = pg.SignalProxy(self._plot_11.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_11)

        self.setLayout(self._grid)

        self._init()

    # TODO fix y data query
    def mouseMoved_00(self, evt):
        pos = evt[0]
        if self._plot_00.sceneBoundingRect().contains(pos):
            mousePoint = self._vb_00.mapSceneToView(pos)
            self._vLine_00.setPos(mousePoint.x())
            self._hLine_00.setPos(mousePoint.y())
            if not self._curve_00 or len(self._curve_00.yData) == 0:
                return

            index = int(mousePoint.x())
            if index > 0 and index < len(self._curve_00.yData):
                self._stat_label.setText(_label_text(mousePoint.x(), self._curve_00.yData[index]))

    def mouseMoved_01(self, evt):
        pos = evt[0]
        if self._plot_01.sceneBoundingRect().contains(pos):
            mousePoint = self._vb_01.mapSceneToView(pos)
            self._vLine_01.setPos(mousePoint.x())
            self._hLine_01.setPos(mousePoint.y())
            if not self._curve_01 or len(self._curve_01.yData) == 0:
                return

            index = int(mousePoint.x())
            if index > 0 and index < len(self._curve_01.yData):
                self._stat_label.setText(_label_text(mousePoint.x(), self._curve_01.yData[index]))

    def mouseMoved_10(self, evt):
        pos = evt[0]
        if self._plot_10.sceneBoundingRect().contains(pos):
            mousePoint = self._vb_10.mapSceneToView(pos)
            self._vLine_10.setPos(mousePoint.x())
            self._hLine_10.setPos(mousePoint.y())
            if not self._curve_10 or len(self._curve_10.yData) == 0:
                return

            index = int(mousePoint.x())
            if index > 0 and index < len(self._curve_10.yData):
                self._stat_label.setText(_label_text(mousePoint.x(), self._curve_10.yData[index]))

    def mouseMoved_11(self, evt):
        pos = evt[0]
        if self._plot_11.sceneBoundingRect().contains(pos):
            mousePoint = self._vb_11.mapSceneToView(pos)
            self._vLine_11.setPos(mousePoint.x())
            self._hLine_11.setPos(mousePoint.y())
            if not self._curve_11 or len(self._curve_11.yData) == 0:
                return

            index = int(mousePoint.x())
            if index > 0 and index < len(self._curve_11.yData):
                self._stat_label.setText(_label_text(mousePoint.x(), self._curve_11.yData[index]))

    def _init(self):
        pass

    def clear(self):
        pass

    def plot(self):
        print('plotting primary stats')
        self.clear()
        self._init()

        curve_00_xs, curve_00_ys = zip(*self._controller.result.data1)
        curve_01_xs, curve_01_ys = zip(*self._controller.result.data2)
        curve_10_xs, curve_10_ys = zip(*self._controller.result.data3)
        curve_11_xs, curve_11_ys = zip(*self._controller.result.data4)

        if not self._curve_00:
            self._curve_00 = pg.PlotDataItem(
                curve_00_xs,
                curve_00_ys,
                pen=pg.mkPen(
                    color='#1f77b4',
                    width=2,
                ),
                symbol='o',
                symbolSize=5,
                symbolBrush='#1f77b4',
                name='Кп(fгет)'
            )
            self._plot_00.addItem(self._curve_00)
        else:
            self._curve_00.setData(curve_00_ys)

        if not self._curve_01:
            self._curve_01 = pg.PlotDataItem(
                curve_01_xs,
                curve_01_ys,
                pen=pg.mkPen(
                    color='#1f77b4',
                    width=2,
                ),
                symbol='o',
                symbolSize=5,
                symbolBrush='#1f77b4',
                name='Кп(fгет)'
            )
            self._plot_01.addItem(self._curve_01)
        else:
            self._curve_01.setData(curve_01_ys)

        if not self._curve_10:
            self._curve_10 = pg.PlotDataItem(
                curve_10_xs,
                curve_10_ys,
                pen=pg.mkPen(
                    color='#1f77b4',
                    width=2,
                ),
                symbol='o',
                symbolSize=5,
                symbolBrush='#1f77b4',
                name='поменять'
            )
            self._plot_10.addItem(self._curve_10)
        else:
            self._curve_10.setData(curve_10_ys)

        if not self._curve_11:
            self._curve_11 = pg.PlotDataItem(
                curve_11_xs,
                curve_11_ys,
                pen=pg.mkPen(
                    color='#1f77b4',
                    width=2,
                ),
                symbol='o',
                symbolSize=5,
                symbolBrush='#1f77b4',
                name='поменять'
            )
            self._plot_11.addItem(self._curve_11)
        else:
            self._curve_11.setData(curve_11_ys)


def _label_text(x, y):
    return f"<span style='font-size: 12pt'>Mouse: x={x:5.2f},   y={y:5.2f}</span>"
