# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

try:
    from app.main import app
    import uvicorn
    
    print("FastAPI app loaded successfully!")
    print("Starting server on http://127.0.0.1:8000")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
