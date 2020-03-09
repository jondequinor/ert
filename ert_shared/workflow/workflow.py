from ert_shared.workflow import Result


def start(name, success_func, failed_func, canceled_func):
    """Starts a workflow, returns immediately but will execute one of the
    callback functions provided at the end of the workflow."""
    pass


def run(name):
    """Runs a workflow. Returns a Result."""
    try:
        runner = ERT.enkf_facade.create_workflow_runner(name)
    except KeyError:
        return Result().with_error(
            "Workflow {} is not in the list of available workflows".format(name)
        )

    runner.run()
    runner.wait()

    report = Result().from_report(runner.workflowReport())

    success = runner.workflowResult()
    if not success:
        report.with_error(runner.workflowError())

    return report
    # workflow_list = ERT.enkf_facade.get_workflow_list()
    # try:
    #     workflow = workflow_list[workflow_name]
    # except KeyError:
    #     msg = "Workflow {} is not in the list of available workflows"
    #     logging.error(msg.format(workflow_name))
    #     return
    # context = workflow_list.getContext()
    # workflow.run(ert=ERT.ert, verbose=True, context=context)
    # all_successfull = all([v['completed']
    #                        for k, v in workflow.getJobsReport().items()])
    # if all_successfull:
    #     logging.info("Workflow {} ran successfully!".format(workflow_name))
