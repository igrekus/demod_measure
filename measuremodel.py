from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant


class MeasureModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._headers = list()
        self._data = list()

        self._init()

    def _init(self):
        self._headers = ['1', '2', '3']

    def update(self):
        self.beginResetModel()
        self._init()
        self._data = ['a', 'b', 'c']
        self.endResetModel()

    def headerData(self, section, orientation, role=None):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section < len(self._headers):
                    return QVariant(self._headers[section])
        return QVariant()

    def rowCount(self, parent=None, *args, **kwargs):
        if parent.isValid():
            return 0
        return 1

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._headers)

    def data(self, index, role=None):
        if not index.isValid():
            return QVariant()
        if role == Qt.DisplayRole:
            try:
                return QVariant(self._data[index.column()])
            except LookupError:
                return QVariant()
        return QVariant()
