# ODRAS - Ontology-Driven Requirements Analysis System

## What is ODRAS?

ODRAS is like having a smart assistant that reads your requirements documents and helps you understand what they really mean. Instead of manually going through hundreds of pages of technical documents, ODRAS uses AI to:

- **Find all the requirements** hidden in your documents
- **Organize them** in a logical, traceable way  
- **Suggest system designs** that could meet those requirements
- **Answer questions** about your requirements in plain English

Think of it as a bridge between messy, real-world documents and clean, structured engineering models that your team can actually work with.

**Perfect for**: Systems engineers, requirements analysts, project managers, and anyone who needs to make sense of complex technical documents quickly.

## 🚀 Key Capabilities

### **Requirements Analysis Engine**
- **Smart Document Processing**: Automatically extracts requirements from PDFs, Word docs, and other formats
- **AI-Powered Extraction**: Uses large language models guided by systems engineering ontologies
- **Confidence Scoring**: Provides confidence levels for each extracted requirement
- **Traceability**: Links every requirement back to its source document and location

### **Conceptual System Modeling**
- **Architecture Generation**: Creates multiple system architecture options from requirements
- **Component Identification**: Automatically identifies system components and their relationships
- **Interface Mapping**: Discovers and maps system interfaces and data flows
- **Alternative Solutions**: Generates multiple design alternatives with trade-off analysis

### **Digital Assistance System (DAS)**
- **AI Chat Interface**: Ask questions about your requirements and get intelligent answers
- **Voice Integration**: Speak your questions and get voice responses
- **Context-Aware Help**: DAS understands your project context and provides relevant suggestions
- **Session Management**: Maintains conversation history across analysis sessions

### **Ontology Workbench**
- **Visual Requirements Editor**: Interactive diagram editor for requirements and system models
- **Ontology Management**: Create and manage systems engineering ontologies
- **Import/Export**: Support for RDF, OWL, and other standard formats
- **Collaborative Editing**: Multiple team members can work on the same project

### **Project Organization**
- **Multi-Project Support**: Manage multiple requirements analysis projects
- **Document Management**: Organize and version control your source documents
- **User Management**: Role-based access control for team collaboration
- **Federated Access**: Share resources across different projects and teams

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, FastAPI for the API server
- **Databases**: PostgreSQL (metadata), Neo4j (relationships), Qdrant (vector search)
- **AI/ML**: OpenAI GPT, Ollama, Sentence Transformers for document analysis
- **Frontend**: HTML5, JavaScript, Cytoscape.js for interactive diagrams
- **Workflow**: BPMN Engine for automated document processing workflows
- **Infrastructure**: Docker and Docker Compose for easy deployment

## 📦 Quick Start

### What You Need
- A computer with Docker installed (handles all the technical setup)
- Some requirements documents to analyze (PDFs, Word docs, etc.)
- About 10 minutes to get started

### Get ODRAS Running

1. **Download ODRAS**
   ```bash
   git clone https://github.com/laserpointlabs/ODRAS.git
   cd ODRAS
   ```

2. **Install everything automatically**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
   This sets up all the databases and services ODRAS needs.

3. **Start ODRAS**
   ```bash
   ./odras.sh start
   ```

4. **Open ODRAS in your browser**
   - Go to: http://localhost:8000
   - Login with: `admin` / `admin` (or `das_service` / `das_service_2024!` for testing)

### Your First Analysis

1. **Upload a document**: Go to the Document Management section and upload a requirements document
2. **Start analysis**: Click "Analyze Document" and let ODRAS extract requirements
3. **Ask questions**: Use the DAS chat to ask about your requirements
4. **View results**: See the extracted requirements and generated system models

## 📚 Documentation

### **Core Documentation**
- **[Architecture](docs/architecture/)** - System design, DAS guide, database schema
- **[Features](docs/features/)** - Ontology workbench, file management, namespace guides
- **[Deployment](docs/deployment/)** - Installation and configuration guides
- **[Development](docs/development/)** - Testing guide and development setup

### **Key Documents**
- **[Document History](docs/DOCUMENT_HISTORY.md)** - Track of all documentation changes
- **[Authentication System](docs/AUTHENTICATION_SYSTEM.md)** - User authentication guide
- **[IRI System Overview](docs/IRI_SYSTEM_OVERVIEW.md)** - Identifier resolution system
- **[Roadmap](docs/ROADMAP.md)** - Future development plans

## 🔧 Development

### Local Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start services**
   ```bash
   ./odras.sh start-services
   ```

3. **Run the application**
   ```bash
   python -m backend.main
   ```

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/api/
pytest tests/unit/
pytest tests/integration/
```

## 🏗️ Project Structure

```
ODRAS/
├── backend/                 # Backend API and services
│   ├── api/                # REST API endpoints
│   ├── services/           # Core business logic
│   └── migrations/         # Database migrations
├── frontend/               # Web interface
├── docs/                   # Documentation
│   ├── architecture/       # System architecture docs
│   ├── features/          # Feature documentation
│   ├── deployment/        # Deployment guides
│   └── development/       # Development docs
├── scripts/               # Utility scripts
├── tests/                 # Test suites
└── data/                  # Sample data and configurations
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/laserpointlabs/ODRAS/issues)
- **Discussions**: Join the conversation in [GitHub Discussions](https://github.com/laserpointlabs/ODRAS/discussions)

## 🎯 Roadmap

- [ ] Enhanced OWL code editor integration
- [ ] SHACL constraints and validation
- [ ] Advanced visualization options
- [ ] Plugin system for extensibility
- [ ] Mobile-responsive interface

---

**ODRAS** - Transform complex requirements documents into actionable system models with AI-powered analysis.