import jwt
import argparse

parser = argparse.ArgumentParser(description='Decode JWT Token.')
parser.add_argument("-f", "--file", help="The input file containing the token", required=False)
parser.add_argument("-t", "--token", help="The input token string", required=False)
args = parser.parse_args()

# Your encoded JWT token
if args.file:
    with open(args.file, "r") as f:
        token = f.read().strip()
elif args.token:
    token = args.token
else:
    raise ValueError("Either --file or --token must be provided.")

try:
    # Decode and verify the token
    decoded_payload = jwt.decode(token, options={"verify_signature": False})
    print(decoded_payload)
except jwt.ExpiredSignatureError:
    print("The token has expired.")
except jwt.InvalidTokenError:
    print("Invalid token signature or malformed token.")