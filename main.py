from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import boto3
from botocore.config import Config
import os
from datetime import datetime
app = FastAPI(title="Frozo 3D Gateway API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
RUNPOD_URL = os.getenv("RUNPOD_URL")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET", "furniture-models")
# Configure boto3 for R2 (Cloudflare-specific)
s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    ),
    region_name='auto'
)
@app.get("/")
async def root():
    return {"service": "Frozo 3D Gateway", "version": "1.0"}
@app.get("/health")
async def health():
    return {
        "gateway": "healthy",
        "runpod_url": RUNPOD_URL,
        "r2_configured": all([R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY])
    }
@app.post("/generate-3d")
async def generate_3d(file: UploadFile = File(...), class_id: int = 0):
    try:
        # Read file
        file_content = await file.read()
        
        # Send to RunPod
        files = {'file': (file.filename, file_content, 'application/octet-stream')}
        data = {'class_id': str(class_id)}
        
        response = requests.post(f"{RUNPOD_URL}/infer", files=files, data=data, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(500, f"RunPod error: {response.status_code}")
        
        # Upload to R2 with correct config
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_{timestamp}.glb"
        
        try:
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=filename,
                Body=response.content,
                ContentType='model/gltf-binary',
                ACL='public-read'  # Make publicly readable
            )
        except Exception as e:
            raise HTTPException(500, f"R2 upload error: {str(e)}")
        
        # Public URL
        public_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{filename}"
        
        return {
            "success": True,
            "model_url": public_url,
            "filename": filename,
            "class_id": class_id
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
