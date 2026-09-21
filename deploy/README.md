# GCP Dashboard Deployment Guide

The included assets allow for deploying this GCP dashboard application on:

- [Google Kubernetes Engine](./gke/) with Workload Identity enabled
- [Kubernetes](./kubernetes/)/[OpenShift](./openshift/) with a Static ServiceAccount Secret for testing purposes
- OpenShift with [Zero Trust Workload Identity Management](./ztwim/) federating to Google Cloud IAM

Before doing either of those, there are some prerequiste steps needed be done in Google Cloud to setup the base IAM structure, the needed RBAC, and a sample resource.

## Prerequisites - All

This assumes you have a Google Cloud account with a Project already set up.  Run the following in the Cloud Console:

```bash
# Region
REGION="us-central1"
# Auto-query the project unless you want to set something else
PROJECT=$(gcloud config get-value project)

# This should be consistent
GOOGLE_SA_NAME="gcp-dash"
GOOGLE_SA_ID="${GOOGLE_SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

### [Optional]
# If you don't have any resources in the Project, create a sample Storage Bucket so the dashboard can show some data
BUCKET_NAME="gcp-dash-${PROJECT}" # This has to be unique from all the buckets ever
gcloud storage buckets create gs://${BUCKET_NAME}

### [Required]
# Create a Google Service Account
gcloud iam service-accounts create ${GOOGLE_SA_NAME} --project=${PROJECT}

### RBAC
# Give the Google Service Account access to APIs used by the dashboard

# Workload Identity User
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${GOOGLE_SA_ID}" \
    --condition=None

# Storage Viewer
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/storage.objectViewer" \
    --member="serviceAccount:${GOOGLE_SA_ID}" \
    --condition=None
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/storage.bucketViewer" \
    --member="serviceAccount:${GOOGLE_SA_ID}" \
    --condition=None

# GKE Viewer
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/container.clusterViewer" \
    --member="serviceAccount:${GOOGLE_SA_ID}" \
    --condition=None

# Network Viewer
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/compute.networkViewer" \
    --member="serviceAccount:${GOOGLE_SA_ID}" \
    --condition=None

# VM Viewer
gcloud projects add-iam-policy-binding projects/${PROJECT} \
    --role="roles/compute.viewer" \
    --member="serviceAccount:${GOOGLE_SA_ID}" \
    --condition=None
```

> There are other prerequisite setup steps that can be found in the individual deployment folders
