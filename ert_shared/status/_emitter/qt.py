class QEmitter:
    """The QEmitter emit events for Qt-based consumers using a dynamically
    created QObject-derived class named qt_emitter."""

    def __init__(
        self,
        tracker,
        event_handler,
    ):
        """See create_tracker for details."""
        self._tracker = tracker
        self._event_handler = event_handler


    def track(self):
        
        # if general_interval > 0:
        #     timer = qobject_cls()
        #     timer.setInterval(general_interval * 1000)
        #     timer.timeout.connect(self._general)
        #     self._qtimers.append(timer)

        # if detailed_interval > 0:
        #     timer = qobject_cls()
        #     timer.setInterval(detailed_interval * 1000)
        #     timer.timeout.connect(self._detailed)
        #     self._qtimers.append(timer)

    # def _general(self):
    #     self._event_handler(self._tracker.general_event())

    #     # Check for completion. If Complete, emit all events including a final
    #     # EndEvent. All timers stop after that.
    #     if self._tracker.is_finished():
    #         self._detailed()
    #         self._end()

    #         self.stop()

    # def _detailed(self):
    #     self._event_handler(self._tracker.detailed_event())

    # def _end(self):
    #     self._event_handler(self._tracker.end_event())

    # def track(self):
    #     for timer in self._qtimers:
    #         timer.start()

    # def stop(self):
    #     for timer in self._qtimers:
    #         timer.stop()
