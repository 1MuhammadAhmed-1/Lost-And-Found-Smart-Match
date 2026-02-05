FoundIt AI: Multimodal Asset Recovery Platform 🔍

FoundIt AI is an intelligent Lost & Found ecosystem that leverages Generative AI and Vector Search to bridge the gap between physical object discovery and digital retrieval. By utilizing Gemini Pro Vision, the system eliminates manual cataloging, turning raw images into searchable semantic metadata.

🏗 Architecture & The Three-Layer Logic

The platform is engineered using a modular approach to handle complex multimodal data:

1. The Vision Layer (Feature Extraction)

Technology: Google Gemini Pro Vision

Logic: When a user uploads an image of a found item, the system autonomously generates a high-fidelity technical description. It extracts attributes such as category, color, material, and unique identifying marks, converting unstructured visual data into structured text metadata.

2. The Embedding Layer (Semantic Search)

Technology: Text-Embedding-004 / NumPy (Cosine Similarity)

Logic: Instead of rigid keyword matching, the system performs Semantic Retrieval. Both the AI-generated item descriptions and the user's lost-item queries are transformed into high-dimensional vectors. Matches are identified based on mathematical proximity, allowing a search for "navy hydration flask" to accurately find a "dark blue water bottle."

3. The Cognitive Layer (Autonomous Verification)

Technology: Gemini 2.5 Flash / Django Ninja

Logic: An AI Agent manages the claim process. It facilitates a multi-turn conversation with the claimant to extract "private" identifying details not explicitly shown in the public description, cross-referencing these details against the original Vision Layer analysis to approve or reject claims.

🛠 Tech Stack

Frontend:

React.js (Functional Components, Hooks)

Tailwind CSS (Responsive UI/UX)

Axios (Asynchronous API Communication)

Lucide React (Iconography)

Backend:

Python / Django

Django Ninja (Fast API-style routing)

Google Generative AI SDK (Gemini API)

Vector Similarity Logic (Cosine Similarity)

🚀 Key Features

Zero-Form Reporting: Upload a photo and let the AI handle the description, categorization, and tagging.

Natural Language Search: Describe what you lost in plain English; no specific keywords required.

AI Claims Adjuster: Interactive chat interface for verifying item ownership without manual intervention.

Responsive Design: Fully optimized for both desktop and mobile users.

🔧 Installation & Setup

Prerequisites

Python 3.10+

Node.js & npm

Gemini API Key

Backend Setup

Navigate to /backend

Create a virtual environment: python -m venv venv

Install dependencies: pip install -r requirements.txt

Set up .env with your GEMINI_API_KEY

Run migrations: python manage.py migrate

Start server: python manage.py runserver

Frontend Setup

Navigate to /frontend

Install dependencies: npm install

Start development server: npm run dev

📈 Future Roadmap

[ ] Integration with Pinecone for scalable vector storage.

[ ] Real-time push notifications via WebSockets for match alerts.

[ ] Multi-campus/Multi-location support with geofencing.

Developed as a demonstration of Multimodal AI integration in modern Full-Stack Web Applications.
