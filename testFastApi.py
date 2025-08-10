# test_fastapi.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>Test</title>
        </head>
        <body>
            <h1>FastAPI is working!</h1>
        </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run("testFastApi:app", host="0.0.0.0", port=8000, reload=True)