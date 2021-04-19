import random

import pyqtgraph as pg

from PyQt6.QtWidgets import QGridLayout, QWidget
# from mytools import GraphWidget


# https://www.learnpyqt.com/tutorials/plotting-pyqtgraph/
# https://pyqtgraph.readthedocs.io/en/latest/introduction.html#what-is-pyqtgraph

class PrimaryPlotWidget(QWidget):

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        self._controller = controller   # TODO decouple from controller, use explicit result passing
        self.only_main_states = False

        self._grid = QGridLayout()

        self._win = pg.GraphicsLayoutWidget(show=True)
        self._win.setBackground('w')
        self._grid.addWidget(self._win, 0, 0)

        self._plot1 = self._win.addPlot(row=0, col=0)
        self._label = pg.LabelItem(justify='right')
        self._win.addItem(self._label, row=0, col=0)

        self._data1 = [30, 32, 34, 32, 33, 31, 29, 32, 35, 45]
        self._data2 = [50, 35, 44, 22, 38, 32, 27, 38, 32, 44]

        # matplotlib colors ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        self._curve1 = pg.PlotCurveItem(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            self._data1,
            pen=pg.mkPen(
                color='#1f77b4',
                width=2,
            ),
            symbol='o',
            symbolSize=5,
            symbolBrush='#1f77b4',
            name='test plot 1'
        )
        self._curve2 = pg.PlotCurveItem(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            self._data2,
            pen=pg.mkPen(
                color='#ff7f0e',
                width=2,
            ),
            symbol='o',
            symbolSize=5,
            symbolBrush='#ff7f0e',
            name='test plot 2'
        )
        self._plot1.addItem(self._curve1)
        self._plot1.addItem(self._curve2)
        style = {'color': 'k', 'font-size': '15px'}
        self._plot1.setLabel('left', 'y-s', **style)
        self._plot1.setLabel('bottom', 'x-es', **style)

        self._plot1.setXRange(0, 11, padding=0)
        self._plot1.setYRange(20, 55, padding=0)
        self._plot1.enableAutoRange('x')
        self._plot1.enableAutoRange('y')

        self._plot1.addLegend()
        self._plot1.showGrid(x=True, y=True)

        self._vb = self._plot1.vb
        self._vLine = pg.InfiniteLine(angle=90, movable=False)
        self._hLine = pg.InfiniteLine(angle=0, movable=False)
        self._plot1.addItem(self._vLine, ignoreBounds=True)
        self._plot1.addItem(self._hLine, ignoreBounds=True)
        self._proxy = pg.SignalProxy(self._plot1.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        self.setLayout(self._grid)

        self._init()

    def mouseMoved(self, evt):
        pos = evt[0]
        if self._plot1.sceneBoundingRect().contains(pos):
            mousePoint = self._vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            if index > 0 and index < len(self._data1):
                self._label.setText("Test plot: <span style='font-size: 12pt'>x=%0.1f,   <span style='color: #1f77b4'>y1=%0.1f</span>,   <span style='color: #ff7f0e'>y2=%0.1f</span>" % (mousePoint.x(),  self._data1[index], self._data2[index]))
            self._vLine.setPos(mousePoint.x())
            self._hLine.setPos(mousePoint.y())

    def _init(self, dev_id=0):
        pass

    def clear(self):
        pass

    def plot(self, dev_id=0):
        print('plotting primary stats')
        self.clear()
        self._init()

        self._data1 = [random.randint(0, 50) for _ in range(10)]
        self._data2 = [random.randint(0, 50) for _ in range(10)]
        self._curve1.setData(self._data1)
        self._curve2.setData(self._data2)
