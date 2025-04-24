#!/bin/bash
# Install dependencies needed for chaos engineering experiments

echo "Setting up dependencies for chaos engineering experiments..."

# Check which package manager is available
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    echo "Using apt-get package manager"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "Using yum package manager"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    echo "Using dnf package manager"
elif command -v apk &> /dev/null; then
    PKG_MANAGER="apk"
    echo "Using apk package manager"
else
    echo "No supported package manager found. Please install dependencies manually."
    exit 1
fi

# Install required packages
echo "Installing required packages..."

# bc - for floating point math
if ! command -v bc &> /dev/null; then
    echo "Installing bc for floating point calculations..."
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        sudo apt-get update && sudo apt-get install -y bc
    elif [ "$PKG_MANAGER" = "yum" ]; then
        sudo yum install -y bc
    elif [ "$PKG_MANAGER" = "dnf" ]; then
        sudo dnf install -y bc
    elif [ "$PKG_MANAGER" = "apk" ]; then
        sudo apk add bc
    fi
    
    if command -v bc &> /dev/null; then
        echo "bc installed successfully"
    else
        echo "Failed to install bc"
    fi
else
    echo "bc is already installed"
fi

# Check for Python and required packages for load generation
if command -v python3 &> /dev/null; then
    echo "Python 3 is available"
    
    # Check if numpy is installed in Python
    if ! python3 -c "import numpy" &> /dev/null; then
        echo "Installing numpy for memory load generation..."
        if command -v pip3 &> /dev/null; then
            sudo pip3 install numpy
        elif command -v pip &> /dev/null; then
            sudo pip install numpy
        else
            echo "pip not found, attempting to install from package manager"
            if [ "$PKG_MANAGER" = "apt-get" ]; then
                sudo apt-get install -y python3-numpy
            elif [ "$PKG_MANAGER" = "yum" ]; then
                sudo yum install -y python3-numpy
            elif [ "$PKG_MANAGER" = "dnf" ]; then
                sudo dnf install -y python3-numpy
            elif [ "$PKG_MANAGER" = "apk" ]; then
                sudo apk add py3-numpy
            fi
        fi
        
        if python3 -c "import numpy" &> /dev/null; then
            echo "numpy installed successfully"
        else
            echo "Failed to install numpy"
        fi
    else
        echo "numpy is already installed"
    fi
else
    echo "Python 3 is not available. Some experiments may not work correctly."
fi

echo "Dependency setup complete!"
echo "You can now run the chaos engineering experiments."
