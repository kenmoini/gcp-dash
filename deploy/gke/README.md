# GKE WIF Deployment

```bash
REGION="us-central1"
GKE_NAME="autopilot-cluster-1"

KNS="gcp-dash"
KSA="gcp-dash"
GSA_NAME="gcp-dash"
PROJECT=$(gcloud config get-value project)
PROJECT_ID=$(gcloud config get-value project) # This is the same in some envs
BUCKET_NAME="gcp-dash-${PROJECT}"
GSA_ID="${GSA_NAME}@${PROJECT}.iam.gserviceaccount.com"

# Create A GCP ServiceAccount
gcloud iam service-accounts create ${GSA_NAME} --project=${PROJECT}

# Create a Bucket to ensure there's some data in the dash
gcloud storage buckets create gs://${BUCKET_NAME}

# Give GSA Access to the bucket
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} --member="serviceAccount:${GSA_ID}" --role="roles/storage.objectViewer"

# Give Service Account Access to APIs
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/container.clusterViewer" \
    --member="serviceAccount:${GSA_ID}" \
    --condition=None
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/storage.objectViewer" \
    --member="serviceAccount:${GSA_ID}" \
    --condition=None
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/storage.bucketViewer" \
    --member="serviceAccount:${GSA_ID}" \
    --condition=None
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/compute.viewer" \
    --member="serviceAccount:${GSA_ID}" \
    --condition=None
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/compute.networkViewer" \
    --member="serviceAccount:${GSA_ID}" \
    --condition=None

# Get WID Endpoint from GKE cluster
WID_ENDPOINT=$(gcloud container clusters describe ${GKE_NAME} --region=${REGION} --format="value(workloadIdentityConfig.workloadPool)")

# Add Impersonation ability IAM Binding
gcloud iam service-accounts add-iam-policy-binding ${GSA_ID} \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:${WID_ENDPOINT}[${KNS}/${KSA}]"

# Annotate the ServiceAccount
kubectl annotate serviceaccount ${KSA} -n ${KNS} iam.gke.io/gcp-service-account=${GSA_ID}

# Make sure the GOOGLE_APPLICATION_CREDENTIALS env var is not set in the Deployment and the Secret is not made
```