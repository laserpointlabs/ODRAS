# ODRAS - Ontology-Driven Requirements Analysis System

**Transform complex documents into structured requirements in minutes, not months.**

ODRAS is an AI-powered platform that reads your project documents (like requirements specifications, technical manuals, and design documents) and automatically extracts, organizes, and structures requirements using intelligent analysis. Think of it as having an expert systems engineer who can instantly understand your documents and create a structured foundation for your project.

## 🤔 What is ODRAS?

**The Problem**: Traditional requirements analysis is slow and manual. Engineers spend weeks reading through hundreds of pages of documents, manually extracting requirements, and trying to organize them into a coherent system. This process is error-prone, time-consuming, and often results in missing or conflicting requirements.

**The Solution**: ODRAS uses AI to automatically:
- 📄 **Read and understand** your project documents
- 🎯 **Extract requirements** using intelligent analysis
- 🔗 **Organize and connect** requirements logically
- 📊 **Create visual models** of your system
- 💬 **Answer questions** about your requirements through an AI assistant

**Real Example**: Instead of spending weeks manually reading a 200-page requirements document, ODRAS can analyze it in minutes and give you a structured breakdown of all requirements, their relationships, and potential issues.

## 🚀 Key Features

### **🤖 AI Assistant (DAS)**
- **Chat with your documents**: Ask questions about your requirements in plain English
- **Voice interaction**: Talk to the system using voice commands
- **Smart suggestions**: Get recommendations based on your project context
- **Always learning**: Remembers your project history and preferences

### **📋 Requirements Workbench**
- **Visual editor**: Create and edit requirements using an intuitive interface
- **Smart organization**: Automatically categorizes and links related requirements
- **Multiple views**: Save different perspectives of your requirements
- **Import/Export**: Works with standard formats (RDF, OWL, ReqIF)

### **📚 Document Intelligence**
- **Smart reading**: AI understands complex technical documents
- **Automatic extraction**: Finds requirements you might have missed
- **Knowledge management**: Builds a searchable knowledge base
- **Workflow automation**: Processes documents through defined workflows

### **👥 Project Management**
- **Multiple projects**: Organize different projects in one place
- **Team collaboration**: Work together on requirements
- **User permissions**: Control who can access what
- **Version control**: Track changes and maintain history

## 🛠️ What Powers ODRAS

**For the Technical Curious:**
- **AI Engine**: Uses advanced language models (OpenAI GPT) to understand documents
- **Database**: Stores your requirements and knowledge in specialized databases
- **Web Interface**: Modern web-based interface that works in any browser
- **Workflow Engine**: Automates document processing using business process management
- **Container Technology**: Runs everything in Docker containers for easy setup

**Don't worry about the technical details** - ODRAS handles all the complexity for you!

## 🚀 Quick Start (5 Minutes)

### What You'll Need
- **Docker Desktop** (download from [docker.com](https://docker.com) if you don't have it)
- **Git** (download from [git-scm.com](https://git-scm.com) if you don't have it)
- **5-10 minutes** of your time

### Step-by-Step Installation

**Step 1: Download ODRAS**
```bash
git clone https://github.com/laserpointlabs/ODRAS.git
cd ODRAS
```

**Step 2: Install Everything (One Command)**
```bash
chmod +x install.sh
./install.sh
```
*This will download and set up all the necessary components automatically.*

**Step 3: Start ODRAS**
```bash
./odras.sh start
```
*This starts all the services. Wait about 30-60 seconds for everything to initialize.*

**Step 4: Open ODRAS in Your Browser**
- Go to: **http://localhost:8000**
- Login with: **Username:** `admin` **Password:** `admin`

**🎉 You're Ready!** ODRAS is now running and you can start analyzing documents.

### First Steps After Installation
1. **Upload a document** using the Document Management section
2. **Ask the AI assistant** questions about your project
3. **Explore the Requirements Workbench** to see how requirements are organized
4. **Try the voice features** if you have a microphone

### Need Help?
- **Stuck?** Check the [Troubleshooting](#-troubleshooting) section below
- **Want to learn more?** Browse the [Documentation](#-documentation) section
- **Have questions?** Open an [issue on GitHub](https://github.com/laserpointlabs/ODRAS/issues)

## 🆘 Troubleshooting

### Common Issues and Solutions

**❌ "Docker not found" error**
- **Solution**: Install Docker Desktop from [docker.com](https://docker.com) and restart your computer

**❌ "Port already in use" error**
- **Solution**: Stop other applications using port 8000, or run: `./odras.sh stop` then `./odras.sh start`

**❌ "Permission denied" when running scripts**
- **Solution**: Run: `chmod +x *.sh` to make scripts executable

**❌ ODRAS won't start or keeps crashing**
- **Solution**: Run: `./odras.sh clean -y` then `./odras.sh init-db` to reset everything

**❌ Can't access the web interface**
- **Solution**: Make sure you're going to `http://localhost:8000` (not https) and wait 60 seconds after starting

**❌ Login doesn't work**
- **Solution**: Try these credentials:
  - Username: `admin` Password: `admin`
  - Username: `das_service` Password: `das_service_2024!`

**❌ Still having problems?**
- Check the logs: `./odras.sh logs`
- Open an [issue on GitHub](https://github.com/laserpointlabs/ODRAS/issues) with your error message

## 📚 Learn More

### **For Beginners**
- **[Getting Started Guide](docs/development/)** - Step-by-step tutorials
- **[User Interface Guide](docs/features/)** - How to use ODRAS features
- **[Common Use Cases](docs/ODRAS_Use_Cases.md)** - Real-world examples

### **For Advanced Users**
- **[System Architecture](docs/architecture/)** - Technical deep-dive
- **[API Documentation](docs/development/)** - Developer resources
- **[Deployment Guide](docs/deployment/)** - Production setup

### **Key Documents**
- **[What is ODRAS?](docs/ODRAS_Origin_and_WhitePaper.md)** - The complete story
- **[Roadmap](docs/ROADMAP.md)** - What's coming next
- **[Authentication Guide](docs/AUTHENTICATION_SYSTEM.md)** - User management

## 👨‍💻 For Developers

### Want to Contribute or Customize ODRAS?

**Prerequisites for Development:**
- Python 3.8+ installed on your computer
- Docker and Docker Compose
- Git

**Setting Up for Development:**

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the database services**
   ```bash
   ./odras.sh start-services
   ```

3. **Run ODRAS in development mode**
   ```bash
   python -m backend.main
   ```

**Running Tests:**
```bash
# Test everything
pytest

# Test specific parts
pytest tests/api/          # API tests
pytest tests/unit/         # Unit tests
pytest tests/integration/  # Integration tests
```

**Need Help with Development?**
- Check the [Development Guide](docs/development/) for detailed instructions
- Look at existing code in the `backend/` and `frontend/` directories
- Join our [GitHub Discussions](https://github.com/laserpointlabs/ODRAS/discussions) to ask questions

## 📁 What's Inside ODRAS

**For the Curious - Here's How ODRAS is Organized:**

```
ODRAS/
├── 🖥️  backend/           # The "brain" - AI processing and APIs
├── 🌐  frontend/          # The "face" - what you see in your browser
├── 📚  docs/              # All the documentation and guides
├── 🔧  scripts/           # Helper tools and utilities
├── 🧪  tests/             # Quality assurance and testing
└── 📊  data/              # Sample files and configurations
```

**You don't need to understand this structure to use ODRAS** - it's just here for developers and the technically curious!

## 🤝 Want to Help?

**We'd love your contribution!** Whether you're a developer, designer, or just someone with ideas:

1. **Found a bug?** [Report it here](https://github.com/laserpointlabs/ODRAS/issues)
2. **Have an idea?** [Share it in discussions](https://github.com/laserpointlabs/ODRAS/discussions)
3. **Want to code?** Check out our [Contributing Guide](docs/development/)
4. **Want to help others?** Answer questions in our discussions

## 📄 Legal Stuff

This project is open source under the MIT License. You can use it, modify it, and share it freely.

## 🆘 Get Help

**Having trouble? We're here to help!**

- 📖 **Read the docs**: Check the [Learn More](#-learn-more) section above
- 🐛 **Report bugs**: [GitHub Issues](https://github.com/laserpointlabs/ODRAS/issues)
- 💬 **Ask questions**: [GitHub Discussions](https://github.com/laserpointlabs/ODRAS/discussions)
- 📧 **Contact us**: Open an issue for direct communication

## 🚀 What's Coming Next

**Exciting features in development:**
- 📱 Mobile app for on-the-go requirements analysis
- 🔌 Plugin system for custom integrations
- 🎨 Enhanced visual tools and diagrams
- 🤖 Even smarter AI capabilities
- 📊 Advanced analytics and reporting

---

## 🎯 Ready to Get Started?

**You're just 5 minutes away from transforming how you handle requirements!**

1. ⬇️ [Download ODRAS](#-quick-start-5-minutes)
2. 🚀 [Start analyzing documents](#-first-steps-after-installation)
3. 💬 [Ask the AI assistant anything](#-ai-assistant-das)
4. 📈 [See your productivity soar](#-what-is-odras)

**ODRAS** - *Where complex documents become clear requirements in minutes, not months.*