import pyqtgraph as pg

from PyQt5.QtWidgets import QGridLayout, QWidget, QLabel
from PyQt5.QtCore import Qt


# https://www.learnpyqt.com/tutorials/plotting-pyqtgraph/
# https://pyqtgraph.readthedocs.io/en/latest/introduction.html#what-is-pyqtgraph

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
          '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class PrimaryPlotWidget(QWidget):
    label_style = {'color': 'k', 'font-size': '15px'}

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        self._controller = controller   # TODO decouple from controller, use explicit result passing
        self.only_main_states = False

        self._grid = QGridLayout()

        self._win = pg.GraphicsLayoutWidget(show=True)
        self._win.setBackground('w')

        self._stat_label = QLabel('Mouse:')
        self._stat_label.setAlignment(Qt.AlignRight)

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

        self._curves_00 = dict()
        self._curves_01 = dict()
        self._curves_10 = dict()
        self._curves_11 = dict()

        self._plot_00.setLabel('left', 'Кп', **self.label_style)
        self._plot_00.setLabel('bottom', 'Fгет, ГГц', **self.label_style)
        # self._plot_00.setXRange(0, 11, padding=0)
        # self._plot_00.setYRange(20, 55, padding=0)
        self._plot_00.enableAutoRange('x')
        self._plot_00.enableAutoRange('y')
        self._plot_00.addLegend(offset=(30, 300))
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
        self._plot_01.addLegend(offset=(30, 300))
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
        self._plot_10.addLegend(offset=(30, 30))
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
        self._plot_11.addLegend(offset=(30, 30))
        self._plot_11.showGrid(x=True, y=True)
        self._vb_11 = self._plot_11.vb
        self._vLine_11 = pg.InfiniteLine(angle=90, movable=False)
        self._hLine_11 = pg.InfiniteLine(angle=0, movable=False)
        self._plot_11.addItem(self._vLine_11, ignoreBounds=True)
        self._plot_11.addItem(self._hLine_11, ignoreBounds=True)
        self._proxy_11 = pg.SignalProxy(self._plot_11.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_11)

        self.setLayout(self._grid)

    # TODO fix y data query
    def mouseMoved_00(self, event):
        pos = event[0]
        if self._plot_00.sceneBoundingRect().contains(pos):
            mouse_point = self._vb_00.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self._vLine_00.setPos(x)
            self._hLine_00.setPos(y)
            if not self._curves_00:
                return

            self._stat_label.setText(_label_text(x, y, [
                [p, curve.yData[_find_value_index(curve.xData, x)]]
                for p, curve in self._curves_00.items()
            ]))

    def mouseMoved_01(self, event):
        pos = event[0]
        if self._plot_01.sceneBoundingRect().contains(pos):
            mouse_point = self._vb_01.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self._vLine_01.setPos(x)
            self._hLine_01.setPos(y)
            if not self._curves_01:
                return

            self._stat_label.setText(_label_text(x, y, [
                [p, curve.yData[_find_value_index(curve.xData, x)]]
                for p, curve in self._curves_01.items()
            ]))

    def mouseMoved_10(self, event):
        pos = event[0]
        if self._plot_10.sceneBoundingRect().contains(pos):
            mouse_point = self._vb_10.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self._vLine_10.setPos(x)
            self._hLine_10.setPos(y)
            if not self._curves_10:
                return

            self._stat_label.setText(_label_text(x, y, [
                [p, curve.yData[_find_value_index(curve.xData, x)]]
                for p, curve in self._curves_10.items()
            ]))

    def mouseMoved_11(self, event):
        pos = event[0]
        if self._plot_11.sceneBoundingRect().contains(pos):
            mouse_point = self._vb_11.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self._vLine_11.setPos(x)
            self._hLine_11.setPos(y)
            if not self._curves_11:
                return

            self._stat_label.setText(_label_text(x, y, [
                [p, curve.yData[_find_value_index(curve.xData, x)]]
                for p, curve in self._curves_11.items()
            ]))

    def clear(self):
        def _remove_curves(plot, curve_dict):
            for _, curve in curve_dict.items():
                plot.removeItem(curve)

        _remove_curves(self._plot_00, self._curves_00)
        _remove_curves(self._plot_01, self._curves_01)
        _remove_curves(self._plot_10, self._curves_10)
        _remove_curves(self._plot_11, self._curves_11)

        self._curves_00.clear()
        self._curves_01.clear()
        self._curves_10.clear()
        self._curves_11.clear()

    def plot(self):
        print('plotting primary stats')
        _plot_curves(self._controller.result.data1, self._curves_00, self._plot_00)
        _plot_curves(self._controller.result.data2, self._curves_01, self._plot_01)
        _plot_curves(self._controller.result.data3, self._curves_10, self._plot_10)
        _plot_curves(self._controller.result.data4, self._curves_11, self._plot_11)


def _plot_curves(datas, curves, plot):
    for pow_lo, data in datas.items():
        curve_xs, curve_ys = zip(*data)
        try:
            curves[pow_lo].setData(x=curve_xs, y=curve_ys)
        except KeyError:
            try:
                color = colors[len(curves)]
            except IndexError:
                color = colors[len(curves) - len(colors)]
            curves[pow_lo] = pg.PlotDataItem(
                curve_xs,
                curve_ys,
                pen=pg.mkPen(
                    color=color,
                    width=2,
                ),
                symbol='o',
                symbolSize=5,
                symbolBrush=color,
                name=f'{pow_lo} дБм'
            )
            plot.addItem(curves[pow_lo])


def _label_text(x, y, vals):
    vals_str = ''.join(f'   <span style="color:{colors[i]}">{p:0.1f}={v:0.2f}</span>' for i, (p, v) in enumerate(vals))
    return f"<span style='font-size: 8pt'>x={x:0.2f},   y={y:0.2f}   {vals_str}</span>"


def _find_value_index(freqs: list, freq):
    return min(range(len(freqs)), key=lambda i: abs(freqs[i] - freq))
