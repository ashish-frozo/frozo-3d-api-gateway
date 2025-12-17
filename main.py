from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
app = FastAPI(title="Frozo 3D Gateway API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
RUNPOD_URL = os.getenv("RUNPOD_URL")
@app.get("/")
async def root():
    return {"service": "Frozo 3D Gateway", "version": "1.0"}
@app.get("/health")
async def health():
    return {"gateway": "healthy", "runpod_url": RUNPOD_URL}
@app.post("/generate-3d")
async def generate_3d(file: UploadFile = File(...), class_id: int = 0):
    try:
        file_content = await file.read()
        files = {'file': (file.filename, file_content, 'application/octet-stream')}
        data = {'class_id': str(class_id)}
        
        response = requests.post(f"{RUNPOD_URL}/infer", files=files, data=data, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(500, f"RunPod error: {response.status_code}")
        
        # Return GLB directly - no R2 needed!
        return Response(
            content=response.content,
            media_type="model/gltf-binary",
            headers={"Content-Disposition": "attachment; filename=model.glb"}
        )
        
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
