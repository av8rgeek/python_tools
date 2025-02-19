#!/usr/bin/env python3
# pylint: disable=no-member
'''
This is a Python Script for Cloudflare's DNS API 
(c) 2025 by av8rgeek systems, llc
This script is licensed under the MIT License.
'''
import os
import sys
import argparse
import json
import cloudflare
from cloudflare import Cloudflare
# import tldextract

### This script has been updated to reflect the Cloudflare Python SDK v4.0.0,
###    but has not been tested for functionality.  Please test before using in production.

def init_argparse() -> argparse.ArgumentParser:
    ''' Define the arguments for the script and how to handle them '''
    parser = argparse.ArgumentParser(
        description="Specify the DNS Zone Name and Cloudflare API Key",
        epilog="""This script calls the Cloudflare API to read all of the records
        from the specified zone and outputs the data into a CSV
        file of <ZONE_NAME>.csv.  If the domain is example.com,
        then the output file will be example.com.csv"""
    )
    parser.add_argument(
        "-p", "--profile",
        default="your-authentication-profile-name",
        type=str,
        required=False,
        help='Cloudflare authentication profile (from ".cloudflare.cfg)"'
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version = f"{parser.prog} version 1.0.0"
    )
    parser.add_argument(
        "-z","--zone",
        type=str,
        required=True,
        help='Zone to query',
    )
    return parser

# *** Main ***    
def main() -> None:
    ''' Main function for the script '''
    # ** Parse the arguments
    parser = init_argparse()
    if len(sys.argv) > 1:
        args = parser.parse_args()
    else:
        parser.print_help()
        sys.exit(2)

    # ** Take action on arguments
    #  Note:  --help and --version arguments are handled before now
    if not args.zone:
        parser.print_help()
        sys.exit(1)

    # ** Execute the program's main functions now

    # Authenticate to the Cloudflare API
    cf = Cloudflare(profile=args.profile)

    # Query for the zone name and expect only one value back
    try:
        zones = cf.zones.get(params = {'name':args.zone,'per_page':1})
    except cloudflare.APIError as e:
        sys.stderr.write('/zones/.get %d %s - api call failed\r\n' % (e, e))
        exit(1)
    except Exception as e:
        sys.stderr.write('/zones.get - %s - api call failed' % (e))
        exit(1)

    if len(zones) == 0:
        exit('No zones found')

    zone_id = zones[0]['id']

    # request the DNS records from that zone
    try:
        pagerules = cf.zones.pagerules.get(zone_id)
    except cloudflare.APIError as e:
        sys.stderr.write('/zones/pagerules.get %d %s - api call failed\r\n' % (e, e))
        exit(1)
    except Exception as e:
        sys.stderr.write('/zones/pagerules.get - %s - api call failed' % (e))
        exit(1)

# id targets actions priority status created_on modified_on

    # then all the DNS records for that zone
    # for rule in pagerules:
    #     r_targets = rule['targets']
    #     r_actions = rule['actions']
    #     r_ = dns_record['content']
    #     r_id = dns_record['id']
    #     print (r_name, r_type, r_value, r_id)

    #json_object = json.loads(str(pagerules))
    #print(json.dumps(json_object, indent=2))
    #print (str(pagerules))

    for rule in pagerules:
        r_id = rule['id']
        r_targets = rule['targets']
        print(rule['targets'][0]['constraint']['value'])
        print(rule['targets'][0]['constraint']['value'])
        r_actions = rule['actions']
        r_priority = rule['priority']
        r_status = rule['status']
        r_created_on = rule['created_on']
        r_modified_on = rule['modified_on']
        output = f"Rule ID: {r_id}\nTarget(s): {r_targets}\nActions: {r_actions}\nPriority: {str(r_priority)}\nStatus: {r_status}\nCreated: {r_created_on}\nModified: {r_modified_on}\n"
        print(f"{output}\n")
        #r_json = json.load(rule)
        #print(json.dumps(r_json, indent=2))
    exit(0)


# Run the program
if __name__ == '__main__':
    main()
