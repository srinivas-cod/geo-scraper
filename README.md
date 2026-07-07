Google Maps Business Extractor
A robust, fully automated tool that scrapes business data from Google Maps using **FastAPI** and **Playwright**. It includes a simple, user-friendly web interface that makes extracting data as easy as typing a search keyword.

Features
1. One-Click Web UI Simply enter your search query (e.g., "Dentists in Avadi") and hit start.
2. Automated Scraping -Uses Playwright to open a headless/visible Chromium browser, scroll through the results, and extract rich business details.
3. Asynchronous Backend- Powered by FastAPI, allowing background processing without timing out your browser.
4. Direct Downloads - Automatically downloads the completed data as a perfectly formatted `.csv` file once the extraction finishes.

Data Extracted
For every business found, the tool extracts:
- Business Name
- Category (e.g., Restaurant, Hospital)
- Rating & Total Reviews
- Full Address & Phone Number
- Website URL & Operating Hours
- Exact Latitude & Longitude
- Direct Google Maps Link



 🛠 Setup Instructions

1. Prerequisites
- Python 3.10+ installed
- Windows OS (Tested)

2. Installation
Open your terminal (Command Prompt or PowerShell) inside the project folder and run the following commands:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# Install the required Python packages
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install

🚀 How to Run

1. Start the Server
   Ensure your virtual environment is activated, then start the FastAPI server:
   bash
   uvicorn api:app --reload --host 0.0.0.0 --port 8080
   

2. Open the Web UI
   Open your web browser and go to:
   👉 http://localhost:8080

3. Extract Data
   - Type your desired search keyword (e.g., "Mechanics in Chennai").
   - Click Start Extraction.
   - The browser will start scraping in the background. Once it finishes, the CSV file will download automatically!



 API Endpoints (For Developers)
If you prefer to interact with the API directly (or via Swagger), visit `http://localhost:8080/docs`.

- `POST /extract`: Start a background scraping job by providing a `{"keyword": "..."}` JSON payload. Returns a `job_id`.
- `GET /results/{job_id}`: Poll the status of the scraping job.
- `GET /download/{job_id}/{file_type}`: Download the finished data. `file_type` can be `csv`, `excel`, or `json`.
