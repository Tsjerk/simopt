from setuptools import setup

# Read the version from a file to be sure it is consistent with the version
# in the package
with open('VERSION.txt') as infile:
    version = infile.readline().strip()

setup(
    name='simopt',
    version=version,
    description='SIMple OPTion parser',
    long_description=open("README.md").read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ],
    keywords='simple option parser',
    url='http://github.com/Tsjerk/simopt',
    download_url='https://github.com/Tsjerk/simopt/archive/v0.1.tar.gz',
    author='Tsjerk A. Wassenaar',
    author_email='tsjerkw@gmail.com',
    license='MIT',
    py_modules=['simopt'],
    install_requires=[
    ],
    #      test_suite='nose.collector',
    #      tests_require=['nose', 'nose-cover3'],
    #      entry_points={
    #      },
    include_package_data=True,
    zip_safe=False
)



