#!/usr/bin/env python

#
# Copyright 2021 Proxeem (https://www.proxeem.fr/)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Specials thanks to A. Razanajatovo for this great work
# mailto: arazanajatovo.dev@gmail.com
#


import argparse
import subprocess
import shlex


def getRate(primaryValue, secondaryValue):
    return float("{:.2f}".format(float(primaryValue) * 100 / (primaryValue + secondaryValue)))


#
# HTTP request with external CURL command
#
def requestByCommand():

    curlURL = args.proto + '://' + args.hostname + args.urlpath
    curlCommand = subprocess.Popen(shlex.split(
        'curl -s -w "|%{http_code}" -m ' + args.timeout + ' ' + curlURL),
        stdout = subprocess.PIPE)
    curlOutput, curlError = curlCommand.communicate()
    curlOutput = curlOutput.decode("utf-8")

    if args.debug:
        print('curlOutput : ' + curlOutput)

    curlValues = curlOutput.replace(',', '.').split('|')

    return {
        'memory': { 'rate': getRate(int(curlValues[0]), int(curlValues[1])), 'warning': int(args.warning_memory), 'critical': int(args.critical_memory), 'label': 'Memory: ' },
        'cached_keys': { 'rate': getRate(int(curlValues[2]), int(curlValues[3]) - int(curlValues[2])), 'warning': int(args.warning_cached_keys), 'critical': int(args.critical_cached_keys), 'label': 'Cached keys: ' },
        'missed': { 'rate': getRate(int(curlValues[5]), int(curlValues[4])), 'warning': int(args.warning_missed), 'critical': int(args.critical_missed), 'label': 'Missed: ' },
        'string_memory': { 'rate': getRate(int(curlValues[6]), int(curlValues[7])), 'warning': int(args.warning_string_memory), 'critical': int(args.critical_string_memory), 'label': 'String memory: ' },
        'status_code': int(curlValues[8])
    }


# Parse command line
parser = argparse.ArgumentParser(description = 'OPCache plugin for Centreon')
parser.add_argument('-d', '--debug', help = 'Output debug information (do not use with Centreon)', action = 'store_true')
parser.add_argument('--proto', help = 'Protocol', required=True)
parser.add_argument('--hostname', help = 'Hostname', required=True)
parser.add_argument('--urlpath', help = 'Relative URL', required=True)
parser.add_argument('--timeout', help = 'Request timeout', default='30')
parser.add_argument('--warning-memory', help = 'Memory used warning level (in %)', default='80')
parser.add_argument('--critical-memory', help = 'Memory used critical level (in %)', default='90')
parser.add_argument('--warning-string-memory', help = 'String memory used warning level (in %)', default='80')
parser.add_argument('--critical-string-memory', help = 'String memory used critical level (in %)', default='90')
parser.add_argument('--warning-cached-keys', help = 'Cached key used warning level (in %)', default='80')
parser.add_argument('--critical-cached-keys', help = 'Cached key used critical level (in %)', default='90')
parser.add_argument('--warning-missed', help = 'Missed rate warning level (in %)', default='5')
parser.add_argument('--critical-missed', help = 'Missed rate critical level (in %)', default='10')
args = parser.parse_args()

# Make HTTP Request
curlStats = requestByCommand()

if args.debug:
    print(curlStats)

displayOrder = [
    'memory',
    'string_memory',
    'cached_keys',
    'missed'
]

if 200 == curlStats['status_code']:
    # Compute waterfall values
    centreonStatusMessageDetails = ': '
    centreonStatusMessage = 'OK'
    centreonStatusCode = 0
    for key in displayOrder:
        if curlStats[key]['rate'] >= curlStats[key]['critical']:
            centreonStatusMessage = 'CRITICAL'
            centreonStatusCode = 2

        elif curlStats[key]['rate'] >= curlStats[key]['warning']:
            if 0 == centreonStatusCode :
                centreonStatusMessage = 'WARNING'
                centreonStatusCode = 1

        centreonStatusMessageDetails += curlStats[key]['label'] + str(curlStats[key]['rate']) + '% '

        if args.debug:
            print(curlStats[key]['label'] + str(curlStats[key]['rate']) + '% ')

    centreonStatusMessageDetails += "| 'cache_memory'=" + str(curlStats['memory']['rate']) + '% '
    centreonStatusMessageDetails += "'cache_memory_string'=" + str(curlStats['string_memory']['rate']) + '% '
    centreonStatusMessageDetails += "'cache_cached_keys'=" + str(curlStats['cached_keys']['rate']) + '% '
    centreonStatusMessageDetails += "'cache_missed'=" + str(curlStats['missed']['rate']) + '% '

    centreonStatusMessage += centreonStatusMessageDetails

else:
    # HTTP Response code KO (3xx, 4xx, 5xx or curl error)
    centreonStatusMessage = 'UNKNOWN: [' + str(curlStats['status_code']).zfill(3) + '] Invalid response code'
    centreonStatusCode = 3

# Output Centreon datas
print(centreonStatusMessage)
exit(centreonStatusCode)
