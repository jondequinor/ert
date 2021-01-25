import logging
import queue
import threading
import time

import ert_shared.ensemble_evaluator.entity.identifiers as ids
from ert_shared.ensemble_evaluator.entity.snapshot import PartialSnapshot
from ert_shared.ensemble_evaluator.monitor import create as create_ee_monitor
from ert_shared.ensemble_evaluator.ws_util import wait_for_ws
from ert_shared.status.entity.event import (
    EndEvent,
    FullSnapshotEvent,
    SnapshotUpdateEvent,
)


class EvaluatorTracker:
    def __init__(
        self,
        model,
        host,
        port,
        general_interval,
        detailed_interval,
    ):
        self._model = model

        self._monitor_host = host
        self._monitor_port = port

        self._work_queue = queue.Queue()

        self._drainer_thread = threading.Thread(target=self._drain_monitor)
        self._drainer_thread.start()

    def _drain_monitor(self):
        drainer_logger = logging.getLogger("ert_shared.ensemble_evaluator.drainer")
        monitor = create_ee_monitor(self._monitor_host, self._monitor_port)
        while monitor:
            try:
                for event in monitor.track():
                    if event["type"] in (
                        ids.EVTYPE_EE_SNAPSHOT,
                        ids.EVTYPE_EE_SNAPSHOT_UPDATE,
                    ):
                        self._work_queue.put(event)
                        if event.data.get("status") == "Stopped":
                            drainer_logger.debug(
                                "observed evaluation stopped event, signal done"
                            )
                            monitor.signal_done()
                    elif event["type"] == ids.EVTYPE_EE_TERMINATED:
                        drainer_logger.debug("got terminator event")
                        self._work_queue.put(event)
                        while True:
                            if self._model.isFinished():
                                drainer_logger.debug(
                                    "observed that model was finished, waiting tasks completion..."
                                )
                                self._work_queue.join()
                                drainer_logger.debug("tasks complete")
                                return
                            try:
                                time.sleep(5)
                                drainer_logger.debug("connecting to new monitor...")
                                monitor = create_ee_monitor(
                                    self._monitor_host, self._monitor_port
                                )
                                wait_for_ws(monitor.get_base_uri(), max_retries=2)
                                drainer_logger.debug("connected")
                                break
                            except ConnectionRefusedError as e:
                                drainer_logger.debug(f"connection refused: {e}")
                                pass

            except ConnectionRefusedError:
                if self._model.isFinished():
                    return
                else:
                    raise

    def track(self):
        while True:
            event = self._work_queue.get()
            current_phase = self._model.currentPhase()
            phase_count = self._model.phaseCount()
            if event["type"] == ids.EVTYPE_EE_SNAPSHOT:
                iter_ = event.data["iter"]
                yield FullSnapshotEvent(
                    phase_name=self._model.getPhaseName(),
                    current_phase=self._model.currentPhase(),
                    total_phases=self._model.phaseCount(),
                    indeterminate=self._model.isIndeterminate(),
                    progress=current_phase / phase_count,
                    iteration=iter_,
                    snapshot=event.data,
                )
            elif event["type"] == ids.EVTYPE_EE_SNAPSHOT_UPDATE:
                iter_ = event.data["iter"]
                yield SnapshotUpdateEvent(
                    phase_name=self._model.getPhaseName(),
                    current_phase=self._model.currentPhase(),
                    total_phases=self._model.phaseCount(),
                    indeterminate=self._model.isIndeterminate(),
                    progress=current_phase / phase_count,
                    iteration=iter_,
                    partial_snapshot=PartialSnapshot.from_dict(event.data),
                )
            elif event["type"] == ids.EVTYPE_EE_TERMINATED:
                try:
                    yield EndEvent(
                        failed=self._model.hasRunFailed(),
                        failed_msg=self._model.getFailMessage(),
                    )
                except GeneratorExit:
                    # consumers will exit at this point, make sure the last
                    # task is marked as done
                    pass
            self._work_queue.task_done()

    def is_finished(self):
        return not self._drainer_thread.is_alive()

    def reset(self):
        pass

    def _clear_work_queue(self):
        try:
            while True:
                self._work_queue.get_nowait()
                self._work_queue.task_done()
        except queue.Empty:
            pass

    def request_termination(self):
        monitor = create_ee_monitor(self._monitor_host, self._monitor_port)
        monitor.signal_cancel()

        while self._drainer_thread.is_alive():
            self._clear_work_queue()
            time.sleep(1)
