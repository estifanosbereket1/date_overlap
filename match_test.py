import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # silence TensorFlow logs

from deepface import DeepFace

def get_embedding(img_path):
    result = DeepFace.represent(
        img_path=img_path,
        model_name="ArcFace",
        enforce_detection=True
    )
    embedding = result[0]["embedding"]
    return embedding

def compare_embeddings(emb1, emb2):
    import numpy as np
    # Convert to numpy arrays
    a = np.array(emb1)
    b = np.array(emb2)
    # Cosine distance formula
    cosine_distance = 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return round(cosine_distance, 4)

# Extract embeddings
print("Extracting embeddings...")
emb_a1 = get_embedding("a1.jpg")
emb_a2 = get_embedding("a2.jpg")
emb_b  = get_embedding("m1.jpg")

print(f"Embedding length: {len(emb_a1)} numbers")
print(f"First 5 numbers of a1's embedding: {emb_a1[:5]}")
print()

# Compare them manually
dist_same    = compare_embeddings(emb_a1, emb_a2)
dist_diff    = compare_embeddings(emb_a1, emb_b)

print(f"Same person distance:      {dist_same}")
print(f"Different person distance: {dist_diff}")

THRESHOLD = 0.68
print()
print("Same person?",      dist_same < THRESHOLD)
print("Different person?", dist_diff > THRESHOLD)