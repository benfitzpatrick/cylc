#!/bin/bash
# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2016 NIWA
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
# Test "cylc poll" for loadleveler, slurm, or pbs jobs.
. $(dirname $0)/test_header
#-------------------------------------------------------------------------------
BATCH_SYS_NAME="${TEST_NAME_BASE##??-}"
RC_PREF="[test battery][batch systems][$BATCH_SYS_NAME]"
export CYLC_TEST_BATCH_TASK_HOST=$( \
    cylc get-global-config -i "${RC_PREF}host" 2>'/dev/null')
export CYLC_TEST_BATCH_SITE_DIRECTIVES=$( \
    cylc get-global-config -i "${RC_PREF}[directives]" 2>'/dev/null')
if [[ -z "${CYLC_TEST_BATCH_TASK_HOST}" || "${CYLC_TEST_BATCH_TASK_HOST}" == None ]]
then
    skip_all "\"[test battery][batch systems][$BATCH_SYS_NAME]host\" not defined"
fi
set_test_number 2
#-------------------------------------------------------------------------------
install_suite $TEST_NAME_BASE $TEST_NAME_BASE
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-validate
run_ok $TEST_NAME cylc validate $SUITE_NAME
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-run
suite_run_ok $TEST_NAME cylc run --reference-test --debug $SUITE_NAME
#-------------------------------------------------------------------------------
if [[ "${CYLC_TEST_BATCH_TASK_HOST}" != 'localhost' ]]; then
    ssh -n -oBatchMode=yes -oConnectTimeout=5 "${CYLC_TEST_BATCH_TASK_HOST}" \
        "rm -fr 'cylc-run/${SUITE_NAME}'"
fi
purge_suite $SUITE_NAME
