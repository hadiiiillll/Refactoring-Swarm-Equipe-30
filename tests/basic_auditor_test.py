from src.agents.auditor_agent import AuditorAgent


if __name__ == "__main__":
    auditor = AuditorAgent()
    result = auditor.audit("sandbox/buggy_code.py")

    print("\n====== PLAN DE REFACTORING ======\n")
    print(result)
