# ODRAS - Ontology-Driven Requirements Analysis System

ODRAS is an intelligent platform that transforms complex requirements documents (like CDDs, ICDs, and technical specifications) into structured, traceable system models. It uses AI-powered analysis guided by systems engineering ontologies to extract requirements, identify relationships, and generate conceptual system architectures that engineers can build upon.

## 🚀 Features

### **Digital Assistance System (DAS)**
- **AI-Powered Chat Interface**: Intelligent conversation system with context awareness
- **Voice Integration**: Voice-to-text and text-to-speech capabilities
- **Session Intelligence**: Advanced session management and conversation history
- **Smart Suggestions**: Contextual recommendations based on user queries

### **Ontology Workbench**
- **Visual Ontology Editor**: Interactive Cytoscape-based diagram editor
- **Named Views System**: Save and restore different ontology states
- **Import/Export**: Support for RDF, OWL, and Turtle formats
- **Real-time Collaboration**: Multi-user ontology editing capabilities

### **Document Processing**
- **Intelligent Ingestion**: Automated document parsing and analysis
- **Requirements Extraction**: AI-powered requirements identification
- **Knowledge Management**: Vector-based knowledge storage and retrieval
- **BPMN Integration**: Workflow-driven document processing

### **Project Management**
- **Multi-Project Support**: Organize work across different projects
- **Namespace Management**: Hierarchical URI organization
- **User Management**: Role-based access control
- **Federated Access**: Cross-project resource sharing

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, FastAPI, PostgreSQL, Neo4j, Qdrant
- **Frontend**: HTML5, JavaScript, Cytoscape.js
- **AI/ML**: OpenAI GPT, Ollama, Sentence Transformers
- **Workflow**: Camunda BPMN Engine
- **Infrastructure**: Docker, Docker Compose

## 📦 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for local development)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/laserpointlabs/ODRAS.git
   cd ODRAS
   ```

2. **Run the installation script**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Start the system**
   ```bash
   ./odras.sh start
   ```

4. **Access the application**
   - Web Interface: http://localhost:8000
   - Default credentials: `admin/admin` or `jdehart/jdehart`

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

**ODRAS** - Empowering intelligent requirements analysis through ontology-driven methodologies.