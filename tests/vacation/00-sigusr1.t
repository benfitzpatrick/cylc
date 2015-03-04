#!/bin/bash
# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2015 NIWA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------
# Test handle of SIGUSR1. (Handle a mock job vacation.)
# Obviously, job vacation does not happen with background job, and the job
# will no longer be poll-able after the kill.
. $(dirname $0)/test_header
#-------------------------------------------------------------------------------
set_test_number 6
if [[ $(gdm --version) =~ 'GDM 3.12.2-'[23] ]]; then
    skip 6 'SIGUSR1 broken in GDM 3.12.2-[23].'
    exit 0
fi
install_suite $TEST_NAME_BASE $TEST_NAME_BASE
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-validate
run_ok $TEST_NAME cylc validate $SUITE_NAME
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-run
suite_run_ok $TEST_NAME cylc run --reference-test $SUITE_NAME
#-------------------------------------------------------------------------------
SUITE_RUN_DIR=$(cylc get-global-config --print-run-dir)/$SUITE_NAME

# Make sure t1.1.1's status file is in place
T1_STATUS_FILE=$SUITE_RUN_DIR/log/job/1/t1/01/job.status

poll '!' test -e "${T1_STATUS_FILE}"
poll '!' grep 'CYLC_JOB_PID=' "${T1_STATUS_FILE}"

# Kill the job and see what happens
T1_PID=$(awk -F= '$1=="CYLC_JOB_PID" {print $2}' "${T1_STATUS_FILE}")
kill -s USR1 $T1_PID
while ps $T1_PID 1>/dev/null 2>&1; do
    sleep 1
done
exists_fail $T1_STATUS_FILE
TIMEOUT=$(($(date +%s) + 120))
while ! grep -q 'Task job script vacated by signal USR1' \
            $SUITE_RUN_DIR/log/suite/log \
        && (($TIMEOUT > $(date +%s)))
do
    sleep 1
done
TIMEOUT=$(($(date +%s) + 10))
while ! sqlite3 $SUITE_RUN_DIR/cylc-suite.db \
            'SELECT status FROM task_states WHERE name=="t1";' \
            >"$TEST_NAME-db-t1" 2>/dev/null \
        && (($TIMEOUT > $(date +%s)))
do
    sleep 1
done
cmp_ok "$TEST_NAME-db-t1" - <<<'submitted'
# Start the job again and see what happens
mkdir -p $SUITE_RUN_DIR/work/1/t1/
touch $SUITE_RUN_DIR/work/1/t1/file # Allow t1 to complete
$SUITE_RUN_DIR/log/job/1/t1/01/job </dev/null >/dev/null 2>&1 &
# Wait for suite to complete
TIMEOUT=$(($(date +%s) + 120))
while [[ -f ~/.cylc/ports/$SUITE_NAME ]] && (($TIMEOUT > $(date +%s))); do
    sleep 1
done
# Test t1 status in DB
sqlite3 $SUITE_RUN_DIR/cylc-suite.db \
    'SELECT status FROM task_states WHERE name=="t1";' >"$TEST_NAME-db-t1"
cmp_ok "$TEST_NAME-db-t1" - <<<'succeeded'
# Test reference
TIMEOUT=$(($(date +%s) + 120))
while ! grep -q 'DONE' $SUITE_RUN_DIR/log/suite/out \
        && (($TIMEOUT > $(date +%s)))
do
    sleep 1
done
grep_ok 'SUITE REFERENCE TEST PASSED' $SUITE_RUN_DIR/log/suite/out
#-------------------------------------------------------------------------------
purge_suite $SUITE_NAME
exit
