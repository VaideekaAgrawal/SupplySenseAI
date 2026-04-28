#!/usr/bin/env bash
# SupplySense AI — Google Cloud Run Deployment Script
# Usage: bash deploy.sh

set -euo pipefail

PROJECT_ID="project-c233b50f-eaa9-44da-9cb"
REGION="us-central1"
BACKEND_SERVICE="supplysense-api"
GEMINI_API_KEY="AIzaSyDR35Y0bHCBvxWR3zmJRZOLW2xifNjQ_Zg"

echo "=== SupplySense AI — Cloud Run Deployment ==="

# 1. Authenticate (if not already)
echo "Step 1: Checking authentication..."
if ! gcloud auth list --format="value(account)" 2>/dev/null | head -1 | grep -q '@'; then
    echo "Please authenticate with Google Cloud:"
    gcloud auth login
fi

# 2. Set project
echo "Step 2: Setting project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# 3. Enable required APIs
echo "Step 3: Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 4. Deploy backend to Cloud Run (source-based deploy)
echo "Step 4: Deploying backend to Cloud Run..."
cd backend
gcloud run deploy "$BACKEND_SERVICE" \
    --source=. \
    --region="$REGION" \
    --allow-unauthenticated \
    --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,GEMINI_MODE=real,CORS_ORIGINS=*,DISRUPTION_MODE=real" \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=300
cd ..

# 5. Get backend URL
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format="value(status.url)")
echo ""
echo "=== Backend deployed at: $BACKEND_URL ==="

# 6. Update frontend .env.local with production backend URL
echo "Step 6: Updating frontend config..."
echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" > chainguard/.env.local

echo ""
echo "=== Deployment Complete ==="
echo "Backend API:  $BACKEND_URL"
echo "API Docs:     $BACKEND_URL/docs"
echo "Health Check: $BACKEND_URL/health"
echo ""
echo "To deploy the frontend, run:"
echo "  cd chainguard && npx next build && npx next start"
echo "Or deploy to Vercel: cd chainguard && npx vercel"
