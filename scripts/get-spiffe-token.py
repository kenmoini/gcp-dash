#!/opt/app-root/bin/python

from spiffe import JwtSource
import argparse

parser = argparse.ArgumentParser(description='Retrieve SPIFFE Token.')
parser.add_argument("-a", "--audience", help="The audience to include in the token", required=True)
parser.add_argument("-o", "--output", help="The output file to write the token to", required=False)
args = parser.parse_args()

jwt_svid = JwtSource().fetch_svid(audience={args.audience})
if args.output:
    with open(args.output, "w") as f:
        f.write(jwt_svid.token)
else:
    print(jwt_svid.token)