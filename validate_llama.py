import time
import os
import json
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

MODEL_NAME = "llama3.1"

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or overwrite an existing file with content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path of the file to write."},
                    "content": {"type": "string", "description": "The content to write into the file."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file from the filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file to read."}
                },
                "required": ["path"]
            }
        }
    }
]

def run_test_case_1():
    print("\n" + "="*50)
    print("TEST CASE 1 (LLAMA 3.1): Single Tool Call Validation")
    print("Target: Have the model write a file named 'hello_local_llama.txt'.")
    print("="*50)
    
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant that has access to file execution tools. Use them to fulfill user requests."},
        {"role": "user", "content": "Write a file named 'hello_local_llama.txt' containing 'Hello from local Llama 3.1!'."}
    ]
    
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        latency = time.time() - start_time
        
        message = response.choices[0].message
        print(f"Latency: {latency:.4f} seconds")
        print("\nRaw Message Object:")
        print(message)
        
        if message.tool_calls:
            print("\nSUCCESS: Model correctly generated a tool call!")
            for idx, tool_call in enumerate(message.tool_calls):
                print(f"\nTool Call #{idx+1}:")
                print(f"  ID:   {tool_call.id}")
                print(f"  Name: {tool_call.function.name}")
                print(f"  Args: {tool_call.function.arguments}")
        else:
            print("\nFAILURE: Model responded with prose instead of a tool call.")
            print("Content:", message.content)
            
    except Exception as e:
        print(f"\nERROR: Failed to query Ollama API: {e}")

def run_test_case_2():
    print("\n" + "="*50)
    print("TEST CASE 2 (LLAMA 3.1): Chained Sequential Tool Calls Validation")
    print("Target: Read 'hello_local_llama.txt', then write 'hello_local_modified_llama.txt'.")
    print("="*50)
    
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant. Fulfill the user request using sequential tool calls step-by-step."},
        {"role": "user", "content": "Read the file 'hello_local_llama.txt' first, then write a modified file 'hello_local_modified_llama.txt' adding 'Modified locally!' to the end."}
    ]
    
    start_time = time.time()
    try:
        print("Step A: Requesting file read...")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        latency_1 = time.time() - start_time
        
        message = response.choices[0].message
        print(f"Step A Latency: {latency_1:.4f} seconds")
        
        if not message.tool_calls:
            print("FAILURE: Model did not generate a tool call for step A.")
            print("Content:", message.content)
            return
            
        tool_call = message.tool_calls[0]
        print(f"Emitted: {tool_call.function.name} with arguments {tool_call.function.arguments}")
        
        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": "Hello from local Llama 3.1!"
        })
        
        print("\nStep B: Requesting file write based on read results...")
        start_time = time.time()
        response_2 = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        latency_2 = time.time() - start_time
        print(f"Step B Latency: {latency_2:.4f} seconds")
        
        message_2 = response_2.choices[0].message
        print("\nRaw Message Object (Step B):")
        print(message_2)
        
        if message_2.tool_calls:
            print("\nSUCCESS: Model successfully generated a chained tool call!")
            for idx, tc in enumerate(message_2.tool_calls):
                print(f"\nTool Call #{idx+1}:")
                print(f"  ID:   {tc.id}")
                print(f"  Name: {tc.function.name}")
                print(f"  Args: {tc.function.arguments}")
        else:
            print("\nFAILURE: Model did not chain the second tool call.")
            print("Content:", message_2.content)
            
    except Exception as e:
        print(f"\nERROR: Failed to query Ollama API: {e}")

if __name__ == "__main__":
    print("Ollama Llama3.1 Tool-Calling Validator")
    print(f"Using Endpoint: http://localhost:11434/v1")
    print(f"Target Model:   {MODEL_NAME}")
    
    run_test_case_1()
    run_test_case_2()
