from qdrant_client import QdrantClient
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.models import VectorParams, Distance, PointStruct, NearestQuery
import hashlib
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class VectorManager:
    def __init__(self):
        # Модель для векторизации (384 измерения)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        # Храним данные локально в папке проекта
        self.qdrant = QdrantClient(path="./qdrant_data")
        self.collection_name = "company_docs"
        self._init_collection()

    def _init_collection(self):
        try:
            collections = self.qdrant.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"Ошибка инициализации Qdrant: {e}")

    def search(self, query: str, limit: int = 3):
        vector = self.embeddings.embed_query(query)
        # Используем простой scroll для поиска всех документов
        all_points = self.qdrant.scroll(
            collection_name=self.collection_name,
            limit=100,
            with_payload=True,
            with_vectors=True
        )[0]
        
        # Считаем косинусное сходство вручную
        if not all_points:
            return []
            
        vectors = [point.vector for point in all_points]
        similarities = cosine_similarity([vector], vectors)[0]
        
        # Получаем топ-k самых похожих
        top_indices = np.argsort(similarities)[-limit:][::-1]
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.3:  # Порог схожести
                results.append(all_points[idx].payload)
        
        return results

    def add_doc(self, text: str, metadata: dict = None):
        stable_id = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        vector = self.embeddings.embed_query(text)
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=stable_id, vector=vector, payload={"text": text, **(metadata or {})})]
        )

# Глобальный объект для использования в инструментах
vector_db = VectorManager()