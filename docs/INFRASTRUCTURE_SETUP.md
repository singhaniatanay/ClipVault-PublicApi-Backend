# ClipVault API - Manual Infrastructure Setup

This document outlines the Google Cloud infrastructure components that need to be created manually for the ClipVault Public API to function properly.

## **🏗️ Infrastructure Overview**

The ClipVault API requires the following Google Cloud components:

### **1. Google Cloud Pub/Sub Setup**

#### **Topics to Create:**
```bash
# Main topic for clip processing events
gcloud pubsub topics create clip-events

# Dead letter queue for failed messages  
gcloud pubsub topics create clip-events-dlq
```

#### **Subscriptions to Create:**
```bash
# Main subscription for AI workers
gcloud pubsub subscriptions create clip-events-ai-worker \
    --topic=clip-events \
    --dead-letter-topic=clip-events-dlq \
    --max-delivery-attempts=5 \
    --ack-deadline=600

# Dead letter subscription for monitoring failed messages
gcloud pubsub subscriptions create clip-events-dlq-monitor \
    --topic=clip-events-dlq
```

#### **IAM Permissions:**
```bash
# Get your project service account email (usually ends with @appspot.gserviceaccount.com)
PROJECT_ID=$(gcloud config get-value project)
SERVICE_ACCOUNT="your-app@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Pub/Sub Publisher role to API service
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/pubsub.publisher"

# Grant Pub/Sub Subscriber role for future worker services  
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/pubsub.subscriber"
```

### **2. Environment Variables Required**

Add these to your deployment environment (Cloud Run, etc.):

```bash
# Google Cloud Project
GOOGLE_CLOUD_PROJECT=your-project-id

# Pub/Sub Topics
PUBSUB_CLIP_EVENTS_TOPIC=clip-events
PUBSUB_CLIP_EVENTS_DLQ_TOPIC=clip-events-dlq

# Note: No GOOGLE_APPLICATION_CREDENTIALS needed for Cloud Run!
# Cloud Run automatically provides credentials via attached service account
```

### **3. Authentication Setup**

#### **For Cloud Run Deployment (Production):**

**Option A: Use Default Service Account (Simplest)**
```bash
# Grant permissions to the default Compute Engine service account
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Pub/Sub permissions to default service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${DEFAULT_SA}" \
    --role="roles/pubsub.publisher"
```

**Option B: Create Custom Service Account (Recommended)**
```bash
# Create dedicated service account for ClipVault API
gcloud iam service-accounts create clipvault-api \
    --display-name="ClipVault API Service Account" \
    --description="Service account for ClipVault API operations"

# Grant Pub/Sub permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:clipvault-api@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

# When deploying to Cloud Run, attach this service account:
gcloud run deploy clipvault-api \
    --service-account=clipvault-api@${PROJECT_ID}.iam.gserviceaccount.com \
    --other-deployment-flags...
```

#### **For Local Development:**

```bash
# Install Google Cloud SDK if not already installed
# https://cloud.google.com/sdk/docs/install

# Authenticate with your Google account (DO NOT use service account keys)
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Set up Application Default Credentials for local development
gcloud auth application-default login

# Verify authentication
gcloud auth list
```

**⚠️ IMPORTANT**: 
- **NEVER commit service account key files** to Git
- **NEVER set GOOGLE_APPLICATION_CREDENTIALS** in production environment variables
- Cloud Run automatically provides credentials via the attached service account
- Use Application Default Credentials (ADC) for both local and production

### **4. How Authentication Works**

#### **In Cloud Run (Production):**
1. Cloud Run service has an attached service account
2. Google Cloud libraries automatically detect the runtime environment
3. Authentication happens transparently using the attached service account
4. No environment variables or key files needed!

#### **In Local Development:**
1. `gcloud auth application-default login` sets up local credentials
2. Google Cloud libraries automatically find and use these credentials
3. Same code works in both environments without changes

#### **In the Code:**
```python
# This works in both local development and Cloud Run!
from google.cloud import pubsub_v1

# No explicit credentials needed - ADC handles it automatically
publisher = pubsub_v1.PublisherClient()
```

### **5. Verification Steps**

After creating the infrastructure, verify setup:

```bash
# List topics
gcloud pubsub topics list

# List subscriptions  
gcloud pubsub subscriptions list

# Test publishing a message
gcloud pubsub topics publish clip-events --message='{"test": "message"}'

# Test receiving the message
gcloud pubsub subscriptions pull clip-events-ai-worker --auto-ack --limit=1
```

### **6. Local Development Setup**

For local development, authentication is handled via Application Default Credentials:

```bash
# Make sure you're authenticated (already covered in section 3)
gcloud auth application-default login

# Set environment variables for local development
export GOOGLE_CLOUD_PROJECT="your-project-id"
export PUBSUB_CLIP_EVENTS_TOPIC="clip-events"
export PUBSUB_CLIP_EVENTS_DLQ_TOPIC="clip-events-dlq"

# Your Python code will automatically work with these credentials!
```

### **7. Production Deployment Notes**

- **Service Account**: Attach service account to Cloud Run service during deployment
- **No Key Files**: Never use service account key files in production
- **Environment Variables**: Only set topic names, not credentials
- **Workload Identity**: Use for GKE deployments (if applicable)
- **Monitoring**: Set up Cloud Monitoring alerts for failed message processing
- **Scaling**: Default Pub/Sub settings should handle expected load

### **9. Security Considerations**

- **Use Application Default Credentials**: Never use service account key files
- **Attach Service Accounts**: Use Cloud Run's built-in service account attachment
- **Least-Privilege IAM**: Only grant `roles/pubsub.publisher` (not broader permissions)
- **Enable Audit Logging**: Monitor Pub/Sub operations for security events
- **VPC Security**: Consider VPC-native networking for internal communication
- **Environment Variables**: Only store non-sensitive configuration (topic names, project ID)
- **No Secrets in Git**: Never commit credentials, keys, or sensitive data

---

## **✅ Checklist**

Before proceeding with PUB-013 implementation:

### Infrastructure Setup:
- [✅] Google Cloud project is set up and accessible
- [✅] Pub/Sub topics created (`clip-events`, `clip-events-dlq`)
- [✅] Subscriptions created (`clip-events-ai-worker`, `clip-events-dlq-monitor`)

### Authentication & Permissions:
- [✅] Service account created (or using default)
- [✅] IAM permissions granted (`roles/pubsub.publisher`)
- [✅] Local development authenticated (`gcloud auth application-default login`)
- [✅] No service account key files created or stored

### Environment & Testing:
- [✅] Environment variables configured (project ID, topic names)
- [✅] Verification tests passed (publish/subscribe test messages)
- [✅] Cloud Run deployment plan includes service account attachment

### **10. Cost Estimation**

**Google Cloud Pub/Sub Pricing (approximate):**
- Message publishing: $0.04 per million messages
- Message delivery: $0.04 per million messages  
- Storage: $0.27 per GB-month for retained messages

**Expected costs for MVP:**
- 1,000 clips/day = ~30k messages/month
- Estimated cost: ~$0.12/month for Pub/Sub

---

## **🔗 Next Steps**

1. Complete this infrastructure setup using the commands above
2. Implement PUB-013 (Pub/Sub service)
3. Implement API-ROUTE-008 (clips endpoint)

---

**✅ Summary of Key Changes:**
- **No service account keys**: Use Application Default Credentials instead
- **Cloud Run authentication**: Automatic via attached service account
- **Local development**: Use `gcloud auth application-default login`
- **Environment variables**: Only non-sensitive configuration (topic names, project ID)

**Note**: This approach follows Google Cloud security best practices and replaces the need for IaC-002 Terraform infrastructure automation. 