"""Runner: `python main.py` from the api/ directory starts uvicorn."""
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("API_RELOAD", "")),
    )


if __name__ == "__main__":
    main()
