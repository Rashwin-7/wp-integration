from fastapi import FastAPI

# Create FastAPI app
app = FastAPI()

# Create a route (endpoint)
@app.get("/")
def read_root():
    return {"message": "Hello World 🚀"}