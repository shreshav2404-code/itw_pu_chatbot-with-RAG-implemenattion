# PU Assist – frontend (Streamlit, Docker, Portainer)

The students' chat page. It has **no AI inside** – every question is sent over HTTP to the **backend API**
(`03_backend_api.ipynb`, running on the Data Lab GPU), and the answer is shown with its sources.

```
student's browser ──► this container (Streamlit, port 8501) ──POST /ask──► notebook 03 (FastAPI on the H200)
```

Features: chat history, text questions, photo of a notice/timetable (📎 in the chat box), voice questions
(microphone recorder in the sidebar), clickable sources, backend online/busy status, "New conversation".

## Settings (environment variables)

| Variable | Example | From |
|---|---|---|
| `BACKEND_URL` | `http://10.0.0.12:8000` | notebook 03, step 7 (an address of the GPU machine + port) |
| `PU_API_KEY` | `kX3…` | notebook 03, step 2 |
| `REQUEST_TIMEOUT` | `300` | optional, seconds to wait for an answer |
| `APP_PASSWORD` | `pu-assist-2026` | optional: visitors must type it before they can chat – set it whenever the page is reachable from the internet |

**Without Portainer:** notebook 03, step 9 runs this same page on the hub and opens a public
Cloudflare quick-tunnel link (`https://….trycloudflare.com`) protected by `APP_PASSWORD` – handy for demos.

## Try it on your laptop (optional)

```bash
pip install -r requirements.txt
```

Set `BACKEND_URL` and `PU_API_KEY` (PowerShell: `$env:BACKEND_URL="http://…:8000"`), then:

```bash
streamlit run app.py
```

It opens at http://localhost:8501. It only gets answers if your laptop can reach the backend address.

## Deploy on Data Lab with Portainer

**1. Build the image** (needs Docker Desktop running), in this folder:

```bash
docker build -t pu-assist-frontend:1.0 .
```

**2. Get the image into Portainer** – pick what your Data Lab allows:

- **Docker Hub:** `docker tag pu-assist-frontend:1.0 <your-dockerhub-user>/pu-assist-frontend:1.0`, then
  `docker push <your-dockerhub-user>/pu-assist-frontend:1.0`, and use that image name in Portainer.
- **Upload in Portainer:** `docker save pu-assist-frontend:1.0 -o pu-assist-frontend.tar`, then
  Portainer → **Images → Import** → choose the `.tar` file.
- **Build in Portainer:** Portainer → **Images → Build a new image** → upload this folder as a `.tar`/`.zip`
  (Dockerfile at its root) → name it `pu-assist-frontend:1.0`.

**3. Start the backend:** on JupyterHub run notebooks 01 → (02) → shut down 02 → **03 Run All**. Note the
`PU_API_KEY` (step 2) and the `BACKEND_URL` candidates (step 7). Keep notebook 03 running.

**4. Create the container** – either:

- **Stacks → Add stack → Web editor**, paste `docker-compose.yml`, and add the environment variables
  `FRONTEND_IMAGE`, `BACKEND_URL`, `PU_API_KEY` at the bottom → **Deploy the stack**; or
- **Containers → Add container**: image `pu-assist-frontend:1.0`, publish port **8501**, add the env variables
  `BACKEND_URL` and `PU_API_KEY`, restart policy *Unless stopped* → **Deploy**.

**5. Check the connection:** Portainer → the container → **Console** → `sh`, then:

```bash
python -c "import os,urllib.request;print(urllib.request.urlopen(os.environ['BACKEND_URL']+'/health').read())"
```

`{"status":"ok",…}` means the frontend can reach the GPU notebook. Then open the container's published port
(8501) in the browser – Data Lab tells you the public address.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sidebar says **offline** | Notebook 03 is not running, or `BACKEND_URL` is not reachable from the container – try the other addresses from notebook 03 step 7, or ask Data Lab which hostname/port containers can use to reach Compute |
| "PU_API_KEY does not match" | Copy the key from notebook 03 step 2 again (it changes when the hub forgets `api_key.txt`; paste a fixed key into notebook 03 to avoid that) |
| Answers take long / "waiting in the queue" | One GPU answers one question at a time – normal for a single notebook backend |
| Page loads without styling behind a sub-path | Set the env variable `STREAMLIT_SERVER_BASE_URL_PATH` to that path |
