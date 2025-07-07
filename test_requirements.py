def check_package(package_name):
    try:
        __import__(package_name)
        print(f"✅ {package_name} is installed")
        return True
    except ImportError:
        print(f"❌ {package_name} is NOT installed")
        return False

# List of required packages
required_packages = [
    "azure.storage.blob",
    "openai",
    "dotenv",
    "numpy",
    "pandas",
    "tqdm",
    "setuptools",
    "PyPDF2",
    "streamlit",
    "langgraph",
    "langchain",
    "langchain_openai"
]

print("Checking required packages...")
print("-" * 40)

all_installed = True
for package in required_packages:
    if not check_package(package):
        all_installed = False

print("-" * 40)
if all_installed:
    print("🎉 All required packages are installed!")
else:
    print("⚠️ Some packages are missing. Please install them using pip.") 