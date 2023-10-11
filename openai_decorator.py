import inspect
import functools
import importlib.util
import os
import json
from docstring_parser import parse

# Map python types to JSON schema types
type_mapping = {
    "int": "integer",
    "float": "number",
    "str": "string",
    "bool": "boolean",
    "list": "array",
    "tuple": "array",
    "dict": "object",
#    "None": "null",
    "None": "string",
}
def get_type_mapping(param_type):
    param_type = param_type.replace("<class '", '')
    param_type = param_type.replace("'>", '')
    if param_type.startswith("typing."):
        generic_type = param_type.split(".")[1].split("[")[0]
        if generic_type in ["List", "Optional"]:
            return type_mapping.get(generic_type.lower(), "string")
    return type_mapping.get(param_type, "string")
    
def get_inner_type(annotation_str):
    """
    Extracts the inner type from a type annotation string like List[str] or Optional[List[str]].
    """
    if "[" in annotation_str and "]" in annotation_str:
        return annotation_str.split("[")[1].split("]")[0]
    return annotation_str
    
def preprocess_docstring(docstring):
    """
    Preprocess a docstring to merge multi-line parameter descriptions into a single line.
    """
    lines = docstring.split("\n")
    merged_lines = []
    previous_line = ""
    keywords = [":param", ":return", ":rtype", ":raises", "Note:", "Example:", "Examples:"]

    for line in lines:
        stripped_line = line.strip()
        if any(keyword in stripped_line for keyword in keywords):
            # Start a new line for recognized keywords
            merged_lines.append(line)
        elif stripped_line and not previous_line.startswith(":param") and previous_line:
            # Merge with the previous line
            merged_lines[-1] = merged_lines[-1] + " " + stripped_line
        else:
            merged_lines.append(line)
        previous_line = stripped_line

    return "\n".join(merged_lines)

def get_params_dict(params, docstring):
    params_dict = {}
    required_params = []
    try:
        # Parse the docstring to get parameter descriptions
        preprocessed_docstring = preprocess_docstring(docstring)
        docstring_parsed = parse(preprocessed_docstring)
        param_descriptions = {p.arg_name: p.description for p in docstring_parsed.params}
    except Exception as e:
        print("Error parsing docstring:", e)
        param_descriptions = {}
        
    for k, v in params.items():
        annotation = str(v.annotation)
        param_type = get_type_mapping(annotation)
        
        is_optional = "typing.Optional" in annotation
        if is_optional:
            annotation = get_inner_type(annotation)
            param_type = get_type_mapping(annotation)

        description = param_descriptions.get(k, k)  # Use the parameter name as a fallback

        param_info = {
            "type": param_type,
            "description": description,
        }

        if k == "patterns":
            param_info["type"] = ["array", "null"]
            param_info["items"] = {
                "type": "string"
            }
            
        if param_type == "array":
            inner_type = get_inner_type(annotation)
            if inner_type != annotation:  # This means we've successfully extracted an inner type
                inner_type = get_type_mapping(inner_type)
                param_info["items"] = {
                    "type": inner_type
                }

        params_dict[k] = param_info
        if v.default == inspect.Parameter.empty:  # This checks if a default value is provided
            required_params.append(k)
    return params_dict, required_params

def openaifunc(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    # Mark the function as an OpenAI function
    wrapper._is_openai_func = True
    return wrapper

class OpenAI_functions:
    def __init__(self, filename=None):
        if filename:
            self.func_list, self.func_mapping = self._func_list_from_file(filename)
            # Check if a description for the whole func_list exists at the module level
            self.func_description = self._func_description_from_file(filename)
            if not self.func_description:
                self.func_description = "\n".join([func["description"] for func in self.func_list])

    @classmethod
    def from_file(cls, filename):
        return cls(filename)

    def _func_list_from_file(self, filename):
        module_spec = importlib.util.spec_from_file_location(filename, filename)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        functions_info = []
        function_mapping = {}
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and hasattr(attr, '_is_openai_func'):
                params = inspect.signature(attr).parameters
                param_dict, required_list = get_params_dict(params, attr.__doc__ or "")
                func_info = {
                    "name": attr.__name__,
                    "description": inspect.cleandoc(attr.__doc__ or ""),
                    "parameters": {
                        "type": "object",
                        "properties": param_dict,
                        "required": required_list,
                    },
                }
                functions_info.append(func_info)
                function_mapping[attr.__name__] = attr

        return functions_info, function_mapping

    def _func_description_from_file(self, filename):
        module_spec = importlib.util.spec_from_file_location(filename, filename)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return inspect.getdoc(module)

    def func_list(self):
        return self.func_list

    def func_mapping(self):
        return self.func_mapping

    def call_func(self, function_call):
        name = function_call["name"]
        arguments = function_call["arguments"]
        if name not in self.func_mapping:
            raise ValueError(f"Function {name} not found in mapping")
        try:
            arguments = json.loads(arguments)  # Convert the JSON string to a dictionary
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid arguments format: {e}")
        function = self.func_mapping[name]
        return function(**arguments)

class OpenAI_function_collection:
    def __init__(self):
        self.function_collections = []

    @classmethod
    def from_files(cls, *files):
        instance = cls()
        for file in files:
            instance.function_collections.append(OpenAI_functions.from_file(file))
        return instance

    @classmethod
    def from_folder(cls, folder_path):
        instance = cls()
        for filename in os.listdir(folder_path):
            if filename.endswith(".py"):
                instance.function_collections.append(OpenAI_functions.from_file(os.path.join(folder_path, filename)))
        return instance

    @property
    def func_description(self):
        return "\n".join([funcs.func_description for funcs in self.function_collections])
        
    @property
    def func_list(self):
        return [func for func_collection in self.function_collections for func in func_collection.func_list]
        
    def call_func(self, function_call):
        for funcs in self.function_collections:
            if function_call["name"] in funcs.func_mapping:
                return funcs.call_func(function_call)
        raise ValueError(f"Function {function_call['name']} not found in mapping")

    def func_mapping(self):
        mapping = {}
        for funcs in self.function_collections:
            mapping.update(funcs.func_mapping)
        return mapping
