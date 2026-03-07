from app.analysis.escalation import find_escalation_paths

paths = find_escalation_paths("Intern_A")

print("Escalation Paths Found:")
for p in paths:
    print(p)