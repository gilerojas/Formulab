from setuptools import setup, find_packages

setup(
    name="formulab",
    version="1.0.0",
    author="GREQ Systems",
    description="Sistema de fórmulas y escalamiento de producción (Formulab GREQ)",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.25.0",
    ],
    python_requires=">=3.9",
)
