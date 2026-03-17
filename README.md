# 🔮 Prism BB

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Google-Gemini%20Embedding-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/FAISS-Facebook%20AI-4267B2?style=for-the-badge&logo=facebook&logoColor=white" />
</p>

<p align="center">
  <b>Multimodal Semantic Search & 3D Visualization Platform</b>
</p>

<p align="center">
  Search across <b>images</b>, <b>videos</b>, <b>audio</b>, <b>PDFs</b>, and <b>text</b> using natural language or media queries.
  Built with Google's Gemini Embedding 2 for state-of-the-art multimodal AI understanding.
</p>

---

## ✨ Features

### 🔍 Cross-Modal Semantic Search
| Query Type | Finds | Example |
|------------|-------|---------|
| **Text** → Any Media | Search with natural language | "sunset at beach" finds matching images, videos |
| **Image** → Similar Media | Visual similarity search | Upload a photo, find similar content |
| **Any** → Any | True multimodal search | Text query can return videos, PDFs, audio |

### 📁 Supported Media Types

| Type | Formats | Limit | Preview |
|------|---------|-------|---------|
| 🖼️ **Images** | JPG, PNG, WEBP, GIF, BMP | Auto-resized | Thumbnail + Lightbox |
| 🎬 **Videos** | MP4, MOV, AVI, MKV, WEBM | ≤128 seconds | Inline player |
| 🎵 **Audio** | MP3, WAV, OGG, M4A, FLAC, AAC | ≤80 seconds | Audio controls |
| 📄 **Documents** | PDF (≤6 pages) | 6 pages max | PDF viewer |
| 📝 **Text** | TXT, MD, JSON, CSV | 8192 tokens | Text preview |

### 🌐 3D Semantic Network Visualization
- **Interactive 3D Graph**: Explore relationships between media files
- **Clustering Algorithms**: 
  - 🔗 Best Match (Nearest Neighbor)
  - ⭐ High Similarity (>75%)
  - 🧠 Embedding Space (PCA)
  - 📊 Similarity Tiers (6 levels)
- **Fullscreen Mode**: Immersive exploration
- **Click to View**: Open media directly from graph nodes

### 🎨 Modern UI Design
- Clean Apple-inspired interface with glassmorphism effects
- Light theme with smooth animations
- Responsive layout for all screen sizes
- Drag & drop file upload with visual feedback

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Installation

#### 🍎 macOS / 🐧 Linux

```bash
# Clone repository
git clone https://github.com/Babajan-B/Prism-BB.git
cd Prism-BB

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 🪟 Windows

```powershell
# Clone repository
git clone https://github.com/Babajan-B/Prism-BB.git
cd Prism-BB

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install FAISS (Windows-specific)
pip install faiss-cpu

# Install other dependencies
pip install flask>=3.0.0 google-genai>=1.32.0 Pillow==10.3.0 numpy==1.26.4 python-dotenv==1.0.1 scikit-learn>=1.4.0
```

> **Windows Note:** If FAISS installation fails, install [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) first.

### Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Run the Application

```bash
# Start the server
python app.py

# Open browser and navigate to:
# http://localhost:8080
```

---

## 📖 Usage Guide

### 1️⃣ Upload Media
1. Go to **Upload** page
2. Drag & drop files or click "Choose files"
3. Click "Index Files" to process
4. Files are embedded and added to searchable index

### 2️⃣ Search
1. Navigate to **Search** page
2. Choose tab:
   - **Text Search**: Type natural language query
   - **Image Search**: Upload/query image
3. View results with similarity percentages
4. Toggle "Relationship Network" to see connections

### 3️⃣ Browse Gallery
- View all indexed media in grid layout
- Click images → Lightbox view
- Click videos/PDFs → Opens in new tab
- Delete files with trash button

### 4️⃣ Explore Network
- Switch clustering methods via dropdown
- Click fullscreen for immersive view
- Drag nodes to explore relationships
- Click nodes to view media

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Upload  │  │  Search  │  │  Gallery │  │ Network  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     FLASK BACKEND                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ File Upload  │  │   Search     │  │ 3D Network   │      │
│  │  & Validate  │  │   Queries    │  │    Data      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    AI/ML PIPELINE                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │     Google Gemini Embedding 2 (multimodal)             │  │
│  │     • 3072-dimension vectors                          │  │
│  │     • Text + Image + Video + Audio + PDF support      │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      DATA STORAGE                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │     FAISS      │  │    SQLite      │  │   File System  │ │
│  │ Vector Search  │  │   Metadata     │  │   Uploads      │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack
| Component | Technology |
|-----------|------------|
| **Backend** | Flask (Python 3.10+) |
| **AI Model** | Google Gemini Embedding 2 Preview |
| **Vector DB** | FAISS (Facebook AI Similarity Search) |
| **Metadata** | SQLite |
| **Frontend** | Vanilla JavaScript, Three.js |
| **Visualization** | 3d-force-graph |
| **Styling** | Custom CSS (Apple-style) |

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini API key |
| `FLASK_ENV` | ❌ No | `development` or `production` |
| `FLASK_PORT` | ❌ No | Server port (default: 8080) |

### Gemini Embedding Limits

| Media Type | Max per Request | Total Limit |
|------------|-----------------|-------------|
| Images | 6 per batch | 8192 tokens |
| Videos | 1 per request | 128 seconds |
| Audio | 1 per request | 80 seconds |
| PDF | 1 per request | 6 pages |
| Text | - | 8192 tokens |

---

## 💻 Platform Support

| Platform | Status | Tested On |
|----------|--------|-----------|
| macOS 12+ | ✅ Fully Supported | Monterey, Ventura, Sonoma |
| Windows 10/11 | ✅ Supported | Python 3.10+ required |
| Ubuntu 20.04+ | ✅ Supported | WSL compatible |

---

## 🐛 Troubleshooting

### Common Issues

**"No files could be processed"**
- Check file format is in supported list
- Verify file isn't corrupted
- Check browser console for errors

**"Batch embedding failed"**
- Verify `GEMINI_API_KEY` is valid
- Check rate limit (60 requests/min on free tier)
- Large files may timeout - try smaller batches

**"FAISS module not found" (Windows)**
```powershell
pip install faiss-cpu
# Or use conda:
conda install -c pytorch faiss-cpu
```

**3D Network not loading**
- Check internet connection (loads libraries from CDN)
- Open browser console (F12) for errors
- Try hard refresh (Ctrl+Shift+R)

### Performance Tips

- Process images in batches (up to 6 at once)
- Resize images >4MB before upload
- Compress videos >10MB
- Delete old files to keep index size manageable

---

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload and index media files |
| `/api/images` | GET | List all indexed media |
| `/api/search/text` | POST | Text-based semantic search |
| `/api/search/image` | POST | Image-based similarity search |
| `/api/network` | GET | Get 3D network graph data |
| `/api/stats` | GET | Get index statistics |
| `/api/images/<id>` | DELETE | Remove media from index |

### Example: Text Search

```bash
curl -X POST http://localhost:8080/api/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sunset at the beach with palm trees",
    "top_k": 10,
    "min_score": 0.20
  }'
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev/) - Multimodal embedding API
- [FAISS](https://github.com/facebookresearch/faiss) - Efficient similarity search
- [3d-force-graph](https://github.com/vasturiano/3d-force-graph) - Network visualization
- [Three.js](https://threejs.org/) - 3D graphics library

---

<p align="center">
  <b>Prism BB</b> — See your media in a new light 🔮
</p>

<p align="center">
  Made with ❤️ using Gemini Embedding 2
</p>
