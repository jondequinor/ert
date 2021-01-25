from ert_shared.status.tracker.legacy import LegacyTracker
from ert_shared.status.tracker.evaluator import EvaluatorTracker
from ert_shared.status.utils import scale_intervals
from ert_shared.ensemble_evaluator.config import load_config
from ert_shared.feature_toggling import FeatureToggling


def create_tracker(
    model,
    general_interval=5,
    detailed_interval=10,
    num_realizations=None,
):
    """Creates a tracker tracking a @model. The provided model
    is updated either purely event-driven, or in two tiers: @general_interval,
    @detailed_interval. Whether updates are continuous or periodic depends on
    invocation.
    Setting any interval to <=0 disables update.

    If @num_realizations is defined, then the intervals are scaled
    according to some affine transformation such that it is tractable to
    do tracking. This only applies to periodic updates.
    """
    if num_realizations is not None:
        general_interval, detailed_interval = scale_intervals(num_realizations)

    if FeatureToggling.is_enabled("ensemble-evaluator"):
        ee_config = load_config()
        return EvaluatorTracker(
            model,
            ee_config.get("host"),
            ee_config.get("port"),
            general_interval,
            detailed_interval,
        )
    return LegacyTracker(
        model,
        general_interval,
        detailed_interval,
    )
