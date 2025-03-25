# fastapi-quickstart

## Run for development (with reload, no ssl)
- Remember to use the correct `--port` argument 
- Uvicorn with `--reload` cannot be used with ssl, so it's easier to use http for development
- Run:
`uvicorn main:app --host 0.0.0.0 --port 5000 --reload` 


## Run for production (with ssl) 
- Set the correct port in the script or do a better config using `dotenv`
- Run: `python main.py`
