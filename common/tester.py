"""Lightweight test framework for CPU_Sim unit testing.

Responsibility:
- Provide a simple, testing utility that avoids heavyweight
  frameworks (like pytest/unittest) while still enabling clear, organized tests.
- Enable assertion-based testing with readable pass/fail output suitable for
  educational contexts.

Design note:
- This module intentionally stays minimal to avoid complexity. Students should be
  able to understand the entire testing infrastructure at a glance. The
  run_tests_for_function helper does exactly what its name suggests—nothing more.
- Tests are integrated directly into each module using the
  `if __name__ == "__main__":` pattern. This means students can run any module
  directly (e.g., `python common/utils.py`) to see its tests execute immediately.
  This approach makes testing a natural part of learning each module.

Entry point / public API:
- :func:`run_tests_for_function`: Test a single function against multiple
  input/output pairs with automatic pass/fail reporting.

How to use:
1. Import the function or module to test
2. Create lists of arguments and expected results:
   - args: list of tuples, where each tuple contains the arguments for one test case
   - expected: list of expected return values (one per test case)
3. Call run_tests_for_function with the function, args, expected, and optional comment
4. The function reports pass/fail status; failed tests show detailed error messages

Example:
    from assembler.assembler import _parse_immediate_operand

    test_args = [
        ("#42",),    # Decimal literal
        ("B1010",),  # Binary literal
        ("&2A",),    # Hexadecimal literal
    ]
    test_expected = [42, 10, 42]

    run_tests_for_function(
        test_args,
        test_expected,
        _parse_immediate_operand,
        comment="normal values"
    )

Design philosophy:
- Each test case is a tuple of arguments and a single expected result
- Tests report clearly: either "OK" if all pass, or "FAIL" with details
- Comments are optional but recommended for clarity
- Students can add tests without learning a complex testing framework

Illustrates:
- CIE 9618: 12.3 Program Testing and Maintenance:
    - Show understanding of the methods of testing available and selecting
      appropriate data for a given method.
    - Show understanding of the need for a test strategy and test plan.
- CIE 9618: 9.1 Computational Thinking Skills:
    - Show an understanding of abstraction (testing abstraction reduces framework
      complexity while maintaining rigor).
    - Describe and use decomposition (breaking complex testing logic into a
      single, reusable utility function).
"""

from typing import Callable


def run_tests_for_function(
    args: list[tuple], expected: list, function: Callable, comment=""
) -> bool:
    """Test a function against multiple input/output pairs, including error cases.

    Runs the given function against each set of arguments and compares the
    result to the corresponding expected value. Prints a summary: either
    "OK" if all tests pass, or "FAIL" with details for each failed test.

    Special case: Use the string "error" as an expected value to indicate that
    the function should raise an exception for that input. The function will
    pass the test if any exception is raised (we don't check the exception type).

    Args:
        args: List of argument tuples. Each tuple contains the arguments for
            one test case. Example: [("#42",), ("B1010",), ("&2A",)]
        expected: List of expected return values (one per test case).
            Must be same length as args. Use the string "error" to expect
            an exception to be raised.
            Example: [42, 10, "error"]  - last test expects an exception
        function: The function to test (will be called as function(*arg)
            for each arg in args).
        comment: Optional string describing what this batch of tests covers.
            Appears in the test report for clarity.

    Returns:
        bool. True if and only if all cases passed. Used to chained multiple tests
        and obtain a complete result at the end.

    Raises:
        No exceptions raised by this function; assertion failures and
        unexpected exceptions are reported as "FAIL" with details.

    Example:
        # Test the _parse_immediate_operand function, including error cases
        test_args = [("#42",), ("B1010",), ("&2A",), ("invalid",)]
        expected = [42, 10, 42, "error"]  # Last case should raise an error
        run_tests_for_function(test_args, expected, _parse_immediate_operand,
                               comment="immediate operands with error handling")

        # Output (if all pass):
        # test _parse_immediate_operand (immediate operands with error handling) ... OK

        # Output (if some fail):
        # test _parse_immediate_operand (immediate operands with error handling) ... FAIL
        #
        #   Test 1 failed: for args ('B1011',), expected 10 but got 11
    """
    passed = True
    function_name = function.__name__
    report = f"test {function_name} "
    report += f"({comment}) ... " if comment else " ... "
    fail_messages = []
    for i, (arg, exp) in enumerate(zip(args, expected)):
        try:
            result = function(*arg)
        except Exception as e:
            # Educational note: In a real test suite (pytest, unittest), we would
            # check the exact exception type and message (e.g., assertRaises with
            # AssemblingError). Here, we just verify that *some* exception was
            # raised, which is sufficient for this educational context but less
            # robust in production code.
            if exp == "error":
                continue
            else:
                fail_messages.append(
                    f"Test {i} failed: for args {arg}:\n  expected {exp}\n  but got exception {e}"
                )
                passed = False
                continue
        if result != exp:
            fail_messages.append(
                f"Test {i} failed: for args {arg}:\n  expected {exp}\n  but got {result}"
            )
            passed = False
    if passed:
        print(report + "OK")
        return True
    else:
        print(report + "FAIL")
        for msg in fail_messages:
            print("\n  " + msg)
        return False

def test_module(module_name: str, test_functions: list, verbose=False):
    # Run all tests
    print(f"\n------------------------\nTesting {module_name.upper()}:\n------------------------\n")
    results = [test_function(verbose) for test_function in test_functions]
    success = True
    for result in results:
        if not result:
            success = False
            break
    if success:
        print(
            f"\n------------------------\n{module_name.upper()}: ALL TESTS PASSED\n------------------------\n"
        )
    else:
        print(
            f"\n------------------------\n{module_name.upper()}: FAILED\n------------------------\n"
        )
