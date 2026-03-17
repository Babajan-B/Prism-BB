# Prism BB

**Semantic Media Search & Visualization Platform**

Prism BB is a multimodal AI-powered search engine that understands images, videos, audio, PDFs, and text in a unified embedding space. Built on Google's Gemini Embedding 2, it enables cross-modal semantic search and interactive 3D visualization of media relationships.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)

---

## ✨ Features

### 🔍 Multimodal Semantic Search
- **Text-to-Media**: Search using natural language descriptions
- **Image-to-Image**: Find visually similar content
- **Cross-Modal**: Query any type, find any type (e.g., describe a scene in text, find matching videos)

### 📁 Supported Media Types
| Type | Formats | Limits |
|------|---------|--------|
| **Images** | JPG, PNG, WEBP, GIF, BMP | Auto-resized |
| **Videos** | MP4, MOV, AVI, MKV, WEBM | ≤128 seconds |
| **Audio** | MP3, WAV, OGG, M4A, FLAC, AAC | ≤80 seconds |
| **Documents** | PDF (≤6 pages), TXT, MD, JSON, CSV | — |

### 🌐 3D Semantic Network
- Visualize relationships between media in interactive 3D space
- Multiple clustering algorithms (PCA, similarity tiers, nearest neighbor)
- Click nodes to view media, drag to explore connections

### 🎨 Modern Apple-Style UI
- Clean light theme with glassmorphism effects
- Smooth animations and transitions
- Responsive design for all screen sizes

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### Installation

#### macOS / Linux

```bash
# Clone the repository
git clone https://github.com/Babajan-B/Prism-BB.git
cd Prism-BB

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Windows

```powershell
# Clone the repository
git clone https://github.com/Babajan-B/Prism-BB.git
cd Prism-BB

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install FAISS (Windows-specific)
pip install faiss-cpu

# Install other dependencies
pip install flask google-genai Pillow python-dotenv numpy scikit-learn
```

> **Note for Windows users:** FAISS requires Visual C++ redistributables. If you encounter issues, install [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) first.

### Configuration
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

### Run the Application

```bash
python app.py
```

Open your browser and navigate to `http://localhost:8080`

---

## 📖 Usage Guide

### Uploading Media
1. Navigate to the **Upload** page
2. Drag & drop files or click "Choose files"
3. Click "Index Files" to process with Gemini Embedding
4. Files are automatically embedded and added to the searchable index

### Searching
1. Go to the **Search** page
2. Choose between **Text Search** or **Image Search**
3. For text: Enter a natural language description
4. For image: Upload a query image
5. View results with similarity scores
6. Toggle "Relationship Network" to see connections between results

### Gallery
- Browse all indexed media
- Click images to open lightbox
- Click videos/PDFs to open in new tab
- Delete files with the delete button

### Network Visualization
- Switch between clustering methods:
  - **Best Match**: Colors by nearest neighbor
  - **High Similarity**: Groups by >75% similarity
  - **Embedding Space**: PCA-based clustering
  - **Similarity Tiers**: 6-level ranking
- Use fullscreen button for immersive view
- Click nodes to view media details

---

## 🏗️ Architecture

```
Prism BB
├── Backend (Flask)
│   ├── File Upload & Validation
│   ├── Gemini Embedding API Integration
│   ├── FAISS Vector Store
│   └── SQLite Metadata Storage
├── Frontend
│   ├── Vanilla JavaScript
│   ├── 3D Force Graph (Three.js)
│   └── Apple-Style CSS
└── AI/ML Pipeline
    ├── Gemini Embedding 2 (multimodal)
    └── 3072-dimension vector space
```

### Tech Stack
- **Backend**: Flask, Python 3.10+
- **Vector DB**: FAISS (Facebook AI Similarity Search)
- **Metadata**: SQLite
- **Frontend**: Vanilla JS, Three.js, 3d-force-graph
- **AI Model**: Google Gemini Embedding 2 Preview

---

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `FLASK_ENV` | Development/production mode | `development` |
| `FLASK_PORT` | Server port | `8080` |

### Embedding Model

The application uses `gemini-embedding-2-preview` which supports:
- Up to 6 images per batch request
- 8192 text tokens
- 128-second videos
- 80-second audio
- 6-page PDFs

---

## 🎨 Customization

### Changing the Theme

Edit CSS variables in `static/css/style.css`:

```css
:root {
  --accent: #007aff;        /* Primary color */
  --bg: #f5f5f7;            /* Background */
  --surface: #ffffff;       /* Card backgrounds */
  --text: #1d1d1f;          /* Primary text */
}
```

### Adding New Media Types

1. Update `ALLOWED_EXTENSIONS` in `app.py`
2. Add MIME type mapping in `backend/embeddings.py`
3. Add preview handlers in `static/js/app.js`

---

## 🐛 Troubleshooting

### Common Issues

**"No files could be processed"**
- Check file formats are supported
- Verify files aren't corrupted
- Check console logs for specific errors

**"Batch embedding failed"**
- Verify Gemini API key is valid
- Check API rate limits (60 req/min on free tier)
- Large files may timeout - try smaller batches

**Network visualization not loading**
- Ensure Three.js and 3d-force-graph libraries loaded
- Check browser console for errors
- Try refreshing the page

### Platform-Specific Issues

**Windows - "faiss" module not found**
```powershell
# Install pre-built wheel
pip install faiss-cpu

# Or use conda
conda install -c pytorch faiss-cpu
```

**Windows - Path errors**
- Use forward slashes `/` or escaped backslashes `\\` in paths
- Ensure `uploads/` and `data/` folders have write permissions

**macOS - Permission denied**
```bash
# Fix folder permissions
chmod -R 755 uploads/ data/
```

### Performance Tips

- Process images in batches (up to 6 at a time)
- Resize large images before upload
- Use video compression for files >10MB
- Clear old index with "Delete" if storage grows large

---

## 💻 Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **macOS** | ✅ Fully Supported | Tested on macOS 12+ |
| **Windows** | ✅ Supported | Python 3.10+ required |
| **Linux** | ✅ Supported | Ubuntu 20.04+ recommended |

---

## 📝 API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload and index media files |
| `/api/images` | GET | List all indexed media |
| `/api/search/text` | POST | Text-based semantic search |
| `/api/search/image` | POST | Image-based similarity search |
| `/api/network` | GET | Get 3D network data |
| `/api/stats` | GET | Index statistics |
| `/api/images/<id>` | DELETE | Remove media from index |

### Example: Text Search

```bash
curl -X POST http://localhost:8080/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset at the beach", "top_k": 10}'
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev/) for the multimodal embedding API
- [FAISS](https://github.com/facebookresearch/faiss) for efficient similarity search
- [3d-force-graph](https://github.com/vasturiano/3d-force-graph) for network visualization
- [Three.js](https://threejs.org/) for 3D graphics

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Prism BB** — *See your media in a new light* 🔮
