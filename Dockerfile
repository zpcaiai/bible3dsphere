FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps.
# NOTE: ffmpeg, libreoffice-impress and poppler-utils are large. They are only
# needed by the offline film/video/pptx-export scripts (biblical_film_studio.py,
# video_studio_server.py, python-pptx PDF conversion). If the runtime API does
# not perform those conversions on HF, remove them to cut image size. Left in
# for now since usage could not be fully confirmed. espeak-ng + fonts-wqy-microhei
# are needed for edge-tts / CJK rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fonts-wqy-microhei libreoffice-impress poppler-utils espeak-ng curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend-requirements.txt
# Install CPU-only torch FIRST from the PyTorch CPU index so the default CUDA
# build (multi-GB) is never pulled. sentence-transformers then sees torch as
# already satisfied.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /app/backend-requirements.txt

# --- Pre-bake large vector/metadata files (~260MB) so cold starts skip the
# per-boot CDN download. main.py's _download_hf_data_files() checks ROOT_DIR
# (=/app) and skips any file already present at >= its min size. Kept BEFORE
# `COPY backend/` so backend code changes don't bust this cached layer.
# Best-effort: if a fetch fails at build time, the runtime downloader still
# fetches it on boot.
ARG VECTOR_DATA_BASE_URL=https://cdn.holiness.uk/npy
RUN set -eux; \
    for f in bible_bilingual_metadata.pkl bible_bilingual_vector_cuv.npy bible_bilingual_vector_esv.npy; do \
        curl -fSL --retry 3 --retry-delay 2 "${VECTOR_DATA_BASE_URL}/${f}" -o "/app/${f}" \
        || { echo "prebake: ${f} failed at build, will fetch at runtime"; rm -f "/app/${f}"; }; \
    done

COPY backend/ /app/backend/
COPY bible/ /app/bible/
COPY query_emotion_verses.py /app/query_emotion_verses.py
COPY web_emotion_query.py /app/web_emotion_query.py
COPY emotion_features_map.json /app/emotion_features_map.json
COPY emotion_exemplar_verse_matches.json /app/emotion_exemplar_verse_matches.json
COPY emotion_sphere_layout.json /app/emotion_sphere_layout.json
COPY emotion_feature_embedding_cache.json /app/emotion_feature_embedding_cache.json

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860
WORKDIR /app/backend

# Liveness check against the app's health endpoint (no DB dependency).
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:7860/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
