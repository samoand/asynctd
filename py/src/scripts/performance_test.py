"""Test the async task distributor using distribute_async_w_arg_divide."""
# pylint: disable=R0801

import argparse
import logging
import asyncio

from scripts import performance_test_base


async def run_performance_test(repeat_times, simulate_activity_coef):
    """Run the async performance test."""
    logging.basicConfig(level=logging.DEBUG)

    await performance_test_base.run_all_tests(
        repeat_times, simulate_activity_coef)


def main():
    """Parse arguments and run the test."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-r', '--repeat-times',
        dest='repeat_times',
        default=1,
        type=int,
        help='Number of times to produce list of char combos')
    parser.add_argument(
        '-s', '--simulate-activity-coef',
        dest='simulate_activity_coef',
        default=1000,
        type=int,
        help='Number of times to swap every word, '
        'to simulate cpu-intensive op')

    args = parser.parse_args()

    # Run the async performance test using asyncio
    asyncio.run(
        run_performance_test(args.repeat_times, args.simulate_activity_coef))


if __name__ == '__main__':
    main()
