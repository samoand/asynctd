
Since [Python3 version of Workload Distributor](https://github.com/samoand/workload_distributor3) no longer support parallelization via multiple processes, the remaining thread-based implementation doesn't seem to have any advantages over async approach for CPython.

This utility is an async-based rework of the above, with minor API changes.

How-To:

Define arg_divider (optional): it should take 1 arguments:

       - value that is to be divided into parts

       Implementation should return the parts. Their structure is to
       be consistent with the signature of the decorated method
       arg_divider may be None. In this case the tasks use elements
       of the dividable input param as their inputs.

Define result_reducer:

       it's argument is a list of partial result. It should use that
       list to build final result.

See tests for examples on how to use run_distributively as a decorator.

Supported semantics:

  - arg divider
  - result reducer
  - policy for exception handling


