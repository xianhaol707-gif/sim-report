from setuptools import Extension, setup


setup(
    ext_modules=[
        Extension(
            "phasegrid._phasegrid_cpp",
            ["src/phasegrid/_phasegrid_cpp.cpp"],
            language="c++",
            optional=True,
        )
    ]
)
