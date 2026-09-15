"""FastAPI source code analyzer using Python AST."""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging import logger
from app.services.analyzers.base import (
    APIAnalyzer,
    APIEndpointSnapshot,
    APISnapshot,
    FieldSnapshot,
    ParameterSnapshot,
    SchemaSnapshot,
)
from app.services.git_service import GitService

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}


class PydanticModelVisitor(ast.NodeVisitor):
    """AST visitor to find Pydantic model definitions."""

    def __init__(self):
        self.models: Dict[str, SchemaSnapshot] = {}

    def visit_ClassDef(self, node: ast.ClassDef):
        # Check if class inherits from BaseModel or similar
        is_pydantic = False
        for base in node.bases:
            if isinstance(base, ast.Name) and "Model" in base.id:
                is_pydantic = True
                break
            elif isinstance(base, ast.Attribute) and "Model" in base.attr:
                is_pydantic = True
                break

        # Collect fields even if base is not strictly named BaseModel (in case of type aliasing)
        fields: List[FieldSnapshot] = []
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                field_type, is_optional = self._parse_type_annotation(stmt.annotation)
                is_required = stmt.value is None and not is_optional
                default_val = self._parse_default_val(stmt.value)
                description = self._parse_field_description(stmt.value)

                # If default value is ellipsis `...`, it is required
                if isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
                    is_required = True
                    default_val = None

                fields.append(
                    FieldSnapshot(
                        name=field_name,
                        type=field_type,
                        required=is_required,
                        default=default_val,
                        description=description,
                    )
                )

        if fields or is_pydantic:
            self.models[node.name] = SchemaSnapshot(name=node.name, fields=fields)

        self.generic_visit(node)

    def _parse_type_annotation(self, node: Optional[ast.AST]) -> Tuple[str, bool]:
        """Convert Python AST type annotation to OpenAPI type string and optional flag."""
        if node is None:
            return "string", False

        if isinstance(node, ast.Name):
            mapping = {
                "int": "integer",
                "float": "number",
                "str": "string",
                "bool": "boolean",
                "dict": "object",
                "list": "array",
                "Any": "any",
            }
            return mapping.get(node.id, node.id), False

        if isinstance(node, ast.Subscript):
            # Handle Optional[T], Union[T, None], List[T]
            if isinstance(node.value, ast.Name):
                container = node.value.id
                if container in ("Optional", "Union"):
                    # Extract inner type
                    inner_type, _ = self._parse_type_annotation(node.slice)
                    return inner_type, True
                elif container in ("List", "Sequence", "Set"):
                    inner_type, _ = self._parse_type_annotation(node.slice)
                    return f"array[{inner_type}]", False
                elif container == "Dict":
                    return "object", False

        if isinstance(node, ast.Constant):
            return str(node.value), False

        return "string", False

    def _parse_default_val(self, node: Optional[ast.AST]) -> Optional[Any]:
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            return node.value if node.value is not Ellipsis else None
        if isinstance(node, ast.Name):
            if node.id == "None":
                return None
            return node.id
        return None

    def _parse_field_description(self, node: Optional[ast.AST]) -> Optional[str]:
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
        return None


class FastAPIFileVisitor(ast.NodeVisitor):
    """AST visitor to inspect routes and endpoints in a Python file."""

    def __init__(self, file_path: str, known_schemas: Dict[str, SchemaSnapshot]):
        self.file_path = file_path
        self.known_schemas = known_schemas
        self.endpoints: List[APIEndpointSnapshot] = []
        self.router_prefixes: Dict[str, str] = {}  # router_var_name -> prefix
        self.router_tags: Dict[str, List[str]] = {}

    def visit_Assign(self, node: ast.Assign):
        """Detect router assignments like: router = APIRouter(prefix='/users', tags=['Users'])"""
        if isinstance(node.value, ast.Call):
            func = node.value.func
            is_router = (
                (isinstance(func, ast.Name) and func.id == "APIRouter")
                or (isinstance(func, ast.Attribute) and func.attr == "APIRouter")
            )
            if is_router:
                prefix = ""
                tags = []
                for kw in node.value.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        prefix = str(kw.value.value)
                    elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                        tags = [elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)]

                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.router_prefixes[target.id] = prefix
                        self.router_tags[target.id] = tags

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)
        self.generic_visit(node)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Analyze decorators on function to identify FastAPI routes."""
        for decorator in node.decorator_list:
            endpoint_info = self._parse_decorator(decorator)
            if not endpoint_info:
                continue

            method, raw_path, router_var, dec_kwargs = endpoint_info

            # Apply router prefix if applicable
            prefix = self.router_prefixes.get(router_var, "")
            full_path = self._normalize_path(prefix, raw_path)

            # Extract docstring
            docstring = ast.get_docstring(node)
            summary = dec_kwargs.get("summary")
            description = dec_kwargs.get("description")

            if not summary and docstring:
                lines = docstring.strip().split("\n")
                summary = lines[0].strip()
                if len(lines) > 1:
                    description = "\n".join(lines[1:]).strip()

            # Status Code
            status_code = dec_kwargs.get("status_code", 200)

            # Tags
            tags = dec_kwargs.get("tags", [])
            if router_var in self.router_tags:
                tags.extend([t for t in self.router_tags[router_var] if t not in tags])

            # Extract parameters and request body from function signature
            parameters, request_body, auth_required, auth_deps = self._parse_parameters(node, full_path)

            # Response model
            response_body = None
            response_model_name = dec_kwargs.get("response_model")
            if response_model_name and response_model_name in self.known_schemas:
                response_body = self.known_schemas[response_model_name]
            elif isinstance(node.returns, ast.Name) and node.returns.id in self.known_schemas:
                response_body = self.known_schemas[node.returns.id]

            endpoint = APIEndpointSnapshot(
                method=method.upper(),
                path=full_path,
                function_name=node.name,
                summary=summary,
                description=description,
                status_code=status_code,
                parameters=parameters,
                request_body=request_body,
                response_body=response_body,
                auth_required=auth_required,
                auth_dependencies=auth_deps,
                tags=tags,
                source_file=self.file_path,
                source_line=node.lineno,
            )
            self.endpoints.append(endpoint)

    def _parse_decorator(self, node: ast.AST) -> Optional[Tuple[str, str, str, Dict[str, Any]]]:
        """Check if decorator matches @app.<method> or @router.<method>."""
        if not isinstance(node, ast.Call):
            return None

        func = node.func
        if not isinstance(func, ast.Attribute):
            return None

        method_name = func.attr.lower()
        if method_name not in HTTP_METHODS:
            return None

        # Determine router / app variable name
        router_var = ""
        if isinstance(func.value, ast.Name):
            router_var = func.value.id

        # Path is typically first positional argument
        path = "/"
        if node.args and isinstance(node.args[0], ast.Constant):
            path = str(node.args[0].value)

        # Keyword arguments
        kwargs = {}
        for kw in node.keywords:
            if kw.arg == "status_code":
                if isinstance(kw.value, ast.Constant):
                    kwargs["status_code"] = int(kw.value.value)
                elif isinstance(kw.value, ast.Attribute):
                    # status.HTTP_201_CREATED
                    match = re.search(r"(\d{3})", kw.value.attr)
                    if match:
                        kwargs["status_code"] = int(match.group(1))
            elif kw.arg == "summary" and isinstance(kw.value, ast.Constant):
                kwargs["summary"] = str(kw.value.value)
            elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                kwargs["description"] = str(kw.value.value)
            elif kw.arg == "response_model":
                if isinstance(kw.value, ast.Name):
                    kwargs["response_model"] = kw.value.id
            elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                kwargs["tags"] = [elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)]

        return method_name, path, router_var, kwargs

    def _normalize_path(self, prefix: str, path: str) -> str:
        """Combine router prefix and route path cleanly."""
        clean_prefix = prefix.strip()
        clean_path = path.strip()

        if not clean_prefix:
            return clean_path if clean_path.startswith("/") else f"/{clean_path}"

        if not clean_prefix.startswith("/"):
            clean_prefix = f"/{clean_prefix}"
        if clean_prefix.endswith("/"):
            clean_prefix = clean_prefix[:-1]

        if not clean_path.startswith("/"):
            clean_path = f"/{clean_path}"

        if clean_path == "/" and clean_prefix:
            return clean_prefix

        return f"{clean_prefix}{clean_path}"

    def _parse_parameters(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        full_path: str
    ) -> Tuple[List[ParameterSnapshot], Optional[SchemaSnapshot], bool, List[str]]:
        """Extract path parameters, query params, headers, and request body model."""
        parameters: List[ParameterSnapshot] = []
        request_body: Optional[SchemaSnapshot] = None
        auth_required = False
        auth_deps: List[str] = []

        # Find path parameters in path string: /users/{user_id} or /items/{item_id:int}
        path_param_names = set(re.findall(r"\{([a-zA-Z0-9_]+)(?::[a-zA-Z0-9_]+)?\}", full_path))

        # Inspect function arguments
        args = node.args.args
        defaults = node.args.defaults
        num_defaults = len(defaults)
        first_default_idx = len(args) - num_defaults

        for i, arg in enumerate(args):
            arg_name = arg.arg
            if arg_name in ("self", "cls", "request"):
                continue

            # Check default value if present
            default_node = defaults[i - first_default_idx] if i >= first_default_idx else None
            is_depends, dep_name = self._is_dependency_injection(default_node)

            if is_depends:
                if any(k in dep_name.lower() for k in ("auth", "user", "token", "security", "jwt", "key", "admin")):
                    auth_required = True
                    auth_deps.append(dep_name)
                continue

            # Check if arg is Header / Cookie / Query / Path
            param_location, is_explicit = self._get_param_location(default_node, arg_name, path_param_names)

            # Determine type
            arg_type = "string"
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    arg_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Subscript):
                    if isinstance(arg.annotation.value, ast.Name):
                        arg_type = f"{arg.annotation.value.id}[...]"

            # Map Python types to OpenAPI
            type_mapping = {"int": "integer", "float": "number", "str": "string", "bool": "boolean"}
            open_api_type = type_mapping.get(arg_type, arg_type)

            # Check if type is a known Pydantic Model -> this is the Request Body
            if arg_type in self.known_schemas:
                request_body = self.known_schemas[arg_type]
            elif arg_name in path_param_names or param_location == "path":
                parameters.append(
                    ParameterSnapshot(
                        name=arg_name,
                        location="path",
                        type=open_api_type,
                        required=True,
                    )
                )
            elif param_location in ("query", "header", "cookie"):
                is_req = default_node is None
                parameters.append(
                    ParameterSnapshot(
                        name=arg_name,
                        location=param_location,
                        type=open_api_type,
                        required=is_req,
                    )
                )
            else:
                # Default non-path, non-body param is a query param
                is_req = default_node is None
                parameters.append(
                    ParameterSnapshot(
                        name=arg_name,
                        location="query",
                        type=open_api_type,
                        required=is_req,
                    )
                )

        return parameters, request_body, auth_required, auth_deps

    def _is_dependency_injection(self, node: Optional[ast.AST]) -> Tuple[bool, str]:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("Depends", "Security"):
                if node.args:
                    if isinstance(node.args[0], ast.Name):
                        return True, node.args[0].id
                    elif isinstance(node.args[0], ast.Attribute):
                        return True, node.args[0].attr
                return True, node.func.id
        return False, ""

    def _get_param_location(
        self,
        node: Optional[ast.AST],
        arg_name: str,
        path_param_names: Set[str]
    ) -> Tuple[str, bool]:
        if arg_name in path_param_names:
            return "path", True

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == "Header":
                return "header", True
            elif func_name == "Query":
                return "query", True
            elif func_name == "Path":
                return "path", True
            elif func_name == "Cookie":
                return "cookie", True

        return "query", False


class FastAPIAnalyzer(APIAnalyzer):
    """FastAPI source code AST analyzer."""

    def analyze(
        self,
        repository_path: Path | str,
        target_files: Optional[List[str]] = None,
        commit_sha: Optional[str] = None
    ) -> APISnapshot:
        """Scan repository Python files and construct an APISnapshot."""
        repo_p = Path(repository_path).resolve()
        snapshot = APISnapshot(framework="fastapi", commit_sha=commit_sha)

        # 1. Discover all Python files
        if target_files:
            py_files = [f for f in target_files if f.endswith(".py")]
        else:
            py_files = GitService.list_python_files(repo_p)

        logger.info(f"Analyzing {len(py_files)} Python source files in {repo_p}...")

        # 2. First Pass: Collect all Pydantic schemas across files
        schema_visitor = PydanticModelVisitor()
        for rel_file in py_files:
            content = GitService.read_file_at_commit(repo_p, rel_file, commit_sha)
            if not content:
                continue
            try:
                tree = ast.parse(content, filename=rel_file)
                schema_visitor.visit(tree)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {rel_file}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error parsing models in {rel_file}: {str(e)}")

        snapshot.schemas = schema_visitor.models

        # 3. Second Pass: Extract routes and endpoint definitions
        for rel_file in py_files:
            content = GitService.read_file_at_commit(repo_p, rel_file, commit_sha)
            if not content:
                continue
            try:
                tree = ast.parse(content, filename=rel_file)
                visitor = FastAPIFileVisitor(file_path=rel_file, known_schemas=snapshot.schemas)
                visitor.visit(tree)
                for ep in visitor.endpoints:
                    snapshot.add_endpoint(ep)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {rel_file}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error parsing routes in {rel_file}: {str(e)}")

        logger.info(f"Analysis complete: Detected {len(snapshot.endpoints)} API endpoints and {len(snapshot.schemas)} models.")
        return snapshot
