#!/usr/bin/env python
from res.enkf import ErtScript
import sys


class FailingJob(ErtScript):
    def run(self, job_config_file):
        raise Exception("{} {} {}\n".format("fail", sys.argv, job_config_file))
