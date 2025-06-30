from fastapi import FastAPI

app = FastAPI()

@app.get("/convert")
async def convert(pycode: str):
    """
    Convert Python code to Cpp.
    """
    return {
        "message": "This endpoint is not implemented yet.",
    }
    

