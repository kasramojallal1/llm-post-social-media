import subprocess
from pathlib import Path

def run_extractors():
    base_dir = Path(__file__).resolve().parent

    # paths to extractors
    resume_extractor = base_dir / "extractors" / "resume.py"
    linkedin_extractor = base_dir / "extractors" / "linkedin.py"

    print("📄 Extracting resume...")
    subprocess.run(["python", str(resume_extractor)], check=True)

    print("🔗 Extracting LinkedIn...")
    subprocess.run(["python", str(linkedin_extractor)], check=True)

    print("✅ Extraction complete. Check the 'processed/' directory.")

if __name__ == "__main__":
    run_extractors()