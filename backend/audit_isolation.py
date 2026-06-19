import os
import re
import sys

def scan_files(root_dir):
    """
    Scans Python files for potential multi-tenant isolation issues.
    Specifically looks for database queries that might be missing organization_id filters.
    """
    print(f"Starting audit scan in {root_dir}...")
    
    # regex to find db.query(Model) calls
    query_pattern = re.compile(r"db\.query\(\s*models\.(\w+)\s*\)")
    
    # Models that must be isolated by organization_id
    isolated_models = {
        "Decision", "Outcome", "Integration", "TeamMember", "Attribution", "SyncLog", "EmailLog"
    }
    
    issues_found = 0
    
    for dirpath, _, filenames in os.walk(root_dir):
        if "migrations" in dirpath or "tests" in dirpath:
            continue
            
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Naive check: Does it query an isolated model?
            for match in query_pattern.finditer(content):
                model_name = match.group(1)
                
                if model_name in isolated_models:
                    # Check context (next 500 chars) for filter(organization_id)
                    start = match.end()
                    context = content[start:start+400]
                    
                    # Very simple heuristic: if it doesn't mention organization_id in the immediate filter chain, flag it.
                    # Also check if it's "all()" directly without filter, or if filter doesn't have org_id.
                    
                    if "organization_id" not in context:
                        # Allow if it filters by ID and we assume ID implies org check (risky but common pattern)
                        # But strictly, we should always check org_id too.
                        
                        # Check line number
                        lineno = content[:match.start()].count('\n') + 1
                        print(f"[WARNING] {filepath}:{lineno} - Querying {model_name} without obvious organization_id filter.")
                        # print(f"Context: {context[:100]}...")
                        issues_found += 1

    if issues_found == 0:
        print("\nSUCCESS: No obvious isolation issues found.")
    else:
        print(f"\nAudit complete. Found {issues_found} potential issues to review.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming script is in /backend/scripts/audit_isolation.py
    # and app is in /backend/app
    backend_root = os.path.dirname(current_dir)
    app_dir = os.path.join(backend_root, "app")
    scan_files(app_dir)
