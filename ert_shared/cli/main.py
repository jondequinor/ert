#!/usr/bin/env python
import logging
import os
import sys
import threading

from ert_shared import ERT
from ert_shared import clear_global_state
from ert_shared.ensemble_evaluator import EnsembleEvaluator
from ert_shared.cli.model_factory import create_model
from ert_shared.cli.monitor import Monitor
from ert_shared.cli.notifier import ErtCliNotifier
from ert_shared.cli.workflow import execute_workflow
from ert_shared.cli import WORKFLOW_MODE, ENSEMBLE_SMOOTHER_MODE, ES_MDA_MODE, ENSEMBLE_EXPERIMENT_MODE
from ert_shared.tracker.factory import create_tracker
from res.enkf import EnKFMain, ResConfig


def _clear_and_exit(args):
    clear_global_state()
    sys.exit(args)


def run_cli(args):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    res_config = ResConfig(args.config)
    os.chdir(res_config.config_path)
    ert = EnKFMain(res_config, strict=True, verbose=args.verbose)
    notifier = ErtCliNotifier(ert, args.config)
    ERT.adapt(notifier)

    if args.mode == WORKFLOW_MODE:
        execute_workflow(args.name)
        return

    model, argument = create_model(args)
    if args.disable_monitoring:
        model.startSimulations(argument)
        if model.hasRunFailed():
            _clear_and_exit(model.getFailMessage())
    else:
        # Test run does not have a current_case
        if "current_case" in args and args.current_case:
            ERT.enkf_facade.select_or_create_new_case(args.current_case)

        if (args.mode in [ENSEMBLE_SMOOTHER_MODE, ES_MDA_MODE] and 
            args.target_case == ERT.enkf_facade.get_current_case_name()):
            msg = (
                "ERROR: Target file system and source file system can not be the same. "
                "They were both: {}.".format(args.target_case)
            )
            _clear_and_exit(msg)

        thread = threading.Thread(
            name="ert_cli_simulation_thread",
            target=model.startSimulations,
            args=(argument,)
        )
        thread.start()

        tracker = create_tracker(model, tick_interval=0, detailed_interval=0)
        monitor = Monitor(color_always=args.color_always)

        try:
            monitor.monitor(tracker)
        except (SystemExit, KeyboardInterrupt):
            print("\nKilling simulations...")
            model.killAllSimulations()

        thread.join()

        if model.hasRunFailed():
            _clear_and_exit(1)  # the monitor has already reported the error message


def run_ee(args):
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    ee = EnsembleEvaluator()
    monitor= ee.run()
    
    for event in monitor.track():
        print("got event from monitor", event._event_index)

        if event.is_terminated():
            print("evaluation terminated")
            return

    print("evaluation done")
    ee.stop()
