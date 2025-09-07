# Controlled Shell Command Execution Tool Plan

This document outlines the plan for integrating a controlled shell command execution tool into the project. The tool will enable the secure execution of specific virtual environment commands while adhering to the existing tool framework.

---

## **Overview**
The new tool will:
- Safely execute commands using the virtual environment's Python executable.
- Restrict execution to pre-approved commands listed in an allowlist.
- Integrate seamlessly with the existing `direct_tools.py` framework.

---

## **Key Design Elements**

### **1. Command Allowlist**
- A dictionary-based allowlist will map command aliases (e.g., `initdb`) to their respective arguments (e.g., `--mktables`).
- Example:
  ```json
  {
      "initdb": "--mktables",
      "runserver": "web"
  }
  ```

### **2. Virtual Environment Python Executable**
- The tool will locate the Python executable within the virtual environment using the `VIRTUAL_ENV` environment variable:
  ```python
  venv_python = os.path.join(os.getenv("VIRTUAL_ENV", ""), "bin", "python")
  ```
- Execution will fail gracefully if the virtual environment is not active or the Python executable cannot be found.

### **3. Integration with Existing Framework**
The tool will follow the established `ToolProvider` and `DirectTool` patterns in `direct_tools.py`:
1. **New Provider:** `VirtualEnvCommandToolProvider`
   - Manages tools related to virtual environment command execution.
   - Validates and executes commands.

2. **New Tool:** `VirtualEnvExecuteTool`
   - Handles the execution of specific commands based on aliases from the allowlist.

---

## **Implementation Details**

### **Step 1: Add a Tool Provider**
A new `ToolProvider`, named `VirtualEnvCommandToolProvider`, will be introduced:
```python
class VirtualEnvCommandToolProvider(ToolProvider):
    def __init__(self, allowlist: Dict[str, str]):
        super().__init__("virtualenv")
        self.allowlist = allowlist
        self.virtualenv_python = os.path.join(os.getenv("VIRTUAL_ENV", ""), "bin", "python")
        if not os.path.exists(self.virtualenv_python):
            raise RuntimeError("Could not locate Python executable in virtual environment!")
        self._register_tools()

    def _register_tools(self) -> None:
        self.register_tool(VirtualEnvExecuteTool(self))
```

### **Step 2: Implement the Tool**
The tool, named `VirtualEnvExecuteTool`, will:
1. Validate the alias against the allowlist.
2. Construct and execute the command using the virtual environment's Python interpreter.

```python
class VirtualEnvExecuteTool(DirectTool):
    def __init__(self, provider: VirtualEnvCommandToolProvider):
        super().__init__(
            name="virtualenv.execute",
            description="Execute specific commands safely in the virtual environment",
            input_model=InputModel  # Replace with a custom input model if needed
        )
        self.provider = provider

    def _execute(self, alias: str) -> Dict[str, Any]:
        try:
            args = self.provider.allowlist.get(alias)
            if not args:
                raise ValueError(f"Alias '{alias}' not allowed.")

            cmd = [self.provider.virtualenv_python, "j4ne.py"] + args.split()
            subprocess.run(cmd, shell=False)
            return {"success": True, "message": f"Successfully executed '{alias}'"}
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}
```

### **Step 3: Register with Multiplexer**
The `DirectMultiplexer` will be updated to include this new provider:
```python
virtualenv_allowlist = {
    "initdb": "--mktables",
    "runserver": "web",
}

virtualenv_provider = VirtualEnvCommandToolProvider(allowlist=virtualenv_allowlist)
multiplexer.add_provider(virtualenv_provider)
```

---

## **Benefits of the Plan**
1. **Consistency:** Adheres to the established patterns in `direct_tools.py`.
2. **Control:** Restricts command execution to pre-approved aliases and arguments.
3. **Safety:** Limits execution to the virtual environment context.
4. **Scalability:** Easily extendable by updating the allowlist with new commands.

---

## **Next Steps**
1. Implement the `VirtualEnvCommandToolProvider` and `VirtualEnvExecuteTool`.
2. Create an initial `allowlist` of commands.
3. Register the provider with the `DirectMultiplexer`.
4. Test the tool with common commands like `initdb` and `runserver`.

---