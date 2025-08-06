#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "=================================================="
echo "    Git-Hyper Setup and Compilation"
echo "=================================================="
echo

log_info "Checking Python installation..."
if ! command_exists python3; then
    log_error "Python3 not found. Please install Python3."
    exit 1
fi
log_success "Python3 found: $(python3 --version)"

log_info "Checking pip installation..."
if ! command_exists pip3 && ! command_exists pip; then
    log_error "pip not found. Please install pip."
    exit 1
fi

if command_exists pip3; then
    PIP_CMD="pip3"
else
    PIP_CMD="pip"
fi
log_success "pip found: $($PIP_CMD --version)"

log_info "Checking requirements.txt file..."
if [ ! -f "requirements.txt" ]; then
    log_warning "requirements.txt not found in current directory."
    log_info "Creating basic requirements.txt..."
    cat > requirements.txt << EOF
pathlib2==2.3.7
setuptools>=45.0.0
wheel>=0.36.0
EOF
    log_success "requirements.txt created with basic dependencies."
else
    log_success "requirements.txt found."
fi

log_info "Checking virtual environment..."
if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        log_success "Virtual environment created."
    else
        log_error "Failed to create virtual environment."
        exit 1
    fi
fi

log_info "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || {
    log_warning "Could not activate virtual environment. Continuing without it."
}

log_info "Updating pip..."
$PIP_CMD install --upgrade pip --quiet
if [ $? -eq 0 ]; then
    log_success "pip updated."
else
    log_warning "Could not update pip, but continuing..."
fi

log_info "Installing requirements.txt dependencies..."
echo "----------------------------------------"
$PIP_CMD install -r requirements.txt --verbose
PIP_EXIT_CODE=$?
echo "----------------------------------------"

if [ $PIP_EXIT_CODE -eq 0 ]; then
    log_success "All dependencies installed successfully!"
else
    log_error "Some dependencies failed to install (code: $PIP_EXIT_CODE)"
    log_info "Continuing with compilation..."
fi

log_info "Checking project structure..."

if [ ! -f "main.py" ]; then
    log_error "main.py file not found in current directory!"
    exit 1
fi
log_success "main.py found."

if [ ! -f "app/data_source.py" ]; then
    log_error "app/data_source.py file not found!"
    
    log_info "Creating basic app structure..."
    mkdir -p app
    
    cat > app/__init__.py << EOF
EOF
    
    cat > app/data_source.py << EOF
class DataSource:
    def __init__(self):
        pass
    
    def load_data(self):
        return {}
    
    def save_data(self, data):
        pass
EOF
    log_success "Basic app structure created."
else
    log_success "app/data_source.py found."
fi

log_info "Checking Python file syntax..."

python3 -m py_compile main.py
if [ $? -eq 0 ]; then
    log_success "main.py - syntax OK"
else
    log_error "main.py - syntax error!"
    exit 1
fi

python3 -m py_compile app/data_source.py
if [ $? -eq 0 ]; then
    log_success "app/data_source.py - syntax OK"
else
    log_error "app/data_source.py - syntax error!"
    exit 1
fi

log_info "Compiling Python files to bytecode..."
python3 -m compileall . --quiet
if [ $? -eq 0 ]; then
    log_success "Bytecode compilation completed!"
else
    log_warning "Some files may not have been compiled."
fi

log_info "Testing module imports..."

python3 -c "
try:
    from app.data_source import DataSource
    print('✓ DataSource imported successfully')
except Exception as e:
    print(f'✗ Error importing DataSource: {e}')
    exit(1)

try:
    import main
    print('✓ main.py imported successfully')
except Exception as e:
    print(f'✗ Error importing main.py: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    log_success "All modules imported correctly!"
else
    log_error "Error importing modules!"
    exit 1
fi

echo "Preparing files ..."

mkdir ~/.git-hyper
mkdir ~/.git-hyper/bin
mv venv ~/.git-hyper/bin/venv
cp docs/SETUP.md ~/.git-hyper/SETUP.md
cp docs/VERSION ~/.git-hyper/VERSION

log_success "files prepared successfully"

echo
read -p "Do you want to run the main program (main.py)? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Running main.py..."
    echo "----------------------------------------"
    python3 main.py
    MAIN_EXIT_CODE=$?
    echo "----------------------------------------"
    
    if [ $MAIN_EXIT_CODE -eq 0 ]; then
        log_success "main.py executed successfully!"
    else
        log_error "main.py finished with exit code: $MAIN_EXIT_CODE"
    fi
fi



echo
echo "=================================================="
echo "              EXECUTION SUMMARY"
echo "=================================================="
log_info "Dependencies installed: $([ $PIP_EXIT_CODE -eq 0 ] && echo 'YES' || echo 'WITH ISSUES')"
log_info "main.py compiled: YES"
log_info "app/data_source.py compiled: YES"
log_info "Imports tested: YES"
echo

log_info "Generated .pyc files:"
find . -name "*.pyc" -type f | head -10

echo
log_success "Setup and compilation completed!"
echo "=================================================="