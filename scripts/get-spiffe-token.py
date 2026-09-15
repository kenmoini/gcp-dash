#!/opt/app-root/bin/python

from spiffe import JwtSource
import argparse

parser = argparse.ArgumentParser(description='Retrieve SPIFFE Token.')
parser.add_argument("-a", "--audience", help="The audience to include in the token", required=True)
args = parser.parse_args()

jwt_svid = JwtSource().fetch_svid(audience={args.audience})
print(jwt_svid.token)