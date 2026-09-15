# Zero Trust Workload Identity Management with GCP

```bash
KNS="gcp-dash"
KSA="gcp-dash"
WORKLOAD_NAME="ztwim-gcp-dash"
PROJECT=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format="value(projectNumber)")
GSA_NAME="gcp-dash"
GSA_ID="${GSA_NAME}@${PROJECT}.iam.gserviceaccount.com"

GOOGLE_AUDIENCE="https://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WORKLOAD_NAME}/providers/${WORKLOAD_NAME}"

# Create trust between ZTWIM and GCP WIF
ZTWIM_OIDC_ISSUER=$(oc get route -n zero-trust-workload-identity-manager spire-oidc-discovery-provider -o jsonpath='{ .spec.host }')

gcloud iam workload-identity-pools create ${WORKLOAD_NAME} --location="global" --display-name="${WORKLOAD_NAME}"

gcloud iam workload-identity-pools providers create-oidc ${WORKLOAD_NAME} \
    --location="global" \
    --workload-identity-pool="${WORKLOAD_NAME}" \
    --issuer-uri="https://${ZTWIM_OIDC_ISSUER}" \
    --attribute-mapping="google.subject=assertion.sub"



SPIFFE_ID_WORKLOAD_APP="spiffe://$(oc get cm -n zero-trust-workload-identity-manager spire-server -o jsonpath='{ .data.server\.conf }' | jq -r '.server.trust_domain')/ns/${KNS}/sa/${KSA}"

# Give workload in K8s NS access
gcloud iam service-accounts add-iam-policy-binding ${GSA_ID} \
    --role roles/iam.workloadIdentityUser \
    --member "principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WORKLOAD_NAME}/subject/${SPIFFE_ID_WORKLOAD_APP}"

# Generate Template JSON
gcloud iam workload-identity-pools create-cred-config \
    projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WORKLOAD_NAME}/providers/${WORKLOAD_NAME} \
    --service-account=${GSA_ID} \
    --output-file=./google-credentials.json \
    --credential-source-file=/opt/app-root/src/spiffe-token-google.txt \
    --credential-source-type=text
```

```json
{
  "universe_domain": "googleapis.com",
  "type": "external_account",
  "audience": "//iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WORKLOAD_NAME}/providers/${WORKLOAD_NAME}",
  "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
  "token_url": "https://sts.googleapis.com/v1/token",
  "credential_source": {
    "file": "/opt/app-root/src/spiffe-token-google.txt",
    "format": {
      "type": "text"
    }
  },
  "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${GSA_ID}:generateAccessToken"
}
```