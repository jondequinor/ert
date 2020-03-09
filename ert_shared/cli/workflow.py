import logging
import sys

from ert_shared import ERT
from ert_shared import workflow


def execute_workflow(workflow_name):
    result = workflow.run(workflow_name)

    if result.had_failures():
        for error in result.errors():
            logging.error(error)
            sys.exit(1)

    logging.info(
        "Workflow {} with {} jobs ran successfully".format(
            workflow_name, result.number_of_jobs()
        )
    )
    # workflow_runner = ERT.enkf_facade.create_workflow_runner(workflow_name)
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
