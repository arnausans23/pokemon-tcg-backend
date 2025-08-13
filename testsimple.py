from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"mensaje": "Funciona!"}

if __name__ == "__main__":
    print("Iniciando servidor de prueba...")
    uvicorn.run(app, host="127.0.0.1", port=8888)