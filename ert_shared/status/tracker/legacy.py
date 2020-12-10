"""Track legacy evaluations that does not use the Ensemble Evaluator.
Tracking is cross-iteration, which means there's complexity pertaining to job
queues and run_context being created, and the abandoned by the experiment.

A FullSnapshotEvent will be emitted at the beginning of each iteration. Within
the life-span of an iteration, zero or more SnapshotUpdateEvent will be
emitted. A final EndEvent is emitted when the experiment is over.
"""

from res.job_queue.job_status_type_enum import JobStatusType
from typing_extensions import final
from ert_shared.models.base_run_model import BaseRunModel
import typing

from res.enkf.ert_run_context import ErtRunContext
from ert_shared.status.queue_diff import QueueDiff
from ert_shared.ensemble_evaluator.entity.snapshot import (
    PartialSnapshot,
    SnapshotBuilder,
    SnapshotDict,
    _ForwardModel,
    _Job,
    _Realization,
    _Stage,
    _Step,
)
import time
from ert_shared.status.entity.event import (
    EndEvent,
    FullSnapshotEvent,
    SnapshotUpdateEvent,
)
from ert_shared.status.entity.state import queue_status_to_real_state
import logging

logger = logging.getLogger(__name__)


class LegacyTracker:
    def __init__(
        self,
        model: BaseRunModel,
        general_interval: int,
        detailed_interval: int,
    ) -> None:
        self._model = model

        # self._states = create_states()

        # map of iter to whether or not a queue has run, represented by a bool
        self._iter_to_queue = {}
        # self._general_interval = general_interval
        # self._detailed_interval = detailed_interval
        self._general_interval = 3
        self._detailed_interval = 5

    def track(self) -> None:
        print("starting legacy track")
        tick = 0
        current_iter = -1
        while not self.is_finished():
            time.sleep(1)
            run_context = self._model.get_run_context()

            if run_context is None:
                logger.debug("no run_context, sleeping")
                continue

            iter_ = _get_run_context_iter(run_context)
            if current_iter != iter_:
                full_snapshot_event = self._full_snapshot_event()
                if full_snapshot_event is None:
                    logger.debug(
                        f"no full_snapshot_event on new iter {iter_} (current {current_iter}), sleeping"
                    )
                    continue
                yield full_snapshot_event
                current_iter = iter_

            self._update_iter_to_queue(iter_)
            if tick % self._general_interval == 0:
                yield self._partial_snapshot()
            elif tick % self._detailed_interval == 0:
                yield self._partial_snapshot(read_from_disk=True)
            tick += 1

        # Simulation done, emit final updates
        final_snapshot = self._full_snapshot_event()
        if final_snapshot:
            yield final_snapshot
        yield self._end_event()

    def _create_full_snapshot(
        self, run_context: ErtRunContext, detailed_progress: typing.Dict
    ) -> typing.Optional[SnapshotDict]:
        """create a snapshot of a run_context and detailed_progress.
        detailed_progress is expected to be a tuple of a realization_progress
        dict and iteration number."""
        run_context_iter = _get_run_context_iter(run_context)
        self._update_iter_to_queue(run_context_iter)

        snapshot = SnapshotDict(
            status="Unknown",
            reals={},
            metadata={},
            forward_model=_ForwardModel(step_definitions={}),
        )
        snapshot.metadata["iter"] = run_context_iter

        forward_model = self._model.get_forward_model()

        real_prog, iter_ = detailed_progress

        enumerated = 0
        for iens, run_arg in _enumerate_from_volatile(run_context):
            real_id = str(iens)
            enumerated += 1
            if not _is_iens_active(iens, run_context):
                continue

            status = JobStatusType.JOB_QUEUE_UNKNOWN
            try:
                # will throw if not yet submitted (is in a limbo state)
                queue_index = run_arg.getQueueIndex()
                if self._model._job_queue:
                    status = self._model._job_queue.getJobStatus(queue_index)
            except ValueError:
                logger.debug(f"iens {iens} was in a limbo state")

            snapshot.reals[real_id] = _Realization(
                status=queue_status_to_real_state(status), active=True, stages={}
            )

            step = _Step(status="", jobs={})
            snapshot.reals[real_id].stages["0"] = _Stage(status="", steps={"0": step})

            for index in range(0, len(forward_model)):
                ext_job = forward_model.iget_job(index)
                step.jobs[str(index)] = _Job(
                    name=ext_job.name(), status="Unknown", data={}
                )

            if iter_ != run_context_iter:
                logger.debug(
                    f"run_context iter ({run_context_iter}) and detailed_progress ({iter_} iter differed"
                )
                return snapshot

            progress = real_prog[iter_].get(iens, None)
            if not progress:
                continue

            jobs = progress[0]
            for idx, fm in enumerate(jobs):
                job = step.jobs[str(idx)]

                # FIXME: parse these as iso date
                job.start_time = str(fm.start_time)
                job.end_time = str(fm.end_time)
                job.name = fm.name
                job.status = fm.status
                job.error = fm.error
                job.stdout = fm.std_out_file
                job.stderr = fm.std_err_file
                job.data = {
                    "current_memory_usage": fm.current_memory_usage,
                    "max_memory_usage": fm.max_memory_usage,
                }

        if enumerated == 0:
            logger.debug("enumerated 0 members from run_context, assume it went away")
            return None

        return snapshot

    def _update_iter_to_queue(self, iter_: int) -> None:
        if iter_ < 0:
            return
        if iter_ not in self._iter_to_queue:
            self._iter_to_queue[iter_] = None

        if self._iter_to_queue[iter_] is None and self._model._job_queue is not None:
            self._iter_to_queue[iter_] = QueueDiff(self._model._job_queue)

    def _get_queue_from_iter(self, iter_: int) -> typing.Optional[QueueDiff]:
        if iter_ not in self._iter_to_queue:
            return None
        return self._iter_to_queue[iter_]

    def _create_partial_snapshot(
        self,
        run_context: ErtRunContext,
        detailed_progress: typing.Tuple[typing.Dict, int],
    ) -> typing.Optional[PartialSnapshot]:
        """Create a PartialSnapshot, or None if the sources of data were
        destroyed or had not been created yet."""
        run_context_iter = _get_run_context_iter(run_context)
        differ = self._get_queue_from_iter(run_context_iter)
        if differ is None:
            return None
        if not differ.queue().is_active():
            return None
        changes = differ.changes_after_transition()
        partial = PartialSnapshot()
        for iens, change in changes.items():
            change_enum = JobStatusType.from_string(change)
            partial.update_real(
                str(iens), status=queue_status_to_real_state(change_enum)
            )

        detailed_progress, iter_ = detailed_progress
        if not detailed_progress:
            logger.debug(f"partial: no detailed progress for iter:{iter_}")
            return partial
        if iter_ != run_context_iter:
            logger.debug(
                f"partial: detailed_progress iter ({iter_}) differed from run_context_iter ({run_context_iter})"
            )

        for iens, run_arg in _enumerate_from_volatile(run_context):
            real_id = str(iens)
            if not _is_iens_active(iens, run_context):
                continue

            progress = detailed_progress[iter_].get(iens, None)
            if not progress:
                continue

            jobs = progress[0]
            for idx, fm in enumerate(jobs):
                partial.update_job(
                    real_id,
                    "0",
                    "0",
                    str(idx),
                    status=fm.status,
                    start_time=str(fm.start_time),
                    end_time=str(fm.end_time),
                    data={
                        "current_memory_usage": fm.current_memory_usage,
                        "max_memory_usage": fm.max_memory_usage,
                    },
                )

        return partial

    def _partial_snapshot(self, read_from_disk=False) -> SnapshotUpdateEvent:
        """Return a SnapshotUpdateEvent. If read_from_disk is set, this method
        will ultimately read status.json files from disk in order to create an
        event."""
        run_context = self._model.get_run_context()
        iter_ = _get_run_context_iter(run_context)
        detailed_progress = (
            self._model.getDetailedProgress() if read_from_disk else (None, -1)
        )
        return SnapshotUpdateEvent(
            phase_name=self._model.getPhaseName(),
            current_phase=self._model.currentPhase(),
            total_phases=self._model.phaseCount(),
            indeterminate=self._model.isIndeterminate(),
            progress=0.0,
            iteration=iter_,
            partial_snapshot=self._create_partial_snapshot(
                run_context, detailed_progress
            ),
        )

    def _full_snapshot_event(self) -> typing.Optional[FullSnapshotEvent]:
        """Return a FullSnapshotEvent if it was possible to create a snapshot.
        Return None if not, indicating that there should be no event."""
        run_context = self._model.get_run_context()
        iter_ = _get_run_context_iter(run_context)
        detailed_progress = self._model.getDetailedProgress()
        if len(detailed_progress[0]) == 0:
            return None
        full_snapshot = self._create_full_snapshot(run_context, detailed_progress)
        if not full_snapshot:
            return None
        return FullSnapshotEvent(
            phase_name=self._model.getPhaseName(),
            current_phase=self._model.currentPhase(),
            total_phases=self._model.phaseCount(),
            indeterminate=self._model.isIndeterminate(),
            progress=0.0,
            iteration=iter_,
            snapshot=full_snapshot,
        )

    def _end_event(self) -> EndEvent:
        return EndEvent(
            failed=self._model.hasRunFailed(), failed_msg=self._model.getFailMessage()
        )

    def is_finished(self) -> bool:
        return self._model.isFinished()

    def request_termination(self) -> None:
        return self._model.killAllSimulations()

    def reset(self):
        self._iter_to_queue = {}


def _get_run_context_iter(run_context: ErtRunContext) -> int:
    """Return the iter from run_context, defensively and by avoiding TOCTOU
    issues."""
    try:
        return run_context.get_iter()
    except AttributeError:
        return -1


def _is_iens_active(iens: int, run_context: ErtRunContext) -> bool:
    """Return whether or not the iens is active, defensively and by avoiding
    potential TOCTOU issues."""
    try:
        return run_context.is_active(iens)
    except AttributeError:
        return False


def _enumerate_from_volatile(run_context: ErtRunContext) -> typing.Iterable:
    """Return an iterable that's either (iens, run_arg) or empty, attempting to
    do this defensively and by avoiding TOCTOU issues."""
    try:
        yield from enumerate(run_context)
    except TypeError:
        yield from ()
