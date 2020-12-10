import time


class BlockingEmitter:
    """The BlockingEmitter emit events for non-qt consumers via a generator."""

    def __init__(
        self,
        tracker,
        general_interval,
        detailed_interval,
    ):
        """See create_tracker for details."""
        self._tracker = tracker
        self._general_interval = general_interval
        self._detailed_interval = detailed_interval

    def track(self):
        """Tracks the model in a blocking manner. This method is a generator
        and will yield events at the appropriate times."""
        tick = 0
        while not self._tracker.is_finished():
            if self._general_interval and tick % self._general_interval == 0:
                yield self._tracker.general_event()
            if self._detailed_interval and tick % self._detailed_interval == 0:
                yield self._tracker.detailed_event()

            tick += 1
            time.sleep(1)

        # Simulation done, emit final updates
        if self._general_interval > 0:
            yield self._tracker.general_event()

        if self._detailed_interval > 0:
            yield self._tracker.detailed_event()

        yield self._tracker.end_event()

    def stop(self):
        raise NotImplementedError("cannot stop BlockingEmitter")
