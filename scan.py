"""
Created by Xuejian Ma at 10/2/2021.
All rights reserved.
"""
from pyqtgraph import mkPen

from pyparktiff import SaveParkTiff
from time import sleep
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime
import time

import numpy as np


class Scan(QObject):
    finished = pyqtSignal()

    def __init__(self, parent):  # curr_coords, XX, YY, frequency, signal, scan_on_boolean_in_list):
        super(Scan, self).__init__()
        self.parent = parent
        self.isRunning = True
        self.x_array = parent.XX[0]
        self.y_array = parent.YY[0]
        self.p_start = np.array([self.x_array[0], self.y_array[0]])
        self.counts = 0
        self.extra_time = 0

    def run(self):
        print("start scan")
        if self.parent.curr_coords[0] != self.p_start[0] or self.parent.curr_coords[1] != self.p_start[1]:
            self.move_to_p_start()  # move to beginning before scan
        while self.parent.scan_on_boolean:
            self.parent.line_trace['X'].clear()
            self.parent.line_trace['ch1'].clear()
            self.parent.line_trace['ch2'].clear()
            self.parent.line_retrace['X'].clear()
            self.parent.line_retrace['ch1'].clear()
            self.parent.line_retrace['ch2'].clear()
            # self.parent.update_line_graph()
            # trace:
            for i in range(len(self.x_array)):
                if not self.parent.scan_on_boolean:
                    break
                t0 = time.time()
                self.single_time = 1 / self.parent.frequency / 2 / len(self.x_array)
                self.mod_unit = np.max([1, int(0.1 / (self.single_time + self.extra_time))])
                self.counts += 1
                self.parent.curr_coords[0] = self.x_array[i]
                self.parent.curr_coords[1] = self.y_array[i]
                # Below: self.single_time_old and 0.002 are used to ensure the sudden change of self.single_time
                # due to sudden change of self.parent.frequency does not inappropriately change the waiting time
                sleep_time = np.max([self.single_time - self.extra_time, 0.002])
                sleep(sleep_time)
                # self.parent.output_voltage_signal.emit()
                self.parent.output_voltage()
                if self.counts % self.mod_unit == 0 or i == len(self.x_array) - 1:
                    self.parent.update_graphs_signal.emit()

                ch1_ch2 = self.parent.get_voltage_ch1_ch2()

                self.parent.line_trace['X'].append(self.parent.X_raw[i])
                self.parent.line_trace['ch1'].append(ch1_ch2[0])
                self.parent.line_trace['ch2'].append(ch1_ch2[1])
                self.extra_time = time.time() - t0 - sleep_time
                # self.parent.update_line_graph()
            # retrace:
            for i in reversed(range(len(self.x_array))):
                if not self.parent.scan_on_boolean:
                    break
                t0 = time.time()
                self.single_time = 1 / self.parent.frequency / 2 / len(self.x_array)
                self.mod_unit = np.max([1, int(0.1 / (self.single_time + self.extra_time))])
                self.counts += 1
                self.parent.curr_coords[0] = self.x_array[i]
                self.parent.curr_coords[1] = self.y_array[i]
                sleep_time = np.max([self.single_time - self.extra_time, 0.002]) #0.002 just for safety (~1s for 512 px)
                sleep(sleep_time)
                # self.parent.output_voltage_signal.emit()
                self.parent.output_voltage()
                if self.counts % self.mod_unit == 0 or i == 0:
                    self.parent.update_graphs_signal.emit()
                ch1_ch2 = self.parent.get_voltage_ch1_ch2()
                self.parent.line_retrace['X'].append(self.parent.X_raw[i])
                self.parent.line_retrace['ch1'].append(ch1_ch2[0])
                self.parent.line_retrace['ch2'].append(ch1_ch2[1])
                self.extra_time = time.time() - t0 - sleep_time
                # self.parent.update_line_graph()
            print("end scan")
        self.finished.emit()

    def move_to_p_start(self):
        self.move = MoveToTarget(self.parent, self.p_start, manual_move=False)
        self.move.started.connect(self.parent.on_off_button_list_turn_off)
        self.move.finished.connect(self.move.deleteLater)
        self.move.finished.connect(lambda: self.parent.on_off_button_list_turn_on(without_pushButton_image=True))
        self.move.move()


class Map(QObject):
    finished = pyqtSignal()
    lineFinished = pyqtSignal()
    finishedAfterMapping = pyqtSignal()

    def __init__(self, parent):
        super(Map, self).__init__()
        self.parent = parent
        self.isRunning = True
        self.x_array = parent.XX[0]
        self.y_array = parent.YY[0]
        self.p_start = np.array([self.x_array[0], self.y_array[0]])
        self.counts = 0
        self.extra_time = 0
        # self.filename_prefix =
        # x = 1 + 1
        self.define_filename()

    def define_filename(self):
        now = datetime.now()
        self.filename_trace_ch1 = self.parent.lineEdit_filename_trace_ch1.text().replace("{d}", now.strftime(
            "%Y%m%d")).replace("{t}", now.strftime("%H%M%S"))
        self.filename_trace_ch2 = self.parent.lineEdit_filename_trace_ch2.text().replace("{d}", now.strftime(
            "%Y%m%d")).replace("{t}", now.strftime("%H%M%S"))
        self.filename_retrace_ch1 = self.parent.lineEdit_filename_retrace_ch1.text().replace("{d}", now.strftime(
            "%Y%m%d")).replace("{t}", now.strftime("%H%M%S"))
        self.filename_retrace_ch2 = self.parent.lineEdit_filename_retrace_ch2.text().replace("{d}", now.strftime(
            "%Y%m%d")).replace("{t}", now.strftime("%H%M%S"))
        self.directory = self.parent.lineEdit_directory.text()

    def run(self):
        print("start scan")
        self.parent.map_trace['XX'].clear()
        self.parent.map_trace['YY'].clear()
        self.parent.map_trace['ch1'].clear()
        self.parent.map_trace['ch2'].clear()
        self.parent.map_retrace['XX'].clear()
        self.parent.map_retrace['YY'].clear()
        self.parent.map_retrace['ch1'].clear()
        self.parent.map_retrace['ch2'].clear()
        if self.parent.curr_coords[0] != self.p_start[0] or self.parent.curr_coords[1] != self.p_start[1]:
            self.move_to_p_start()
        row_num = 0
        while self.parent.map_on_boolean and row_num < self.parent.XX.shape[0]:
            self.x_array = self.parent.XX[row_num]
            self.y_array = self.parent.YY[row_num]
            self.parent.line_trace['X'].clear()
            self.parent.line_trace['ch1'].clear()
            self.parent.line_trace['ch2'].clear()
            self.parent.line_retrace['X'].clear()
            self.parent.line_retrace['ch1'].clear()
            self.parent.line_retrace['ch2'].clear()
            # trace:
            for i in range(len(self.x_array)):
                if not self.parent.map_on_boolean:
                    break
                t0 = time.time()
                self.single_time = 1 / self.parent.frequency / 2 / len(self.x_array)
                self.mod_unit = np.max([1, int(0.1 / (self.single_time + self.extra_time))])
                self.counts += 1
                self.parent.curr_coords[0] = self.x_array[i]
                self.parent.curr_coords[1] = self.y_array[i]
                sleep_time = np.max([self.single_time - self.extra_time, 0.002])
                sleep(sleep_time)
                # self.parent.output_voltage_signal.emit()
                self.parent.output_voltage()
                if self.counts % self.mod_unit == 0 or i == len(self.x_array) - 1:
                    self.parent.update_graphs_signal.emit()
                ch1_ch2 = self.parent.get_voltage_ch1_ch2()
                self.parent.line_trace['X'].append(self.parent.X_raw[i])
                self.parent.line_trace['ch1'].append(ch1_ch2[0])
                self.parent.line_trace['ch2'].append(ch1_ch2[1])
                self.extra_time = time.time() - t0 - sleep_time
            # list() converts array to list, also copying the data rather than using reference
            if self.parent.map_on_boolean:
                self.parent.map_trace['XX'].append(list(self.parent.XX[row_num]))
                self.parent.map_trace['YY'].append(list(self.parent.YY[row_num]))
                self.parent.map_trace['ch1'].append(self.parent.line_trace['ch1'].copy())
                self.parent.map_trace['ch2'].append(self.parent.line_trace['ch2'].copy())
                self.lineFinished.emit()

                self.parent.thread1 = QThread() # thread1 is assigned to self.parent to avoid abrupt killing of the saving thread while it's running
                self.save1 = SaveTiffFile(self.parent.map_trace['ch1'], self.parent.X_raw[-1], self.parent.Y_raw[len(self.parent.map_trace['ch1']) - 1],
                                          self.filename_trace_ch1, self.directory)
                self.save1.moveToThread(self.parent.thread1)
                self.parent.thread1.started.connect(self.save1.save)
                self.save1.finished.connect(self.save1.deleteLater)
                self.save1.finished.connect(self.parent.thread1.exit)
                self.parent.thread1.finished.connect(self.parent.thread1.deleteLater)

                self.parent.thread1.start()

                self.parent.thread2 = QThread()
                self.save2 = SaveTiffFile(self.parent.map_trace['ch2'], self.parent.X_raw[-1], self.parent.Y_raw[len(self.parent.map_trace['ch2']) - 1],
                                          self.filename_trace_ch2, self.directory)
                self.save2.moveToThread(self.parent.thread2)
                self.save2.finished.connect(self.parent.thread2.exit)
                self.save2.finished.connect(self.save2.deleteLater)
                self.parent.thread2.finished.connect(self.parent.thread2.deleteLater)
                self.parent.thread2.started.connect(self.save2.save)
                self.parent.thread2.start()

            # retrace:
            for i in reversed(range(len(self.x_array))):
                if not self.parent.map_on_boolean:
                    break
                t0 = time.time()
                self.single_time = 1 / self.parent.frequency / 2 / len(self.x_array)
                self.mod_unit = np.max([1, int(0.1 / (self.single_time + self.extra_time))])
                self.counts += 1
                self.parent.curr_coords[0] = self.x_array[i]
                self.parent.curr_coords[1] = self.y_array[i]
                sleep_time = np.max([self.single_time - self.extra_time, 0.002])
                sleep(sleep_time)
                # self.parent.output_voltage_signal.emit()
                self.parent.output_voltage()
                if self.counts % self.mod_unit == 0 or i == 0:
                    self.parent.update_graphs_signal.emit()
                ch1_ch2 = self.parent.get_voltage_ch1_ch2()
                self.parent.line_retrace['X'].append(self.parent.X_raw[i])
                self.parent.line_retrace['ch1'].append(ch1_ch2[0])
                self.parent.line_retrace['ch2'].append(ch1_ch2[1])
                self.extra_time = time.time() - t0 - sleep_time
            if self.parent.map_on_boolean:
                self.parent.map_retrace['XX'].append(list(self.parent.XX[row_num]))
                self.parent.map_retrace['YY'].append(list(self.parent.YY[row_num]))
                self.parent.map_retrace['ch1'].append(self.parent.line_retrace['ch1'][::-1])#.copy())
                self.parent.map_retrace['ch2'].append(self.parent.line_retrace['ch2'][::-1])#.copy())
                self.lineFinished.emit()

                self.parent.thread3 = QThread()
                self.save3 = SaveTiffFile(self.parent.map_retrace['ch1'], self.parent.X_raw[-1], self.parent.Y_raw[len(self.parent.map_retrace['ch1']) - 1],
                                          self.filename_retrace_ch1, self.directory)
                self.save3.moveToThread(self.parent.thread3)
                self.save3.finished.connect(self.parent.thread3.exit)
                self.save3.finished.connect(self.save3.deleteLater)
                self.parent.thread3.finished.connect(self.parent.thread3.deleteLater)
                self.parent.thread3.started.connect(self.save3.save)
                self.parent.thread3.start()

                self.parent.thread4 = QThread()
                self.save4 = SaveTiffFile(self.parent.map_retrace['ch2'], self.parent.X_raw[-1], self.parent.Y_raw[len(self.parent.map_retrace['ch2']) - 1],
                                          self.filename_retrace_ch2, self.directory)
                self.save4.moveToThread(self.parent.thread4)
                self.save4.finished.connect(self.parent.thread4.exit)
                self.save4.finished.connect(self.save4.deleteLater)
                self.parent.thread4.finished.connect(self.parent.thread4.deleteLater)
                self.parent.thread4.started.connect(self.save4.save)
                self.parent.thread4.start()
            row_num += 1
            print("end scan")
        if self.parent.map_on_boolean:
            self.finishedAfterMapping.emit()
        self.finished.emit()

    def move_to_p_start(self):
        self.move = MoveToTarget(self.parent, self.p_start, manual_move=False)
        self.move.started.connect(self.parent.on_off_button_list_turn_off)
        self.move.finished.connect(self.move.deleteLater)
        self.move.finished.connect(lambda: self.parent.on_off_button_list_turn_on(without_pushButton_scan=True))
        self.move.move()


class ApproachDisplay(QObject):
    finished = pyqtSignal()
    def __init__(self, parent):
        super(ApproachDisplay, self).__init__()
        self.max_count = 600
        self.parent = parent
    def run(self):
        while self.parent.display_approach_on:
            sleep(0.1)
            ch1, ch2 = self.parent.get_voltage_ch1_ch2()
            # print(ch1, ch2)
            if len(self.parent.display_list_ch1) == self.max_count:
                self.parent.display_list_ch1.pop(0)
                self.parent.display_list_ch2.pop(0)
            self.parent.display_list_ch1.append(ch1)
            self.parent.display_list_ch2.append(ch2)
            self.parent.update_display_approach_signal.emit()
        self.finished.emit()

def distance(p_A, p_B):
    return np.sqrt((p_A[0] - p_B[0]) ** 2 + (p_A[1] - p_B[1]) ** 2)


class MoveToTarget(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, parent, target, manual_move=False):
        super(MoveToTarget, self).__init__()
        self.parent = parent
        self.target = target
        self.manual_move = manual_move
        self.counts = 0

    def move(self):
        print("start move-to-target")
        self.started.emit()
        ratio = distance(self.parent.curr_coords, self.target) / \
                distance(np.array([self.parent.XX[0][0], self.parent.YY[0][0]]),
                         np.array([self.parent.XX[0][-1], self.parent.YY[0][-1]]))

        # for w in self.parent.on_off_button_list:
        #     w.setDisabled(True)

        steps = np.max([int(len(self.parent.XX[0]) * ratio), 1])
        x_array = np.round(np.linspace(self.parent.curr_coords[0], self.target[0], steps), 6)
        y_array = np.round(np.linspace(self.parent.curr_coords[1], self.target[1], steps), 6)
        for i in range(len(x_array)):
            # TODO: if halted, stop for loop
            if (not self.manual_move) and (not self.parent.scan_on_boolean) and (not self.parent.map_on_boolean):
                break
            total_time = 1 / self.parent.frequency / 2 * ratio
            single_time = total_time / steps
            self.parent.curr_coords[0] = x_array[i]
            self.parent.curr_coords[1] = y_array[i]
            sleep(single_time)
            self.single_time = 1 / self.parent.frequency / 2 / len(x_array)
            self.mod_unit = np.max([1, int(0.1 / self.single_time)])
            # self.parent.output_voltage_signal.emit()
            self.parent.output_voltage()
            if self.counts % self.mod_unit == 0:
                self.parent.update_graphs_signal.emit()
            self.counts += 1
        print("end move-to-target")
        # for w in self.parent.on_off_button_list:
        #     w.setDisabled(False)
        self.finished.emit()


class MoveToTargetZ(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    def __init__(self, parent, target, auto_approach = False, parent_finished_signal = None,
                 parent_finishedAfterApproach_signal = None):
        super(MoveToTargetZ, self).__init__()
        self.target = target
        self.parent = parent
        self.auto_approach = auto_approach
        self.parent_finished_signal = parent_finished_signal
        self.parent_finishedAfterApproach_signal = parent_finishedAfterApproach_signal
        self.delta = 0.1 if self.target >= self.parent.curr_coord_z else -0.1
        self.array = np.round(np.arange(self.parent.curr_coord_z, self.target + self.delta, self.delta), 6)
    def move(self):
        self.started.emit()
        for val in self.array:
            if self.auto_approach and not self.parent.auto_approach_on_boolean:
                break
            # print(val)
            self.parent.curr_coord_z = val
            self.parent.doubleSpinBox_z.setValue(self.parent.curr_coord_z)
            self.parent.output_voltage_z_direction()
            time.sleep(0.05)
        if self.parent_finished_signal is not None:
            self.parent_finished_signal.emit()
        if self.parent_finished_signal is not None and self.parent.auto_approach_on_boolean:
            self.parent_finishedAfterApproach_signal.emit()
        self.finished.emit()


class AutoApproach(QObject):
    finished = pyqtSignal()
    finishedAfterApproach = pyqtSignal()
    def __init__(self, parent):
        super(AutoApproach, self).__init__()
        self.parent = parent

    def move(self):
        # print("auto start")
        self.parent.goto_position_z(
            self.parent.doubleSpinBox_scanner_voltage_per_turn.value(),
            auto_approach = True, parent_finished_signal = self.finished,
            parent_finishedAfterApproach_signal = self.finishedAfterApproach)


class SaveTiffFile(QObject):
    finished = pyqtSignal()
    def __init__(self, data, xmax, ymax, filename, directory):
        super(SaveTiffFile, self).__init__()
        self.data = np.asanyarray(data)
        self.filename = filename
        self.directory = directory
        self.xmax = xmax
        self.ymax = ymax

    def save(self):
        SaveParkTiff(data=self.data, X_scan_size=self.xmax, Y_scan_size=self.ymax,
                     file_path=self.directory + '/' + self.filename + ".tiff")
        np.savetxt(self.directory + '/' + self.filename + ".txt", self.data)
        self.finished.emit()
        print('save done')


