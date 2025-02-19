#!/usr/bin/env python3
# pylint: disable=no-member
'''
This is a Python Script for Cloudflare's DNS API
(c) 2025 by av8rgeek systems, llc
This script is licensed under the MIT License.

This script reads from a CSV file containing the following columns:
zone_name,status,match_url,action,destination,httpcode,priority

It then calls the Cloudflare API to verify the existence of the record
from the specified zone and, if it does not exist, add it
to Cloudflare.  TTL is set to AUTO by default.
The script will print out progress information.
This script has been updated to reflect the Cloudflare Python SDK v4.0.0,
   but has not been tested for functionality.  Please test before using in production.
'''
import os
import sys
import csv
import argparse
import json
import cloudflare
from cloudflare import Cloudflare
import tldextract

#debug = False
#override_ttl = True

def init_argparse() -> argparse.ArgumentParser:
    ''' Define the arguments for the script and how to handle them '''
    parser = argparse.ArgumentParser(
        description="Use the switches to provide the input",
        epilog="""This script reads from a CSV file containing
        4 columns, hostname, RR type, answer, and proxied.  It
        then calls the Cloudflare API to verify the existence of the record
        from the specified zone and, if it does not exist, add it
        to Cloudflare.  TTL is set to AUTO by default.  
        The script will print out progress information."""
    )
    parser.add_argument(
        "file",
        type=str,
        help='CSV file to be read'
    )
    parser.add_argument(
        "--debug",
        action='store_true',
        required=False,
        help='Enable debugging output'
    )
    #parser.add_argument(
    #    "--noautottl",
    #    action='store_false',
    #    required=False,
    #    help='Enable debugging output'
    #)
    parser.add_argument(
        "-p", "--profile",
        default="your-authentication-profile-name",
        type=str,
        required=False,
        help='Cloudflare authentication profile (from ".cloudflare.cfg")'
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version = f"{parser.prog} version 1.0.0",
        help='Show the version of this program'
    )
    return parser


# @param header_names:  List object of header names
def ValidHeaders(header_names):
    ''' Make sure we have all the correct headers in the CSV file '''
    columns = []
    for hdr in header_names:
        # Look for specific header fields for us to use
        # Valid headers 
        # zone_name,status,match_url,action,destination,httpcode,priority
        if ((hdr == "zone_name") or (hdr == "status") or (hdr == "match_url") or (hdr == "action") or (hdr == "destination") or (hdr == "httpcode") or (hdr == "priority")):
            columns.append(hdr) 
    if len(columns) != 7:
        return False
    else:
        return True


def ValidateTLD(dnsname):
    ''' Ensure we have a valid TLD for the dns domain'''
    dns = tldextract.extract(dnsname)
    if len(dns.suffix) == 0:
        return ""
    else:
        return f'{dns.domain}.{dns.suffix}'

    
def main() -> None:
    ''' Main function for the script '''
    # Define some basic variables.
    count = 0           # Counts the number of records processed successfully

    # Get the Arguments and parse them
    parser = init_argparse()
    if len(sys.argv) > 1:
        args = parser.parse_args()
    else:
        parser.print_help()
        sys.exit(1)

    # Take action on arguments
    #  Note:  --help and --version arguments are handled before now
    if not args.file:
        parser.print_help()
        sys.exit(1)
    else:
        infile = args.file
    debug = args.debug

    # * Execute the program's main functions now

    # Authenticate to the API and load the zone data
    print("Accessing Cloudflare API")
    cf = Cloudflare(profile=args.profile)

    # Read the CSV file.
    print("Reading data from %s..." % infile) 
    with open(infile, newline='') as f:
        reader = csv.DictReader(f, delimiter=',')
    
        # Read the headers to make sure we have all the correct columns to reference
        headers = reader.fieldnames
        if (not ValidHeaders(headers)):
            sys.stderr.write("Missing critical columns from CSV file. Terminating.\r\n")
            sys.exit(1)

        try:
            for row in reader:
                if debug:
                    print(f'Processing {row["domain"]}...')

                # Extract the zone name from the row['domain'] field and make sure it is a valid TLD
                zone_name = row['zone_name']
                
                # Get the Zone data from the API
                try:
                    zones = cf.zones.get(params = {'name':zone_name,'per_page':1})
                except Cloudflare.APIError as e:
                    sys.stderr.write('/zones.get %d %s - api call failed\r\n' % (e, e))
                    exit(1)
                except Exception as e:
                    sys.stderr.write(f'/zones.get - {e} - api call failed\r\n')
                    exit(1)

                # If the Zone is not found, Write it to stderr and move on.
                if len(zones) == 0:
                    sys.stderr.write(f'{zone_name} not found.  Skipping.\r\n')
                    continue
                else:
                    zone_id = zones[0]['id']

                # Validate the action 

                # If the Priority of the page rule is not defined, set it to "1"
                if int(row['priority']) == 0:
                    priority = 1
                else:
                    priority = int(row['priority'])

                # Check for a 301/302 HTTP Status Code when redirecting.  Otherwise, skip
                if int(row["httpcode"]) == 301:
                    response_code = int(row["httpcode"])
                elif int(row["httpcode"]) == 302:
                    response_code = int(row["httpcode"])
                else:
                    sys.stdout.write(f'HTTP Response Code {row["httpcode"]} is not valid.  Only 301/302 are valid codes, skipping\r\n')
                    continue

                # Set up the page rule action for a forwarding url
                if row['action'] == "forwarding_url":
                        new_pagerule = {
                            "targets": [
                                {
                                    "target": "url",
                                    "constraint": {
                                        "operator": "matches",
                                        "value": row["match_url"]
                                    }
                                }
                            ],
                            "actions": [
                                {
                                "id": row["action"],
                                "value": {
                                    "url": row["destination"],
                                    "status_code": response_code
                                    }
                                }
                            ],
                            "priority": priority,
                            "status": row['status']
                        }
                        print(f'{new_pagerule}\r\n')
                else:
                    sys.stdout.write(f' {row["action"]} is not supported at this time, skipping\r\n')
                    continue

                # * Try to create the Page Rule using the API
                try:
                    sys.stdout.write(f'Creating Page Rule...')
                    dns_record = cf.zones.pagerules.post(zone_id, data=new_pagerule)
                    sys.stdout.write(f'success!\r\n')
                    count += 1
                except Cloudflare.APIError as e:
                    #print (e.args[0])
                    if (e.args[0] == 81053) or (e.args[0] == 81057):
                        sys.stdout.write(f'Failed!  Rule Already exists.  Moving on to next rule..\r\n')
                    else:
                        sys.stdout.write(f'Failed:  {int(e)}: {str(e)} - api call failed. Skipping.\r\n')
                        #sys.stderr.write('%s (%s) = %s : /zones/dns_records.post %d %s - api call failed\r\n' % (fqdn, row['type'], row['answer'], e, e))
                    continue

                # If we are debugging, print the record
                if debug:
                    pass
                    # print('\t%s %30s %6d %-5s %s ; proxied=%s proxiable=%s' % (
                    #     dns_record['id'],
                    #     dns_record['name'],
                    #     dns_record['ttl'],
                    #     dns_record['type'],
                    #     dns_record['content'],
                    #     dns_record['proxied'],
                    #     dns_record['proxiable']
                    # ))
        # Catch any errors reading the file
        except csv.Error as e:
            sys.stderr.write(f'File {infile}, line {reader.line_num}: {e}\r\n' )
    print(f'Script Complete. {count} records created.')
    exit(0)


if __name__ == "__main__":
    ''' Run the program '''
    main()

# This is an example of a page rule (when the script was first developed)
"""
{
    'id': 'ab19c685f22a0d3b13f23d0789dae5f2', ### NOT A REAL ID
    'targets': [
        {
            'target': 'url',
            'constraint': {
                'operator': 'matches',
                'value': 'example.com/url/'
            }
        }
    ],
    'actions': [
        {
            'id': 'forwarding_url',
            'value': {
                'url': 'https://example.com/url',
                'status_code': 301
            }
        }
    ],
    'priority': 11,
    'status': 'active'
}
"""