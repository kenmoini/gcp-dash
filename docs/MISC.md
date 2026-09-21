# MISC

```bash

# Give GSA Access to the bucket
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} --member="serviceAccount:${GOOGLE_SA_ID}" --role="roles/storage.objectViewer"

```