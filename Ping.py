__author__ = 'Hwaipy'
__version__= '1.0.0'

import sys
from PyQt5.QtWidgets import QTableWidget, QAction, QMainWindow, QAbstractItemView, QTableWidgetItem, QDesktopWidget, \
    QApplication
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import pyqtSignal
import re
import subprocess
from threading import Thread
import numpy as np

pingClick = 10


class Example(QMainWindow):
    reportAction = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.loadHosts()
        self.initUI()

    def loadHosts(self):
        with open('Hosts', 'rt') as f:
            hosts = f.read()
            hostNames = re.split("\n", hosts)
            self.pingProcesses = []
            for i in range(0, hostNames.__len__()):
                self.pingProcesses.append(PingProcess(hostNames[i], i, pingClick))

    def initUI(self):
        # Refresh Action with Toolbar and Shortcut
        self.refreshAction = QAction(QIcon("icons/refresh.png"), "Refresh", self)
        self.refreshAction.setShortcut(QKeySequence("Ctrl+R"))
        self.refreshAction.triggered.connect(self.actionRefresh)
        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.addAction(self.refreshAction)

        # Display host data
        self.table = QTableWidget(self.pingProcesses.__len__(), 6, self)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(['Host Name', 'IP Address', 'time', 'ttl', 'Progress', 'Failed'])
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 80)
        for pingProcess in self.pingProcesses:
            self.table.setItem(pingProcess.index, 0, QTableWidgetItem(pingProcess.hostName))

        # Setup Callback Actions
        self.reportAction.connect(self.updateResult)

        # Set main window
        self.setCentralWidget(self.table)
        self.setGeometry(300, 300, 700, 500)
        self.setWindowTitle('Review')
        self.centering()
        self.show()

    def actionRefresh(self):
        # Renew
        self.refreshAction.setEnabled(False)
        for pingProcess in self.pingProcesses:
            pingProcess.renew()
        self.actionPingProcessed = self.pingProcesses.copy()
        for i in range(self.pingProcesses.__len__()):
            for j in range(4, 6):
                self.table.setItem(i, j, QTableWidgetItem(''))

        for pingProcess in self.pingProcesses:
            t = Thread(target=self.ping, args=(pingProcess,))
            t.setDaemon(True)
            t.start()
        pass

    def centering(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def ping(self, pingProcess):
        for i in range(pingClick):
            pingProcess.ping()
            self.reportAction.emit(pingProcess)

    def updateResult(self, pingProcess):
        # in UI thread
        index = pingProcess.index
        results = pingProcess.result()
        for i in range(results.__len__()):
            self.table.setItem(index, i + 1, QTableWidgetItem(results[i]))
        if (pingProcess.finished()):
            if (self.actionPingProcessed.__contains__(pingProcess)):
                self.actionPingProcessed.remove(pingProcess)
            if (self.actionPingProcessed.__len__() == 0):
                self.refreshAction.setEnabled(True)


class PingProcess():
    def __init__(self, hostName, index, click):
        self.hostName = hostName
        self.index = index
        self.click = click
        self.success = 0
        self.fail = 0
        self.ttls = []
        self.times = []
        self.ip = None


    def ping(self):
        try:
            process = subprocess.Popen(["ping", "-c", "1", "-t", "1", self.hostName], stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            outB, errB = process.communicate()
            out = outB.decode('utf-8')
            lines = re.split('\n', out)
            match = re.match('.*\\((.*)\\).*', lines[0])
            ip = match.group(1)
            match = re.match('.*ttl=([0-9]+) time=([0-9.]+) ms', lines[1])
            ttl = int(match.group(1))
            time = int(float(match.group(2)))
            if (self.ip == None):
                self.ip = ip
            self.ttls.append(ttl)
            self.times.append(time)
            self.success += 1
        except Exception:
            self.fail += 1

    def result(self):
        ip = self.ip
        npTimes = np.array(self.times)
        npTtl = np.array(self.ttls)
        progress = '{0}/{1}'.format((self.success + self.fail), pingClick)
        failed = ''
        timeResult = ''
        ttlResult = ''
        if (ip == None):
            ip = 'Unknown'
        if (self.success > 0):
            timeResult = '{0} ms ({1} ms - {2} ms)'.format(int(npTimes.mean()), npTimes.min(), npTimes.max())
            ttlResult = '{0} ({1} - {2})'.format(int(npTtl.mean()), npTtl.min(), npTtl.max())
        if (self.fail > 0):
            failed = '{0} ({1}%)'.format(self.fail, int(self.fail / (self.fail + self.success) * 100))
        return ip, timeResult, ttlResult, progress, failed

    def finished(self):
        return self.success + self.fail >= pingClick

    def renew(self):
        self.success = 0
        self.fail = 0
        self.ttls = []
        self.times = []
        self.ip = None


if __name__ == '__main__':
    app = QApplication(sys.argv)
ex = Example()
sys.exit(app.exec_())