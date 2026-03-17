import os
import uuid

from flask import Flask, jsonify, request, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from backend.database import (
    delete_image,
    get_all_images,
    get_image_by_id,
    get_image_count,
    init_db,
    insert_image,
)
from backend.embeddings import (
    EMBEDDING_DIM,
    generate_media_embedding_batch,
    generate_image_embedding,
    generate_media_caption,
    generate_query_embedding,
    setup_gemini,
    _media_type,
)
from backend.vector_store import (
    add_embedding,
    load_or_create_index,
    save_index,
    search_similar,
)

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024  # 128 MB

UPLOAD_FOLDER = "uploads"
# All supported media types per Gemini Embedding model
ALLOWED_EXTENSIONS = {
    # Images
    "jpg", "jpeg", "png", "webp", "gif", "bmp",
    # Videos (up to 120 seconds)
    "mp4", "mov", "avi", "mkv", "webm",
    # Audio
    "mp3", "wav", "ogg", "m4a", "flac", "aac",
    # Documents
    "pdf", "txt", "md", "json", "csv"
}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("data", exist_ok=True)

init_db()
setup_gemini()

# Load FAISS once at startup
_faiss_index, _faiss_ids = load_or_create_index(EMBEDDING_DIM)


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Serve frontend ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(os.path.abspath(UPLOAD_FOLDER), filename)


@app.route("/1.json")
def serve_test_json():
    return send_from_directory(os.path.abspath('.'), '1.json')


@app.route("/favicon.ico")
def favicon():
    return "", 204  # No content - browser will ignore


@app.route("/test-network.html")
def test_network():
    """Serve test page with static JSON data."""
    return """<!DOCTYPE html>
<html>
<head>
  <title>Network Test</title>
  <style>
    body { margin: 0; background: #0f1117; color: #e8eaf6; font-family: sans-serif; }
    #graph { width: 100vw; height: 100vh; }
    .info { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 8px; z-index: 100; }
    .error { color: #f05454; }
    .success { color: #4caf7d; }
  </style>
</head>
<body>
  <div class="info">
    <h3>Network Test</h3>
    <p id="status">Loading libraries...</p>
  </div>
  <div id="graph"></div>
  
  <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
  <script src="https://unpkg.com/3d-force-graph@1.73.0/dist/3d-force-graph.min.js"></script>
  <script>
    // Check libraries loaded
    if (typeof THREE === 'undefined' || typeof ForceGraph3D === 'undefined') {
      document.getElementById('status').innerHTML = '<span class="error">Libraries failed to load!</span>';
    } else {
      document.getElementById('status').textContent = 'Loading data...';
      
      fetch('/1.json')
        .then(r => r.json())
        .then(data => {
          document.getElementById('status').innerHTML = 
            `<span class="success">Nodes: ${data.nodes.length}, Edges: ${data.edges.length}</span>`;
          
          // Set initial positions using fx, fy, fz
          data.nodes.forEach(n => {
            n.fx = n.x;
            n.fy = n.y;
            n.fz = n.z;
          });
          
          const graphData = {
            nodes: data.nodes,
            links: data.edges.map(e => ({
              source: e.source,
              target: e.target,
              similarity: e.similarity
            }))
          };
          
          const Graph = ForceGraph3D({ controlType: 'orbit' })(document.getElementById('graph'))
            .graphData(graphData)
            .backgroundColor('#0f1117')
            .nodeLabel('name')
            .nodeColor(() => '#5b6ef5')
            .linkWidth(l => (l.similarity || 0.5) * 3)
            .linkColor(() => 'rgba(123, 140, 255, 0.5)');
          
          Graph.warmupTicks(80);
          Graph.cooldownTicks(50);
          
          // Release fixed positions after stabilization
          setTimeout(() => {
            data.nodes.forEach(n => {
              n.fx = undefined;
              n.fy = undefined;
              n.fz = undefined;
            });
          }, 1000);
        })
        .catch(e => {
          document.getElementById('status').innerHTML = '<span class="error">Error: ' + e.message + '</span>';
          console.error(e);
        });
    }
  </script>
</body>
</html>"""


# ── API: Upload ────────────────────────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload():
    """
    Upload and embed media files (images, videos, audio, PDFs, text) with batch processing.
    Failed files are silently skipped - only successful uploads are returned.
    """
    global _faiss_index, _faiss_ids

    files = request.files.getlist("files") or request.files.getlist("images")
    if not files:
        return jsonify({"results": []})

    # First pass: save files and collect valid ones
    valid_files = []
    for file in files:
        if not file or not allowed(file.filename):
            print(f"[UPLOAD] Skipping {file.filename}: not allowed")
            continue
        
        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit(".", 1)[-1].lower()
        save_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.{ext}")
        file.save(save_path)
        
        media_type = _media_type(save_path)
        print(f"[UPLOAD] Saved {file.filename} as {media_type}: {save_path}")
        
        # Get dimensions for images
        width, height = None, None
        if media_type == "image":
            try:
                img = Image.open(save_path)
                img.verify()
                img = Image.open(save_path)
                width, height = img.size
            except Exception as e:
                print(f"[UPLOAD] Invalid image {file.filename}: {e}")
                # Invalid image, delete and skip
                if os.path.exists(save_path):
                    os.remove(save_path)
                continue
        
        file_size = os.path.getsize(save_path)
        
        valid_files.append({
            "file_id": file_id,
            "save_path": save_path,
            "filename": file.filename,
            "ext": ext,
            "media_type": media_type,
            "width": width,
            "height": height,
            "file_size": file_size
        })
    
    if not valid_files:
        print("[UPLOAD] No valid files to process")
        return jsonify({"results": []})
    
    # Second pass: batch embed all valid files
    paths = [f["save_path"] for f in valid_files]
    print(f"[UPLOAD] Embedding {len(paths)} files: {paths}")
    
    try:
        embeddings = generate_media_embedding_batch(paths)
        print(f"[UPLOAD] Got {len(embeddings)} embeddings, {sum(1 for e in embeddings if e is not None)} successful")
    except Exception as e:
        print(f"[UPLOAD] Embedding batch failed: {e}")
        embeddings = [None] * len(paths)
    
    # Process results
    results = []
    for i, vf in enumerate(valid_files):
        embedding = embeddings[i] if i < len(embeddings) else None
        
        if embedding is None:
            print(f"[UPLOAD] No embedding for {vf['filename']}, deleting")
            # Failed to embed, delete and skip silently
            if os.path.exists(vf["save_path"]):
                os.remove(vf["save_path"])
            continue
        
        try:
            # Generate caption/description (best effort)
            caption = generate_media_caption(vf["save_path"])
            print(f"[UPLOAD] Caption for {vf['filename']}: {caption[:50]}...")
            
            # Add to vector store
            _faiss_index, _faiss_ids = add_embedding(
                _faiss_index, _faiss_ids, embedding, vf["file_id"]
            )
            
            # Save to database
            insert_image(
                image_id=vf["file_id"],
                file_path=vf["save_path"],
                original_name=vf["filename"],
                caption=caption,
                file_size=vf["file_size"],
                width=vf["width"],
                height=vf["height"],
                media_type=vf["media_type"],
            )
            
            results.append({
                "name": vf["filename"],
                "status": "ok",
                "file_id": vf["file_id"],
                "media_type": vf["media_type"],
                "caption": caption,
                "url": f"/uploads/{vf['file_id']}.{vf['ext']}",
                "width": vf["width"],
                "height": vf["height"],
            })
        except Exception as e:
            print(f"[UPLOAD] Error processing {vf['filename']}: {e}")
            # Any error, delete and skip silently
            if os.path.exists(vf["save_path"]):
                os.remove(vf["save_path"])
            continue
    
    # Save index once after all successful additions
    if results:
        save_index(_faiss_index, _faiss_ids)
    
    print(f"[UPLOAD] Returning {len(results)} successful results")
    return jsonify({"results": results})


# ── API: Gallery ───────────────────────────────────────────────────────────────
@app.route("/api/images", methods=["GET"])
def get_images():
    images = get_all_images()
    for img in images:
        fp = img["file_path"]
        img["url"] = "/" + fp.replace("\\", "/")
        img["exists"] = os.path.exists(fp)
        # Default media_type for old records
        if not img.get("media_type"):
            img["media_type"] = "image"
    return jsonify({"images": images, "total": len(images)})


# ── API: Text search ─────────────────────────────────────────────────────────--
@app.route("/api/search/text", methods=["POST"])
def search_text():
    try:
        data = request.get_json(force=True)
        query = (data.get("query") or "").strip()
        top_k = int(data.get("top_k", 12))
        min_score = float(data.get("min_score", 0.10))

        if not query:
            return jsonify({"error": "Query is required"}), 400
        if _faiss_index.ntotal == 0:
            return jsonify({"results": [], "message": "No images indexed yet"})

        q_emb = generate_query_embedding(query)
        if q_emb is None:
            return jsonify({"error": "Failed to generate query embedding. Check API key."}), 500
        
        print(f"[SEARCH] Query: '{query}', Index size: {_faiss_index.ntotal}, Embeddings: {len(_faiss_ids)}")
        
        # Search with lower threshold to get more candidates
        hits = search_similar(_faiss_index, _faiss_ids, q_emb, top_k=top_k, min_score=min_score)
        print(f"[SEARCH] Found {len(hits)} hits above threshold {min_score}")
        
        # Sort by score descending
        hits = sorted(hits, key=lambda x: x["score"], reverse=True)
        
        return jsonify({
            "results": _enrich_hits(hits),
            "indexed_count": _faiss_index.ntotal,
            "query": query
        })
    except Exception as e:
        import traceback
        print(f"[ERROR] search_text: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Image-to-image search ─────────────────────────────────────────────────
@app.route("/api/search/image", methods=["POST"])
def search_image():
    file = request.files.get("image")
    top_k = int(request.form.get("top_k", 8))

    if not file or not allowed(file.filename):
        return jsonify({"error": "Valid image file required"}), 400
    if _faiss_index.ntotal == 0:
        return jsonify({"results": [], "message": "No images indexed yet"})

    tmp_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[-1].lower()
    tmp_path = os.path.join(UPLOAD_FOLDER, f"_tmp_{tmp_id}.{ext}")
    file.save(tmp_path)

    try:
        q_emb = generate_image_embedding(tmp_path)
        if q_emb is None:
            return jsonify({"error": "Failed to process image"}), 500
        hits = search_similar(_faiss_index, _faiss_ids, q_emb, top_k=top_k)
        results = _enrich_hits(hits)
        
        return jsonify({"results": results})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/api/search/network", methods=["POST"])
def search_network():
    """Get network data for a list of image IDs (for search results visualization)."""
    data = request.get_json(force=True)
    image_ids = data.get("image_ids", [])
    
    if len(image_ids) < 2:
        return jsonify({"network": {"nodes": [], "edges": []}})
    
    network_data = get_search_network(image_ids)
    return jsonify({"network": network_data})


def get_search_network(result_ids):
    """Get network data for search results showing their interconnections."""
    import numpy as np
    
    if len(result_ids) < 2:
        return {"nodes": [], "edges": []}
    
    # Get embeddings for result images
    id_to_idx = {img_id: idx for idx, img_id in enumerate(_faiss_ids)}
    indices = [id_to_idx[rid] for rid in result_ids if rid in id_to_idx]
    
    if len(indices) < 2:
        return {"nodes": [], "edges": []}
    
    # Get embeddings
    embeddings = np.vstack([_faiss_index.reconstruct(i) for i in indices])
    emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    sim_matrix = np.dot(emb_norm, emb_norm.T)
    
    # Build nodes
    all_meta = {img["image_id"]: img for img in get_all_images()}
    nodes = []
    for i, idx in enumerate(indices):
        img_id = _faiss_ids[idx]
        meta = all_meta.get(img_id, {})
        nodes.append({
            "id": str(img_id),
            "name": str(meta.get("original_name", img_id[:8])) if meta else str(img_id[:8]),
            "url": "/" + meta.get("file_path", "").replace("\\", "/") if meta else "",
            "caption": str(meta.get("caption", "")) if meta else "",
            "score": 100,
            "is_result": True
        })
    
    # Build edges between results
    edges = []
    for i in range(len(indices)):
        for j in range(i + 1, len(indices)):
            sim = float(sim_matrix[i, j])
            if sim > 0.4:
                edges.append({
                    "source": str(_faiss_ids[indices[i]]),
                    "target": str(_faiss_ids[indices[j]]),
                    "similarity": round(sim, 3)
                })
    
    return {"nodes": nodes, "edges": edges}


# ── API: Delete image ──────────────────────────────────────────────────────────
@app.route("/api/images/<image_id>", methods=["DELETE"])
def delete(image_id):
    global _faiss_index, _faiss_ids

    meta = get_image_by_id(image_id)
    if not meta:
        return jsonify({"error": "Not found"}), 404

    delete_image(image_id)
    if os.path.exists(meta["file_path"]):
        os.remove(meta["file_path"])

    # Rebuild FAISS index from remaining files on disk
    from backend.vector_store import create_index
    import numpy as np, faiss

    new_index = create_index(EMBEDDING_DIM)
    new_ids: list[str] = []
    
    # Re-embed all remaining files in batches
    all_images = get_all_images()
    paths = [img["file_path"] for img in all_images if os.path.exists(img["file_path"])]
    valid_images = [img for img in all_images if os.path.exists(img["file_path"])]
    
    embeddings = generate_media_embedding_batch(paths)
    
    for img, emb in zip(valid_images, embeddings):
        if emb is not None:
            vec = np.array([emb], dtype=np.float32)
            faiss.normalize_L2(vec)
            new_index.add(vec)
            new_ids.append(img["image_id"])

    save_index(new_index, new_ids)
    _faiss_index, _faiss_ids = new_index, new_ids

    return jsonify({"ok": True})


# ── API: Stats ─────────────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify({
        "total_images": get_image_count(),
        "indexed_vectors": _faiss_index.ntotal,
    })


# ── API: Network graph data ────────────────────────────────────────────────────
@app.route("/api/network", methods=["GET"])
def network_data():
    """
    Return 3D network with multiple embedding-based grouping approaches.
    
    Methods:
    - neighbor: Each node colored by its single most similar match
    - high_sim: Connected components of >75% similarity (tight clusters)
    - embedding_pca: Cluster in 3072-dim embedding space using PCA reduction
    - similarity_tiers: 6 tiers based on average similarity to all others
    - dominant_theme: Group by most common words in captions (if available)
    """
    import traceback
    import os
    
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    cluster_method = request.args.get('cluster', 'neighbor')
    
    # Descriptions for each method
    descriptions = {
        'neighbor': 'Each image is colored based on its single most similar match. Creates visual "pairs" or "chains" of related images.',
        'high_sim': 'Only images with >75% similarity are grouped. Creates tight, highly similar clusters. Isolated images remain ungrouped (gray).',
        'embedding_pca': 'Clusters formed directly in the 3072-dim embedding space, reduced via PCA. Groups images with similar semantic meaning.',
        'similarity_tiers': 'Images ranked by average similarity to all others, divided into 6 tiers (blue=most connected, red=most unique).',
        'dominant_theme': 'Groups by analyzing caption keywords. Images with similar described content are colored alike.'
    }
    
    try:
        if _faiss_index.ntotal == 0:
            return jsonify({"nodes": [], "edges": [], "description": "", "message": "No images indexed yet"})
        
        if _faiss_index.ntotal == 1:
            return jsonify({"nodes": [], "edges": [], "description": "", "message": "Need at least 2 images"})
        
        import numpy as np
        from sklearn.decomposition import PCA
        from sklearn.cluster import KMeans
        
        n_total = _faiss_index.ntotal
        embeddings = np.vstack([_faiss_index.reconstruct(i) for i in range(n_total)])
        
        # Normalize for similarity
        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        sim_matrix = np.dot(emb_norm, emb_norm.T)
        
        # Build edges (for visualization)
        edges = []
        for i in range(n_total):
            for j in range(i + 1, n_total):
                sim = float(sim_matrix[i, j])
                if sim > 0.5:
                    edges.append({
                        "source": str(_faiss_ids[i]),
                        "target": str(_faiss_ids[j]),
                        "similarity": round(sim, 3)
                    })
                    if len(edges) >= 500:
                        break
            if len(edges) >= 500:
                break
        
        # PCA for 3D visualization coords
        if n_total >= 3:
            coords_3d = PCA(n_components=3, random_state=42).fit_transform(embeddings)
        else:
            coords_3d = np.random.randn(n_total, 3) * 20
        
        coords_min, coords_max = coords_3d.min(axis=0), coords_3d.max(axis=0)
        coords_range = coords_max - coords_min
        coords_range[coords_range == 0] = 1
        coords_3d = (coords_3d - coords_min) / coords_range * 100 - 50
        
        # Color palette
        colors = ["#5b6ef5", "#f5a623", "#4caf7d", "#f05454", "#9c27b0", "#00bcd4", "#ffeb3b", "#795548"]
        gray = "#6b7280"
        
        # Apply selected clustering method
        if cluster_method == 'neighbor':
            node_colors = []
            for i in range(n_total):
                sims = sim_matrix[i].copy()
                sims[i] = -1
                best_match = np.argmax(sims)
                node_colors.append(colors[best_match % len(colors)])
                
        elif cluster_method == 'high_sim':
            # Connected components at 75% threshold
            parent = list(range(n_total))
            def find(x):
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]
            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py
            
            for i in range(n_total):
                for j in range(i + 1, n_total):
                    if sim_matrix[i, j] > 0.75:
                        union(i, j)
            
            # Map to colors
            cluster_map = {}
            node_colors = []
            next_color = 0
            for i in range(n_total):
                root = find(i)
                if root == i and sim_matrix[i].max() <= 0.75:
                    # Isolated node (no high-sim connections)
                    node_colors.append(gray)
                else:
                    if root not in cluster_map:
                        cluster_map[root] = next_color
                        next_color = (next_color + 1) % len(colors)
                    node_colors.append(colors[cluster_map[root]])
                    
        elif cluster_method == 'embedding_pca':
            # Cluster in original high-dim space via PCA reduction then k-means
            if n_total >= 6:
                n_clusters = min(6, n_total // 2)
                # Use first 50 PCA components for clustering
                pca_50 = PCA(n_components=min(50, n_total), random_state=42)
                reduced = pca_50.fit_transform(embeddings)
                labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(reduced)
                node_colors = [colors[l % len(colors)] for l in labels]
            else:
                node_colors = [colors[i % len(colors)] for i in range(n_total)]
                
        elif cluster_method == 'similarity_tiers':
            # Rank by average similarity
            avg_sims = sim_matrix.mean(axis=1)
            # Sort and assign colors
            sorted_idx = np.argsort(avg_sims)
            node_colors = [""] * n_total
            tier_size = max(1, n_total // 6)
            for tier in range(6):
                start = tier * tier_size
                end = min((tier + 1) * tier_size, n_total) if tier < 5 else n_total
                for idx in sorted_idx[start:end]:
                    node_colors[idx] = colors[tier]
                    
        elif cluster_method == 'dominant_theme':
            # Group by caption keyword analysis
            all_meta = {img["image_id"]: img for img in get_all_images()}
            captions = [all_meta.get(img_id, {}).get("caption", "") for img_id in _faiss_ids]
            
            # Extract keywords and group
            keyword_groups = group_by_caption_themes(captions)
            node_colors = []
            for i in range(n_total):
                assigned = False
                for group_idx, keywords in enumerate(keyword_groups):
                    caption_lower = captions[i].lower()
                    if any(kw in caption_lower for kw in keywords):
                        node_colors.append(colors[group_idx % len(colors)])
                        assigned = True
                        break
                if not assigned:
                    node_colors.append(gray)
        else:
            node_colors = ["#5b6ef5"] * n_total
        
        # Get metadata
        all_meta = {img["image_id"]: img for img in get_all_images()}
        
        # Build nodes
        nodes = []
        for i, img_id in enumerate(_faiss_ids):
            meta = all_meta.get(img_id, {})
            # Handle None values for width/height (for videos, PDFs, etc.)
            width = meta.get("width")
            height = meta.get("height")
            nodes.append({
                "id": str(img_id),
                "x": float(coords_3d[i, 0]),
                "y": float(coords_3d[i, 1]),
                "z": float(coords_3d[i, 2]),
                "url": "/" + meta.get("file_path", "").replace("\\", "/") if meta else "",
                "name": str(meta.get("original_name", img_id[:8])) if meta else str(img_id[:8]),
                "caption": str(meta.get("caption", "")) if meta else "",
                "width": int(width) if width is not None else 0,
                "height": int(height) if height is not None else 0,
                "media_type": meta.get("media_type", "image") if meta else "image",
                "color": node_colors[i]
            })
        
        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "description": descriptions.get(cluster_method, ""),
            "method": cluster_method,
            "node_count": len(nodes),
            "edge_count": len(edges)
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "description": "", "nodes": [], "edges": []}), 500


def group_by_caption_themes(captions):
    """Extract common theme keywords from captions for grouping."""
    # Common visual themes
    theme_keywords = [
        ["screenshot", "screen", "desktop", "window"],
        ["person", "people", "face", "man", "woman", "child"],
        ["nature", "outdoor", "tree", "flower", "plant", "garden"],
        ["building", "architecture", "house", "room", "interior"],
        ["text", "document", "paper", "writing", "code"],
        ["food", "meal", "dish", "restaurant", "cooking"],
        ["animal", "pet", "dog", "cat", "bird"],
        ["vehicle", "car", "bus", "train", "road"]
    ]
    return theme_keywords





# ── Helper ─────────────────────────────────────────────────────────────────────
def _enrich_hits(hits: list[dict]) -> list[dict]:
    enriched = []
    skipped = 0
    for h in hits:
        meta = get_image_by_id(h["image_id"])
        if not meta:
            skipped += 1
            print(f"[ENRICH] Skip {h['image_id'][:8]}: no metadata")
            continue
        if not os.path.exists(meta["file_path"]):
            skipped += 1
            print(f"[ENRICH] Skip {h['image_id'][:8]}: file not found {meta['file_path']}")
            continue
        enriched.append({
            "image_id": h["image_id"],
            "score": round(h["score"] * 100, 1),
            "url": "/" + meta["file_path"].replace("\\", "/"),
            "original_name": meta["original_name"],
            "caption": meta["caption"],
            "width": meta["width"],
            "height": meta["height"],
            "upload_ts": meta["upload_ts"],
            "media_type": meta.get("media_type", "image"),
        })
    if skipped > 0:
        print(f"[ENRICH] Enriched {len(enriched)}, skipped {skipped}")
    return enriched


# ── Global Error Handlers ─────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template("index.html")

@app.errorhandler(500)
def server_error(error):
    import traceback
    print(f"[ERROR 500]: {error}")
    traceback.print_exc()
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def handle_exception(error):
    import traceback
    print(f"[ERROR]: {error}")
    traceback.print_exc()
    if request.path.startswith('/api/'):
        return jsonify({"error": str(error)}), 500
    return "Error occurred", 500

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8080)
