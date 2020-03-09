class Result(object):
    def __init__(self, workflow):
        self._workflow = workflow
        self._errors = []
        self._job_status = None

    def had_errors(self):
        return len(self._errors) > 0

    def errors(self):
        return self._errors

    def number_of_jobs(self):
        return 0 if self._job_status is None else len(self._job_status.items())

    def _add_error(self, error):
        self.errors.append(error)

    def with_error(self, error):
        self._add_error(error)
        return self

    @staticmethod
    def from_report(report):
        result = Result()
        result._job_status = report
        for k, v in report.items():
            if not v["completed"]:
                result._add_error(
                    "{} failed with result {}.\nSTDOUT: {}\nSTDERR: {}".format(
                        k, v["return_value"], v["stdout"], v["stderr"]
                    )
                )
