FROM node:18-alpine AS frontend-builder
WORKDIR /app/emotion-sphere-ui
COPY emotion-sphere-ui/package*.json ./
RUN npm install
COPY emotion-sphere-ui/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt /app/backend-requirements.txt
RUN pip install --no-cache-dir -r /app/backend-requirements.txt

COPY --from=frontend-builder /app/emotion-sphere-ui/dist /app/emotion-sphere-ui/dist
COPY backend/ /app/backend/
COPY query_emotion_verses.py /app/query_emotion_verses.py
COPY web_emotion_query.py /app/web_emotion_query.py
COPY emotion_features_map.json /app/emotion_features_map.json
COPY emotion_exemplar_verse_matches.json /app/emotion_exemplar_verse_matches.json
COPY emotion_sphere_layout.json /app/emotion_sphere_layout.json
COPY emotion_feature_embedding_cache.json /app/emotion_feature_embedding_cache.json

EXPOSE 7860
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
