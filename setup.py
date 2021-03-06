import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="emr_studio_publisher",
    version="0.0.1",

    description="Jupyter Notebook CD Pipeline",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "emr_studio_publisher"},
    packages=setuptools.find_packages(where="emr_studio_publisher"),

    install_requires=[
        "aws-cdk.core==1.110.0",
        "aws-cdk.aws-s3",
        "aws-cdk.aws-s3-deployment",
        "aws-cdk.aws-cloudfront",
        "aws-cdk.aws-cloudfront-origins",
        "aws-cdk.aws-codecommit",
        "aws-cdk.aws-codebuild",
        "aws-cdk.aws-codepipeline",
        "aws-cdk.aws-codepipeline-actions",
        "aws-cdk.aws-servicecatalog",
        "aws-cdk.aws-certificatemanager"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
