"""Test the async task distributor using distribute_w_wide_step."""
# pylint: disable=R0801

import argparse
import logging
import asyncio
import time

from scripts import performance_test_base


async def run_performance_test(repeat_times, simulate_activity_coef):
    """Run the async performance test."""
    logger = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)

    data = performance_test_base.prepare_data()
    valid_keys = data.valid_keys
    words = data.words * repeat_times

    starting_time = time.time()
    result = await performance_test_base.distribute_w_wide_step(
        valid_keys, words, simulate_activity_coef)
    logger.info('Time to run distribute_w_wide_step: %d, '
                'result size: %d',
                time.time() - starting_time, len(result))


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
