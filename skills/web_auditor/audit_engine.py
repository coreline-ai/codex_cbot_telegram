import os
from bs4 import BeautifulSoup

class AuditEngine:
    def __init__(self):
        pass

    def audit_project(self, project_path):
        """
        Scans a web project for broken links, missing images, and structure.
        Returns a quality report dictionary.
        """
        report = {
            "score": 100,
            "issues": [],
            "checked_assets": 0
        }
        
        index_path = os.path.join(project_path, "index.html")
        if not os.path.exists(index_path):
            return {"score": 0, "issues": ["Fatal: index.html missing"]}

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

            # 1. Check Images
            images = soup.find_all("img")
            for img in images:
                src = img.get("src")
                if not src:
                    report["issues"].append("Image tag missing src attribute")
                    report["score"] -= 10
                    continue

                # Check if local asset exists
                if not src.startswith("http") and not src.startswith("data:"):
                    # Handle relative paths
                    asset_path = os.path.join(project_path, src)
                    if not os.path.exists(asset_path):
                        report["issues"].append(f"Broken image link: {src}")
                        report["score"] -= 20
                    else:
                        report["checked_assets"] += 1
                        
            # 2. Check structure
            if not soup.find("h1"):
                report["issues"].append("Missing H1 heading (SEO penalty)")
                report["score"] -= 5
            
            if not soup.find("title"):
                report["issues"].append("Missing Title tag")
                report["score"] -= 5

        except Exception as e:
            report["issues"].append(f"Audit failed: {e}")
            report["score"] = 0

        # Create textual summary
        report["summary"] = f"Quality Score: {report['score']}/100. Found {len(report['issues'])} issues."
        
        print(f"[AUDIT] {report['summary']}")
        if report["issues"]:
            print(f"[AUDIT] Issues: {', '.join(report['issues'])}")
            
        return report

if __name__ == "__main__":
    pass
