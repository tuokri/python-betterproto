import os.path
import re

try:
    # betterproto[compiler] specific dependencies
    import black
    import isort.api
    import jinja2
except ImportError as err:
    print(
        "\033[31m"
        f"Unable to import `{err.name}` from betterproto plugin! "
        "Please ensure that you've installed betterproto as "
        '`pip install "betterproto[compiler]"` so that compiler dependencies '
        "are included."
        "\033[0m"
    )
    raise SystemExit(1)

from .models import OutputTemplate


def _render_template(template: str, **kwargs) -> str:
    templates_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates")
    )

    env = jinja2.Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=jinja2.FileSystemLoader(templates_folder),
    )
    template = env.get_template(template)

    code = template.render(**kwargs)
    code = isort.api.sort_code_string(
        code=code,
        show_diff=False,
        py_version=37,
        profile="black",
        combine_as_imports=True,
        lines_after_imports=2,
        quiet=True,
        force_grid_wrap=2,
        known_third_party=["grpclib", "betterproto"],
    )
    return black.format_str(
        src_contents=code,
        mode=black.Mode(),
    )


def outputfile_init(
    *,
    output_file: OutputTemplate,
    output_package_name: str,
) -> str:
    # TODO: this func needs a bit of refactoring.

    service_imports = (
        name
        for service in output_file.services
        for name in (f"{service.py_name}Base", f"{service.py_name}Stub")
    )

    import_objects = sorted(
        [
            *[x.py_name for x in output_file.enums],
            *[x.py_name for x in output_file.messages],
            *service_imports,
        ]
    )

    other_package_imports = []
    for imp in output_file.imports:
        match = re.match(r"from\s+\.\s+import\s+(\w+)", imp)
        if match:
            other_package_imports.append(match.group(1))

    __all__ = sorted(
        [
            *import_objects,
            *other_package_imports,
        ]
    )

    return _render_template(
        "init.py.j2",
        output_file=output_file,
        imports=output_file.imports,
        package=output_package_name.split(".")[-1],
        import_objects=import_objects,
        __all__=__all__,
    )


def outputfile_compiler(*, output_file: OutputTemplate) -> str:
    return _render_template("template.py.j2", output_file=output_file)
