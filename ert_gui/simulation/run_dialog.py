from ert_gui.model.real_list import RealListModel
from ert_gui.model.job_list import JobListProxyModel
from ert_gui.model.node import NodeType
from ert_gui.model.snapshot import SnapshotModel
from ert_shared.ensemble_evaluator.entity.snapshot import PartialSnapshot, Snapshot
from ert_gui.simulation.tracker_worker import TrackerWorker
from ert_shared.status.entity.state import REAL_STATE_TO_COLOR
import time
from threading import Thread

from qtpy.QtCore import Qt, QTimer, QSize, Signal, Slot, QThread, QModelIndex
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget, QTreeView, QTableView, QListView

from ecl.util.util import BoolVector
from ert_gui.ertwidgets import Legend, resourceMovie
from ert_gui.simulation import DetailedProgressWidget, Progress, SimpleProgress
from ert_gui.tools.plot.plot_tool import PlotTool
from ert_shared.models import BaseRunModel
from ert_shared.status.entity.event import FullSnapshotEvent, EndEvent, SnapshotUpdateEvent
from ert_shared.status.tracker.factory import create_tracker
from ert_shared.status.utils import format_running_time
from res.job_queue import JobStatusType


class RunDialog(QDialog):
    simulation_done = Signal(bool, str)

    def __init__(self, config_file, run_model, simulation_arguments, storage_client, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowFlags(Qt.Window)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle("Simulations - {}".format(config_file))
        self._snapshot_model = SnapshotModel(self)
        assert isinstance(run_model, BaseRunModel)
        self._run_model = run_model

        ert = None
        if isinstance(run_model, BaseRunModel):
            ert = run_model.ert()

        self._simulations_argments = simulation_arguments
        self._storage_client = storage_client

        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._on_ticker)

        # states = self.simulations_tracker.get_states()
        # self.state_colors = {state.name: state.color for state in states}
        # self.state_colors['Success'] = self.state_colors["Finished"]
        # self.state_colors['Failure'] = self.state_colors["Failed"]

        self.total_progress = SimpleProgress()

        status_layout = QHBoxLayout()
        status_layout.addStretch()
        self.__status_label = QLabel()
        status_layout.addWidget(self.__status_label)
        status_layout.addStretch()
        status_widget_container = QWidget()
        status_widget_container.setLayout(status_layout)

        self.progress = Progress()

        legend_layout = QHBoxLayout()
        self.legends = {}
        for state, color in REAL_STATE_TO_COLOR.items():
            self.legends[state] = Legend("%s (%d/%d)", QColor(*color))
            self.legends[state].updateLegend(state, 0, 0)
            legend_layout.addWidget(self.legends[state])

        legend_widget_container = QWidget()
        legend_widget_container.setLayout(legend_layout)

        self.running_time = QLabel("")

        self.plot_tool = PlotTool(config_file, self._storage_client)
        self.plot_tool.setParent(self)
        self.plot_button = QPushButton(self.plot_tool.getName())
        self.plot_button.clicked.connect(self.plot_tool.trigger)
        self.plot_button.setEnabled(ert is not None)

        self.kill_button = QPushButton("Kill simulations")
        self.done_button = QPushButton("Done")
        self.done_button.setHidden(True)
        self.restart_button = QPushButton("Restart")
        self.restart_button.setHidden(True)
        self.show_details_button = QPushButton("Details")
        self.show_details_button.setCheckable(True)

        size = 20
        spin_movie = resourceMovie("ide/loading.gif")
        spin_movie.setSpeed(60)
        spin_movie.setScaledSize(QSize(size, size))
        spin_movie.start()

        self.processing_animation = QLabel()
        self.processing_animation.setMaximumSize(QSize(size, size))
        self.processing_animation.setMinimumSize(QSize(size, size))
        self.processing_animation.setMovie(spin_movie)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.processing_animation)
        button_layout.addWidget(self.running_time)
        button_layout.addStretch()
        button_layout.addWidget(self.show_details_button)
        button_layout.addWidget(self.plot_button)
        button_layout.addWidget(self.kill_button)
        button_layout.addWidget(self.done_button)
        button_layout.addWidget(self.restart_button)
        button_widget_container = QWidget()
        button_widget_container.setLayout(button_layout)

        self.detailed_progress = DetailedProgressWidget(self)
        self.detailed_progress.setVisible(False)
        self.dummy_widget_container = QWidget() #Used to keep the other widgets from stretching

        layout = QVBoxLayout()
        layout.addWidget(self.total_progress)
        layout.addWidget(status_widget_container)
        layout.addWidget(self.progress)
        layout.addWidget(legend_widget_container)
        layout.addWidget(self.detailed_progress)
        layout.addWidget(self.dummy_widget_container)
        layout.addWidget(button_widget_container)

        snapshot_tree = QTreeView(self)
        snapshot_tree.setModel(self._snapshot_model)
        snapshot_tree.clicked.connect(self._select_iter)

        layout.addWidget(snapshot_tree)

        real_model = RealListModel(self, 0)
        real_model.setSourceModel(self._snapshot_model)

        self._real_list = QListView(self)
        self._real_list.setViewMode(QListView.IconMode)
        self._real_list.setGridSize(QSize(120, 20))
        self._real_list.setModel(real_model)
        self._real_list.setVisible(False)
        self._real_list.clicked.connect(self._select_real)
        layout.addWidget(self._real_list)

        job_model = JobListProxyModel(self, 0, 0, 0, 0)
        job_model.setSourceModel(self._snapshot_model)

        self._job_list = QTableView(self)
        self._job_list.setModel(job_model)
        layout.addWidget(self._job_list)

        layout.setStretch(0, 0)
        layout.setStretch(1, 0)
        layout.setStretch(2, 0)
        layout.setStretch(3, 0)
        layout.setStretch(4, 1)
        layout.setStretch(5, 1)
        layout.setStretch(6, 0)

        self.setLayout(layout)

        self.kill_button.clicked.connect(self.killJobs)
        self.done_button.clicked.connect(self.accept)
        self.restart_button.clicked.connect(self.restart_failed_realizations)
        self.show_details_button.clicked.connect(self.toggle_detailed_progress)
        self.simulation_done.connect(self._on_simulation_done)

    @Slot(QModelIndex)
    def _select_iter(self, index):
        node = index.internalPointer()
        if node is None or node.type != NodeType.ITER:
            return
        iter_ = node.row()
        print("select iter: ", iter_)

        self._real_list.model().setIter(iter_)
        self._real_list.setVisible(True)

    @Slot(QModelIndex)
    def _select_real(self, index):
        node = index.internalPointer()
        if node is None or node.type != NodeType.REAL:
            return
        step = 0
        stage = 0
        real = node.row()
        iter_ = node.parent.row()
        print("select real", step, stage, real, iter_)

        # create a proxy model
        # TODO: change values on proxymodel such that it does not need creation
        proxy = JobListProxyModel(self, iter_, real, stage, step)
        proxy.setSourceModel(self._snapshot_model)
        self._job_list.setModel(proxy)

    def reject(self):
        return

    def closeEvent(self, QCloseEvent):
        if self._run_model.isFinished():
            self.simulation_done.emit(self._run_model.hasRunFailed(),
                                      self._run_model.getFailMessage())
        else:
            # Kill jobs if dialog is closed
            if self.killJobs() != QMessageBox.Yes:
                QCloseEvent.ignore()

    def startSimulation(self):
        self._run_model.reset()

        def run():
            self._run_model.startSimulations( self._simulations_argments )

        simulation_thread = Thread(name="ert_gui_simulation_thread")
        simulation_thread.setDaemon(True)
        simulation_thread.run = run
        simulation_thread.start()

        self._ticker.start(1000)

        tracker = create_tracker(
            self._run_model,
            num_realizations=self._simulations_argments["active_realizations"].count()
        )
        worker = TrackerWorker(tracker)
        worker_thread = QThread()
        worker.done.connect(worker_thread.quit)
        worker.consumed_event.connect(self._on_tracker_event)
        worker.moveToThread(worker_thread)
        self.simulation_done.connect(worker.stop)
        self._worker = worker
        self._worker_thread = worker_thread
        worker_thread.started.connect(worker.consume_and_emit)
        self._worker_thread.start()

    def killJobs(self):

        msg =  "Are you sure you want to kill the currently running simulations?"
        if self._run_model.getQueueStatus().get(JobStatusType.JOB_QUEUE_UNKNOWN, 0) > 0:
            msg += "\n\nKilling a simulation with unknown status will not kill the realizations already submitted!"
        kill_job = QMessageBox.question(self, "Kill simulations?",msg, QMessageBox.Yes | QMessageBox.No )

        if kill_job == QMessageBox.Yes:
            # Normally this slot would be invoked by the signal/slot system,
            # but the worker is busy tracking the evaluation.
            self._worker.request_termination()
            self.reject()
        return kill_job

    @Slot(bool, str)
    def _on_simulation_done(self, failed, failed_msg):
        self.processing_animation.hide()
        self.kill_button.setHidden(True)
        self.done_button.setHidden(False)
        self.restart_button.setVisible(self.has_failed_realizations())
        self.restart_button.setEnabled(self._run_model.support_restart)

        if failed:
            QMessageBox.critical(self, "Simulations failed!",
                                 "The simulation failed with the following " +
                                 "error:\n\n{}".format(failed_msg))

    @Slot()
    def _on_ticker(self):
        runtime = self._run_model.get_runtime()
        self.running_time.setText(format_running_time(runtime))
        if runtime % 5 == 0:
            self.total_progress.update()
            self.progress.update()
            # self.legends.handle(event)
        if runtime % 10 == 0:
            self.detailed_progress.update()

    @Slot(object)
    def _on_tracker_event(self, event):
        print("got tracker event", type(event))

        if isinstance(event, EndEvent):
            self.simulation_done.emit(event.failed, event.failed_msg)
            self._worker.stop()
            self._ticker.stop()
        elif isinstance(event, FullSnapshotEvent):
            if event.snapshot is not None:
                self._snapshot_model._add_snapshot(event.snapshot, event.iteration)
        elif isinstance(event, SnapshotUpdateEvent):
            if event.partial_snapshot is not None:
                self._snapshot_model._add_partial_snapshot(event.partial_snapshot, event.iteration)
            # self.total_progress.handle(event)
            # self.progress.handle(event)
            # self.detailed_progress.handle(event)
            # self.legends.handle(event)
        # if isinstance(event, GeneralEvent):
        #     self.total_progress.setProgress(event.progress)
        #     self.progress.setIndeterminate(event.indeterminate)

        #     if event.indeterminate:
        #         for state in event.sim_states:
        #             self.legends[state].updateLegend(state.name, 0, 0)
        #     else:
        #         for state in event.sim_states:
        #             try:
        #                 self.progress.updateState(
        #                     state.state, 100.0 * state.count / state.total_count)
        #             except ZeroDivisionError:
        #                 # total_count not set by some slow tracker (EE)
        #                 pass
        #             self.legends[state].updateLegend(
        #                 state.name, state.count, state.total_count)

        # if isinstance(event, DetailedEvent):
        #     if not self.progress.get_indeterminate():
        #         self.detailed_progress.set_progress(event.details,
        #                                             event.iteration)

        # if isinstance(event, EndEvent):
        #     self.simulation_done.emit(event.failed, event.failed_msg)

    def has_failed_realizations(self):
        completed = self._run_model.completed_realizations_mask
        initial = self._run_model.initial_realizations_mask
        for (index, successful) in enumerate(completed):
            if initial[index] and not successful:
                return True
        return False


    def count_successful_realizations(self):
        """
        Counts the realizations completed in the prevoius ensemble run
        :return:
        """
        completed = self._run_model.completed_realizations_mask
        return completed.count(True)

    def create_mask_from_failed_realizations(self):
        """
        Creates a BoolVector mask representing the failed realizations
        :return: Type BoolVector
        """
        completed = self._run_model.completed_realizations_mask
        initial = self._run_model.initial_realizations_mask
        inverted_mask = BoolVector(  default_value = False )
        for (index, successful) in enumerate(completed):
            inverted_mask[index] = initial[index] and not successful
        return inverted_mask


    def restart_failed_realizations(self):

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setText("Note that workflows will only be executed on the restarted realizations and that this might have unexpected consequences.")
        msg.setWindowTitle("Restart Failed Realizations")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msg.exec_()

        if result == QMessageBox.Ok:
            self.restart_button.setVisible(False)
            self.kill_button.setVisible(True)
            self.done_button.setVisible(False)
            active_realizations = self.create_mask_from_failed_realizations()
            self._simulations_argments['active_realizations'] = active_realizations
            self._simulations_argments['prev_successful_realizations'] = self._simulations_argments.get('prev_successful_realizations', 0)
            self._simulations_argments['prev_successful_realizations'] += self.count_successful_realizations()
            self.startSimulation()



    def toggle_detailed_progress(self):

        self.detailed_progress.setVisible(not(self.detailed_progress.isVisible()))
        self.dummy_widget_container.setVisible(not(self.detailed_progress.isVisible()))
        self.adjustSize()
