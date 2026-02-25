from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [line for line in f.read().strip().split("\n") if line]

setup(
    name="real_estate_crm",
    version="0.0.1",
    description="Real Estate CRM & Sales Management System on ERPNext",
    author="Placeholder Author",           # TODO: replace with actual publisher name
    author_email="placeholder@example.com", # TODO: replace with actual email
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
