#!/usr/bin/env python3

import re
import subprocess
import sys
from enum import Enum

JOB_STATE_RGX = re.compile(r"job_state\s*=\s*(?P<status>[A-Z])", re.IGNORECASE)
EXIT_STATUS_RGX = re.compile(r"exit_status\s*=\s*(?P<excode>\d+)", re.IGNORECASE)


class PbsStatusError(Exception):
    pass


class Status(Enum):
    Running = "running"
    Failed = "failed"
    Success = "success"


class StatusCode(Enum):
    Exiting = "E"  # Job is exiting after having run.
    ArrayJob = "B"  # Array job: at least one subjob has started.
    Finished = "F"
    Held = "H"
    Moved = "M"  # Job was moved to another server.
    Queued = "Q"
    Running = "R"
    Suspended = "S"
    MovedToNewLocation = "T"  # Job is being moved to new location.
    Waiting = "W"  # Job is waiting for its submitter-assigned start time to be reached.
    SubjobComplete = "X"  # Subjob has completed execution or has been deleted.
    CycleHarvest = "U"  # Cycle-harvesting job is suspended due to keyboard activity.

    def is_finished(self) -> bool:
        return self in (StatusCode.Finished, StatusCode.SubjobComplete)


def eprint(msg: str):
    print(msg, file=sys.stderr)


def main():

    jobid = sys.argv[1]
    cmd = "qstat -fx {}".format(jobid)

    try:
        res = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
        )
    except (subprocess.CalledProcessError, IndexError, KeyboardInterrupt) as e:
        raise PbsStatusError(
            "Failed to get status with {cmd} and error {err}".format(cmd=cmd, err=e)
        )

    qstat_output = res.stdout.decode()
    m = JOB_STATE_RGX.search(qstat_output)
    if not m:
        raise PbsStatusError(
            "Could not find job state in qstat output\n{}".format(qstat_output)
        )

    status = StatusCode(m.group("status"))

    if not status.is_finished():
        print(Status.Running.value)
    else:
        m = EXIT_STATUS_RGX.search(qstat_output)
        if not m:
            raise PbsStatusError(
                "Could not find exit code (status) for finished job\n{}".format(
                    qstat_output
                )
            )

        exit_code = int(m.group("excode"))
        if exit_code == 0:
            print(Status.Success.value)
        else:
            print(Status.Failed.value)


if __name__ == "__main__":
    main()
