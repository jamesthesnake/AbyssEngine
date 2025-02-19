#!/usr/bin/env python3

import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GlobalFunctionItem:
    function_name: str
    owned_function: str

@dataclass
class ClassPropertyItem:
    name: str
    type: str
    comment: str

@dataclass
class ParameterDefinition:
    name: str
    type: str
    comment: str

@dataclass
class FunctionDefinition:
    name: str
    return_type: str
    comment: str
    return_comment: str
    parameters: List[ParameterDefinition]


class Generator:
    def __init__(self, base_path, out_path):
        self.include_paths: List[str] = []
        self.base_path = base_path
        self.out_path = out_path
        self.generated_banner = [
            "-- ---------------------------------------------------------------------- --",
            "-- THIS FILE WAS AUTO-GENERATED BY generate.py -  DO NOT HAND MODIFY!     --",
            "-- ---------------------------------------------------------------------- --",
            ""
        ]

    def ReadFileLines(self, file_path) -> List[str]:
        """ Reads a file and returns it as a collection of strings. """

        file = open(file_path, 'r')
        source_lines = file.readlines()
        file.close()
        return source_lines

    def WriteFileLines(self, file_path, lines):
        file = open(file_path, 'w')
        file.write("\n".join(self.generated_banner))
        file.write("\n".join(lines))
        file.write("\n") # Add trailing line
        file.close()

    def GetTopLevelLuaFunctions(self) -> List[GlobalFunctionItem]:
        """ Returns the list of top level functions (abyss module functions). """

        results: GlobalFunctionItem[int] = []

        file_lines = self.ReadFileLines(
            os.path.join(self.base_path, "scripthost.cpp"))
        for line in file_lines:

            # Skip if this isn't a module function
            if not "module.set_function(\"" in line:
                continue

            parts = line.strip().split('"')
            function_name = parts[1].strip()

            owned_function = ""
            if ("InitializeTableFor(" in parts[2]):
                owned_function = "ScriptHost::" + parts[2].strip().split('InitializeTableFor(')[1].split('(')[0]
            else:
                owned_function = parts[2].strip().split('&')[1].split(',')[0].strip()
            results.append(GlobalFunctionItem(function_name, owned_function))
        return results

    def SanitizeTypeName(self, type_name: str):
        is_vector = "std::vector<" in type_name

        if "std::function<" in type_name or "sol::protected_function" in type_name or "sol::" in type_name:
            return "function"


        result = type_name\
            .replace("*", "")\
            .replace("&", "")\
            .replace("virtual", "")\
            .replace("const", "") \
            .replace("std::string_view", "string") \
            .replace("std::string", "string")\
            .replace("std::u16string", "string")\
            .replace("sol::safe_function", "function") \
            .replace("std::tuple<", "") \
            .replace("std::vector<", "") \
            .replace("std::unique_ptr<", "") \
            .replace(">", "") \
            .replace("function", "")\
            .replace("LibAbyss::", "") \
            .replace("uint32_t", "number")\
            .replace("uint16_t", "number")\
            .replace("uint8_t", "number")\
            .replace("int", "number")\
            .replace("bool", "boolean")\
            .replace("float", "number")\
            .replace("double", "number")\
            .replace("void", "nil")\
            .strip()

        if is_vector:
            result += "[]"


        return result


    def GetFunctionsForHeader(self, header_path) -> Dict[str, FunctionDefinition]:
        result = {}
        current_class = ""

        file_lines = self.ReadFileLines(header_path)

        for line_idx in range(0, len(file_lines)):
            line = file_lines[line_idx].strip()

            if line.strip().startswith("[[nodiscard]]"):
                line = line.replace("[[nodiscard]]", "").strip()


            if current_class == "" and ((line.startswith("class ") or line.startswith("struct ")) and line.endswith("{")):
                current_class = line.split(" ")[1].strip()
                continue

            if not ("(" in line and (");" in line or ") const;" in line or " = 0;" in line)):
                continue

            function_name = line.split("(")[0]
            function_name = function_name.split(" ")[function_name.count(" ")]
            function_return_type = self.SanitizeTypeName(line[0:line.find(function_name)-1])
            function_name = current_class + "::" + function_name


            default_comment = "No description set in " + os.path.basename(header_path) + ":" + str(line_idx+1) + "."
            result[function_name] = FunctionDefinition("", "", default_comment, default_comment, [])
            result[function_name].name = function_name
            result[function_name].return_type = function_return_type

            param_strs = line.split("(")[1].split(")")[0].strip().split(",")

            if not (len(param_strs) == 1 and param_strs[0] == ""):
                for param_str in param_strs:
                    parts = param_str.strip().split(" ")
                    param_name = parts[len(parts)-1].replace("&", "").replace("*", "").strip()
                    param_type = self.SanitizeTypeName(param_str[:param_str.rfind(" ")])
                    result[function_name].parameters.append(ParameterDefinition(param_name, param_type, default_comment))

            for i in range(line_idx - 1, 0, -1):
                comment_line = file_lines[i].strip()
                if not comment_line.startswith("/// \\"):
                    break

                if comment_line.startswith("/// \\brief "):
                    result[function_name].comment = comment_line[11:]
                elif comment_line.startswith("/// \\return "):
                    result[function_name].return_comment = comment_line[12:]
                elif comment_line.startswith("/// \\param "):
                    end_str = comment_line[11:]
                    param_name = end_str[:end_str.find(" ")].strip()
                    param_comment = end_str[end_str.find(" "):].strip()

                    for param in result[function_name].parameters:
                        if param.name != param_name:
                            continue
                        param.comment = param_comment
                        break

        return result

    def GenerateFunctionDefLine(self, class_name: str, function_name: str, func_def: FunctionDefinition) -> List[str]:
        result = []
        param_names = []
        result.append("---" + func_def.comment)
        for param in func_def.parameters:
            param_names.append(param.name)
            result.append("---@param " + param.name + " " + param.type + " @ " + param.comment)
        if len(func_def.return_type) > 0 and func_def.return_type != 'nil':
            result.append("---@return " + func_def.return_type + " @ " + func_def.return_comment)

        sep = ":"
        if class_name == "abyss":
            sep = "."
        result.append("function " + class_name + sep + function_name + "(" + ", ".join(param_names) + ") end")

        return result

    def CreateAbyssModuleFile(self):
        file_lines = [
            "---@meta",
            "---version: 0.1",
            "",
            "---@class abyss",
            "abyss = {}",
        ]

        abyss_funcs = self.GetTopLevelLuaFunctions()
        script_host_functions = self.GetFunctionsForHeader(os.path.join(self.base_path, "scripthost.h"))

        for abyss_func in abyss_funcs:
            if abyss_func.owned_function not in script_host_functions.keys():
                continue

            script_host_function = script_host_functions[abyss_func.owned_function]
            file_lines.append("")
            def_lines = self.GenerateFunctionDefLine("abyss", abyss_func.function_name, script_host_function)
            file_lines.extend(def_lines)

        self.WriteFileLines(os.path.join(self.out_path, "abyss.lua"), file_lines)

    def GetHostClassProperties(self, class_name:str) -> List[GlobalFunctionItem]:
        result: List[GlobalFunctionItem] = []
        file_lines = self.ReadFileLines(os.path.join(self.base_path, "scripthost.cpp"))

        class_var = ""
        node_special_case = class_name == "Node"

        if node_special_case:
            class_var = "nodeType"
        else:
            for line in file_lines:
                line = line.strip()
                if not line.startswith("auto "):
                    continue
                if (not "<" + class_name + ">" in line) and (not "::" + class_name + ">" in line):
                    continue

                class_var = line.split(" ")[1]
                break

        if len(class_var) == 0:
            return []

        for line in file_lines:
            line = line.strip()

            if not line.startswith(class_var + "[\""):
                continue

            if "sol::property(" not in line:
                continue


            if node_special_case:
                owned_name = line.split("&")[1].replace(",", "").strip().replace("T::", "Node::").replace(";", "")
            else:
                owned_name = line.split("&")[1].replace(",", "").strip().replace(";", "")
            function_name = line.split('"')[1].strip()

            result.append(GlobalFunctionItem(function_name, owned_name))

        return result

    def GetHostClassMethods(self, class_name:str) -> List[GlobalFunctionItem]:
        file_lines = self.ReadFileLines(os.path.join(self.base_path, "scripthost.cpp"))

        class_var = ""
        node_special_case = class_name == "Node"

        if node_special_case:
            class_var = "nodeType"
        else:
            for line in file_lines:
                line = line.strip()
                if not line.startswith("auto "):
                    continue
                if not "<" + class_name + ">" in line:
                    continue

                class_var = line.split(" ")[1].strip()

        if len(class_var) == 0:
            return []

        result = []
        for line in file_lines:
            line = line.strip()
            if not line.startswith(class_var + "[\""):
                continue

            if "sol::property(" in line:
                continue

            if node_special_case:
                owned_name = line.split("&")[1].replace(",", "").strip().replace("T::", class_name + "::").replace(";", "").strip()
            else:
                owned_name = line.split("&")[1].replace(";", "").strip()

            function_name = line.split('"')[1].strip()

            result.append(GlobalFunctionItem(function_name, owned_name))

        return result

    def DefaultValueFor(self, type_name) -> str:
        if type_name == "number":
            return "0"

        if type_name == "boolean":
            return "false"

        if type_name == "string":
            return "''"

        return "nil"

    def CreateAbyssClassFile(self, custom_type: str, header_path: str, has_node_parent: bool):
        file_lines = [
            "---@meta",
            "---version: 0.1",
            "",
            "---@class " + custom_type
        ]

        class_header_functions = self.GetFunctionsForHeader(header_path)
        class_methods = self.GetHostClassMethods(custom_type)
        class_properties = self.GetHostClassProperties(custom_type)

        if has_node_parent:
            class_properties.extend(self.GetHostClassProperties("Node"))
            class_methods.extend(self.GetHostClassMethods("Node"))
            class_header_functions.update(self.GetFunctionsForHeader(os.path.join(self.base_path, "../node/node.h")))

#         for header_funcs in class_header_functions:
#             print("\t\theader_funcs: " + header_funcs)
#
#
#         for class_method in class_methods:
#             print("\t\tM: " + class_method.function_name + " -> " + class_method.owned_function)

        if len(class_properties) == 0:
            file_lines.append(custom_type + " = {}")
        else:
            file_lines.append(custom_type + " = {")
            for property in class_properties:
                if property.owned_function not in class_header_functions.keys():
                    continue
                script_host_function = class_header_functions[property.owned_function]
                file_lines.append("---" + script_host_function.return_comment)
                file_lines.append("---@type " + script_host_function.return_type)
                file_lines.append(property.function_name + " = " + self.DefaultValueFor(script_host_function.return_type) + ",")
                file_lines.append("")

            file_lines.append("}")


        if len(class_methods) > 0:
            for class_func in class_methods:
                if class_func.owned_function not in class_header_functions.keys():
                    print("\t\tFunction not found: " + class_func.owned_function)
                    continue

                script_host_function = class_header_functions[class_func.owned_function]
                file_lines.append("")
                def_lines = self.GenerateFunctionDefLine(custom_type, class_func.function_name, script_host_function)
                file_lines.extend(def_lines)

        self.WriteFileLines(os.path.join(self.out_path, custom_type + ".lua"), file_lines)


    def LoadHeaderFiles(self, source_path):
        host_file_lines = self.ReadFileLines(source_path)

        for line in host_file_lines:
            line = line.strip()
            if not line.startswith("#include "):
                continue

            line = line[9:]

            line_path = ""

            if line.startswith("<libabyss"):
                line = line.replace("<", "").replace(">", "")
                line_path = os.path.normpath(os.path.join(\
                    self.base_path, "..", "..", "..", "..", "libabyss", "include", line))

            elif (line.startswith('"') or line.startswith("'")):
                line = line.strip().replace('"', "").replace("'", "")
                line_path = os.path.normpath(os.path.join(self.base_path, line))

            else:
                continue

            if line_path not in self.include_paths:
                self.include_paths.append(line_path)

        return

    def GetHeaderFileForClass(self, class_name: str) -> str:
        for header_path in self.include_paths:
            header_lines = self.ReadFileLines(header_path)

            for line in header_lines:
                if (("class " + class_name + " ") not in line) and (("struct " + class_name + " ") not in line):
                    continue
                return header_path

        return ""

    def CreateCustomTypesFiles(self):
        host_lines = self.ReadFileLines(os.path.join(self.base_path, "scripthost.cpp"))
        for line in host_lines:
            if ("module.new_usertype<" not in line) and ("CreateLuaObjectType<" not in line):
                continue

            if "<T>" in line:
                continue

            has_node_parent = "CreateLuaObjectType<" in line
            custom_type = line[line.find("<")+1:line.find(">")]
            parts = custom_type.split("::")
            custom_type = parts[len(parts)-1].strip()
            custom_type_header = self.GetHeaderFileForClass(custom_type)
            if custom_type_header == "":
                print("*WARNING* Couldn't find header for type", custom_type)
                continue

            print("   -> " + custom_type + " (" + custom_type_header + ")")
            self.CreateAbyssClassFile(custom_type, custom_type_header, has_node_parent)

        return

    def Generate(self):
        print("Loading header files...")
        self.LoadHeaderFiles(os.path.join(self.base_path, "scripthost.h"))
        self.LoadHeaderFiles(os.path.join(self.base_path, "scripthost.cpp"))

        print("Writing abyss module file...")
        self.CreateAbyssModuleFile()

        print("Writing class definitions:")
        self.CreateCustomTypesFiles()



generator = Generator(
    os.path.normpath(os.path.join(os.path.curdir, "..", "apps", "abyssengine", "src", "engine")),
    os.path.normpath(os.path.join(os.path.curdir, "library"))
)
generator.Generate()
