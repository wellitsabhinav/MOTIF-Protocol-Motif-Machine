# Verification

Run `python -m pip install -e '.[test]'` and `python -m pytest -q` from the repository
root. Python 3.11 or later is supported. Tests operate wires through the frontend,
not through protocol-specific receive shortcuts.

SPI seeds are 7, 41 and 20261012, with 200 frames per seed. Assertion failures
report the seed and frame index. Guardian randomized requests use seed 141 and
5,000 requests. Directed tests cover raw deselection with stale OE, conflicting
owners, open-drain requests, timeout, partial-frame abort, FIFO bounds, reset,
UART stop failure and recovery without reset.

CI installs the package and runs the same tests. RTL differential verification,
formal proofs, synthesis and physical qualification are future milestones. No
formal result is implied by simulation. Heavy physical jobs will be manually
dispatched. Generated runs, traces and waveforms remain untracked.
